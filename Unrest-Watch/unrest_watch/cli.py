"""Command line: collect -> ML filter -> risk for your location -> supply plan."""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone

import requests

from . import collector, supplies
from .geo import default_gazetteer
from .model import LABELS_TH, UnrestClassifier, evaluate
from .pipeline import build_events
from .risk import LEVELS, Assessment, assess


def _fmt_threat(t, idx: int) -> str:
    e = t.event
    where = e.place.name if e.place else "ไม่ทราบพื้นที่"
    dist = f"{t.distance_km:,.0f} กม." if t.distance_km is not None else "ไม่ระบุจุด"
    flag = " ⏳ล่วงหน้า" if e.planned else ""
    title = e.title if len(e.title) <= 110 else e.title[:107] + "..."
    return (f"{idx}. [{LABELS_TH[e.label]}] {title}\n"
            f"   📍 {where} · ห่าง {dist} · ความรุนแรง {e.severity:.1f}/5 · "
            f"{e.n_sources} แหล่งข่าว · ผลต่อคุณ {t.contribution * 100:.1f}%{flag}")


def render_report(a: Assessment, events_n: int, dropped: int, household: supplies.Household,
                  days: int, inventory: dict | None, top: int) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append(f"{a.emoji}  ระดับภัยสำหรับตำแหน่งของคุณ: {a.level_th}  "
                 f"(คะแนน {a.score * 100:.0f}/100)")
    lines.append("=" * 60)
    lines.append(f"ML คัดข่าว: เก็บ {events_n} เหตุการณ์ · ตัดข่าวไม่เกี่ยวข้องทิ้ง {dropped} ข่าว")
    if a.upcoming:
        lines.append("\n⚠️  เหตุที่กำลังจะเกิด/มีการนัดหมายใกล้คุณ:")
        lines += [_fmt_threat(t, i) for i, t in enumerate(a.upcoming[:3], 1)]
    lines.append(f"\n📰 เหตุการณ์ที่กระทบคุณมากที่สุด:")
    if a.threats:
        lines += [_fmt_threat(t, i) for i, t in enumerate(a.threats[:top], 1)]
    else:
        lines.append("   ไม่มีเหตุการณ์ใกล้ตัว")

    p = supplies.plan(household, days)
    lines.append(f"\n🛒 รายการกักตุนสำหรับ {household.size} คน "
                 f"(ผู้ใหญ่ {household.adults}, เด็ก {household.children}, ผู้สูงอายุ {household.elderly}) "
                 f"อยู่ได้ {days} วัน — ครบ 5 หมู่:")
    by_group: dict[int, list[str]] = {}
    for key, q in p["quantities"].items():
        if q:
            it = supplies.CATALOG[key]
            by_group.setdefault(it.group, []).append(f"{it.name_th} {q:g} × {it.unit_th}")
    for g in [1, 2, 3, 4, 5, 0]:
        title = supplies.GROUPS_TH.get(g, "💧 น้ำ (ดื่ม + ทำอาหาร + สุขอนามัยขั้นต่ำ)")
        lines.append(f"  • {title}")
        lines += [f"      - {s}" for s in by_group.get(g, [])]
    cov = p["coverage"]
    lines.append(f"  ➜ ชุดนี้พอสำหรับ ~{cov['balanced_days']:.0f} วันแบบครบ 5 หมู่ "
                 f"(ตัวที่หมดก่อน: {supplies.METRIC_TH[cov['limiting']]})")

    if inventory is not None:
        c = supplies.days_supported(inventory, household)
        lines.append("\n📦 ของที่คุณมีอยู่ตอนนี้อยู่ได้:")
        for g, d in c["groups"].items():
            mark = "✅" if d >= days else "❌"
            lines.append(f"   {mark} {supplies.GROUPS_TH[g]}: {d:.1f} วัน")
        lines.append(f"   {'✅' if c['per_metric']['water'] >= days else '❌'} น้ำดื่ม: "
                     f"{c['per_metric']['water']:.1f} วัน")
        lines.append(f"   ➜ ครบ 5 หมู่ได้ {c['balanced_days']:.1f} วัน (หมดก่อน: "
                     f"{supplies.METRIC_TH[c['limiting']]}) · ประทังชีวิตได้ {c['survival_days']:.1f} วัน")

    lines.append("\n🎒 ของจำเป็นอื่น ๆ:")
    lines += [f"   ☐ {x}" for x in supplies.checklist(a.level)]
    lines.append("\nหมายเหตุ: เป็นการประเมินจากหัวข้อข่าวโดยอัตโนมัติ ให้ยึดประกาศของทางการเป็นหลัก")
    return "\n".join(lines)


def notify_ntfy(topic: str, a: Assessment) -> None:
    body = f"{a.emoji} ระดับ {a.level_th} ({a.score * 100:.0f}/100) — ควรกักตุนเสบียง {a.stockpile_days} วัน"
    if a.threats:
        body += f"\nเหตุสำคัญ: {a.threats[0].event.title}"
    prio = {"green": "2", "yellow": "3", "orange": "4", "red": "5"}[a.level]
    requests.post(f"https://ntfy.sh/{topic}", data=body.encode("utf-8"),
                  headers={"Title": "Unrest Watch", "Priority": prio}, timeout=10)


