"""World view: every unrest event worldwide, ranked, plus 'what's new' between polls."""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .geo import region_of
from .model import LABELS_TH
from .pipeline import Event

BANGKOK = ZoneInfo("Asia/Bangkok")
TYPE_ICON = {"protest": "📢", "riot": "🔥", "armed_conflict": "💥", "terrorism": "💣", "coup": "🏛️"}


def importance(e: Event, now: datetime) -> float:
    """How much an event matters right now, anywhere in the world (0-1)."""
    age_h = max(0.0, (now - e.published).total_seconds() / 3600)
    recency = 1.0 if e.planned else math.exp(-age_h / 24)
    corroboration = min(1.0, 0.5 + 0.1 * e.n_sources)
    return (e.severity / 5) * recency * e.confidence * corroboration


def ago_th(when: datetime, now: datetime) -> str:
    mins = max(0, int((now - when).total_seconds() // 60))
    if mins < 60:
        return f"{mins} นาทีที่แล้ว"
    if mins < 48 * 60:
        return f"{mins // 60} ชม.ที่แล้ว"
    return f"{mins // 1440} วันที่แล้ว"


def region(e: Event) -> str:
    return region_of(e.place) if e.place else "ไม่ระบุพื้นที่"


def worth_showing(e: Event) -> bool:
    """Unlocated single-source items are mostly local or misread news."""
    return e.place is not None or (e.n_sources >= 2 and e.severity >= 3.5)


def recent(events: list[Event], now: datetime, hours: float) -> list[Event]:
    keep = [e for e in events if worth_showing(e) and
            (e.planned or (now - e.published).total_seconds() <= hours * 3600)]
    return sorted(keep, key=lambda e: -importance(e, now))


def fmt_event(e: Event, now: datetime, mark: str = "") -> str:
    where = f"{e.place.name}" if e.place else "ไม่ระบุพื้นที่"
    if e.place and e.place.country != e.place.name:
        where += f", {e.place.country}"
    title = e.title if len(e.title) <= 120 else e.title[:117] + "..."
    local = e.published.astimezone(BANGKOK).strftime("%d/%m %H:%M")
    flag = " ⏳ล่วงหน้า" if e.planned else ""
    return (f"{mark}{TYPE_ICON[e.label]} {title}\n"
            f"   📍 {where} · {LABELS_TH[e.label]} · รุนแรง {e.severity:.1f}/5 · "
            f"{e.n_sources} แหล่ง · {local} น. ({ago_th(e.published, now)}){flag}")


def render_world(events: list[Event], dropped: int, total_articles: int, now: datetime,
                 hours: float, top: int) -> str:
    evs = recent(events, now, hours)
    lines = ["=" * 60,
             f"🌍 สถานการณ์ความไม่สงบทั่วโลก · {len(evs)} เหตุการณ์ใน {hours:g} ชม.ล่าสุด",
             f"   อัปเดต {now.astimezone(BANGKOK):%d/%m/%Y %H:%M} น. (เวลาไทย)",
             "=" * 60,
             f"ML อ่าน {total_articles} หัวข่าว · ตัดข่าวไม่เกี่ยวข้อง {dropped} · "
             f"รวมข่าวซ้ำเหลือ {len(events)} เหตุการณ์ "
             f"(ซ่อน {sum(not worth_showing(e) for e in events)} รายการที่ไม่รู้พื้นที่และมีแหล่งเดียว)"]
    by_type = Counter(e.label for e in evs)
    lines.append("ประเภท: " + " · ".join(f"{TYPE_ICON[k]} {LABELS_TH[k]} {n}"
                                         for k, n in by_type.most_common()))

    lines.append(f"\n🔺 สำคัญที่สุด {min(top, len(evs))} เหตุการณ์:")
    lines += [fmt_event(e, now, f"{i}. ") for i, e in enumerate(evs[:top], 1)]

    by_region: dict[str, list[Event]] = {}
    for e in evs:
        by_region.setdefault(region(e), []).append(e)
    lines.append("\n🗺️  แยกตามภูมิภาค:")
    for reg, items in sorted(by_region.items(), key=lambda kv: (kv[0] == "ไม่ระบุพื้นที่", -len(kv[1]))):
        hot = Counter(e.place.country for e in items if e.place).most_common(4)
        hot_s = ", ".join(f"{c} {n}" for c, n in hot)
        lines.append(f"  • {reg}: {len(items)} เหตุการณ์" + (f" (มากสุด: {hot_s})" if hot_s else ""))
        lines.append(f"      ↳ {items[0].title[:100]}")
    return "\n".join(lines)


def _key(title: str) -> str:
    return re.sub(r"\W+", " ", title.lower()).strip()


@dataclass
class Change:
    event: Event
    is_new: bool  # False = more reports about a situation already shown


class LiveTracker:
    """Remembers what was already shown, so each poll only prints what changed.

    News feeds return a slightly different set of articles on every request,
    so "a headline I haven't seen" is not enough: a change needs a report
    published after the newest one already seen for that situation.
    """

    SLACK = timedelta(minutes=30)  # feeds publish a little late

    def __init__(self) -> None:
        self.latest: dict[tuple, datetime] = {}
        self.last_poll: datetime | None = None

    @staticmethod
    def _situation(e: Event) -> tuple:
        return (e.place.name if e.place else _key(e.title), e.label)

    def update(self, events: list[Event], now: datetime) -> list[Change]:
        changes = []
        for e in events:
            sit = self._situation(e)
            seen = self.latest.get(sit)
            if seen is None:
                if self.last_poll is None or e.published >= self.last_poll - self.SLACK:
                    changes.append(Change(e, True))
            elif e.published > seen:
                changes.append(Change(e, False))
            self.latest[sit] = max(seen or e.published, e.published)
        self.last_poll = now
        return changes