def parse_args(argv=None):
    ap = argparse.ArgumentParser(prog="unrest_watch",
                                 description="รวบรวมข่าวความไม่สงบทั่วโลก คัดกรองด้วย ML และแจ้งเตือนพร้อมรายการกักตุนเสบียง")
    loc = ap.add_argument_group("ตำแหน่งของคุณ")
    loc.add_argument("--place", default="Bangkok", help="ชื่อเมือง/ประเทศ เช่น Bangkok, เชียงใหม่ (ค่าเริ่มต้น Bangkok)")
    loc.add_argument("--lat", type=float)
    loc.add_argument("--lon", type=float)
    hh = ap.add_argument_group("สมาชิกในบ้าน")
    hh.add_argument("--adults", type=int, default=1)
    hh.add_argument("--children", type=int, default=0)
    hh.add_argument("--elderly", type=int, default=0)
    ap.add_argument("--days", type=int, help="จำนวนวันที่อยากกักตุน (ค่าเริ่มต้นตามระดับภัย)")
    ap.add_argument("--inventory", help='ไฟล์ JSON ของที่มีอยู่ เช่น {"rice": 1, "canned_fish": 10, "water": 3}')
    ap.add_argument("--offline", action="store_true", help="ใช้ข่าวตัวอย่างแทนการดึงข่าวจริง")
    ap.add_argument("--news-days", type=int, default=3, help="ดึงข่าวย้อนหลังกี่วัน")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--json", action="store_true", help="พิมพ์ผลเป็น JSON")
    ap.add_argument("--watch", type=float, metavar="MIN", help="เฝ้าดูต่อเนื่อง ตรวจซ้ำทุก MIN นาที")
    ap.add_argument("--ntfy", metavar="TOPIC", help="ส่งแจ้งเตือนเข้ามือถือผ่านแอป ntfy เมื่อระดับภัยสูงขึ้น")
    ap.add_argument("--eval", action="store_true", help="วัดผลโมเดล ML (cross-validation) แล้วออก")
    ap.add_argument("--list-items", action="store_true", help="แสดงรหัสรายการอาหารสำหรับไฟล์ --inventory")
    return ap.parse_args(argv)


def run_once(args, model, lat, lon, household):
    log = lambda m: print(m, file=sys.stderr)
    if args.offline:
        articles = collector.load_sample()
        now = max(a.published for a in articles)
    else:
        articles = collector.collect(days=args.news_days, log=log)
        now = datetime.now(timezone.utc)
        if not articles:
            log("ดึงข่าวไม่ได้ ใช้ข่าวตัวอย่างแทน")
            articles = collector.load_sample()
            now = max(a.published for a in articles)
    events, dropped = build_events(articles, model)
    return assess(events, lat, lon, now=now), len(events), dropped


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.eval:
        r = evaluate()
        print(f"ข้อมูลฝึก {r['n']} หัวข่าว · 5-fold CV\n"
              f"macro-F1 {r['macro_f1']:.3f} · accuracy {r['accuracy']:.3f} · "
              f"แยกข่าวเกี่ยว/ไม่เกี่ยว ถูก {r['relevance_accuracy']:.3f}\n\n{r['report']}")
        return 0
    if args.list_items:
        for k, it in supplies.CATALOG.items():
            print(f"{k:16} {it.name_th} ({it.unit_th}) · เก็บได้ ~{it.shelf_days} วัน")
        return 0

    if args.lat is not None and args.lon is not None:
        lat, lon = args.lat, args.lon
    else:
        place = default_gazetteer().find(args.place)
        if place is None:
            print(f"ไม่รู้จักสถานที่ '{args.place}' ลองใส่ --lat/--lon", file=sys.stderr)
            return 2
        lat, lon = place.lat, place.lon
    household = supplies.Household(args.adults, args.children, args.elderly)
    if household.size <= 0:
        print("ต้องมีสมาชิกอย่างน้อย 1 คน", file=sys.stderr)
        return 2
    inventory = None
    if args.inventory:
        with open(args.inventory, encoding="utf-8") as f:
            inventory = json.load(f)

    model = UnrestClassifier().fit()
    last_level = None
    while True:
        a, n_events, dropped = run_once(args, model, lat, lon, household)
        days = args.days or a.stockpile_days
        if args.json:
            out = a.to_dict()
            p = supplies.plan(household, days)
            out["plan"] = {"days": days, "quantities": p["quantities"],
                           "balanced_days": round(p["coverage"]["balanced_days"], 1)}
            if inventory is not None:
                c = supplies.days_supported(inventory, household)
                out["inventory_days"] = {k: round(v, 1) for k, v in c["per_metric"].items()}
            print(json.dumps(out, ensure_ascii=False, indent=1))
        else:
            print(render_report(a, n_events, dropped, household, days, inventory, args.top))
        rank = [lv[1] for lv in LEVELS].index(a.level)
        if args.ntfy and (last_level is None or rank > last_level):
            try:
                notify_ntfy(args.ntfy, a)
            except requests.RequestException as e:
                print(f"ส่งแจ้งเตือนไม่สำเร็จ: {e}", file=sys.stderr)
        last_level = rank
        if not args.watch:
            return 0
        time.sleep(args.watch * 60)


if __name__ == "__main__":
    sys.exit(main())
