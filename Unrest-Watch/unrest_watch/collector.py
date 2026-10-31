"""Collects unrest headlines from Google News RSS (English + Thai)."""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote_plus

import requests

SAMPLE_JSON = Path(__file__).parent / "data" / "sample_news.json"
RSS_URL = "https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={gl}:{lang}"

QUERIES_EN = [
    "protest OR demonstration OR strike OR rally",
    "riot OR clashes OR \"tear gas\" OR curfew OR looting",
    "airstrike OR shelling OR \"armed clashes\" OR offensive OR insurgents",
    "bombing OR \"terror attack\" OR \"mass shooting\" OR explosion",
    "coup OR \"martial law\" OR \"state of emergency\" OR junta",
]
QUERIES_TH = [
    "ชุมนุม OR ประท้วง OR ม็อบ",
    "ปะทะ OR จลาจล OR เคอร์ฟิว OR สลายการชุมนุม",
    "ระเบิด OR กราดยิง OR ก่อความไม่สงบ",
    "รัฐประหาร OR กฎอัยการศึก OR สู้รบ OR ชายแดน",
]


@dataclass
class Article:
    title: str
    source: str
    url: str
    published: datetime

    def to_dict(self) -> dict:
        d = asdict(self)
        d["published"] = self.published.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Article":
        return cls(d["title"], d.get("source", ""), d.get("url", ""),
                   datetime.fromisoformat(d["published"]))


def _split_source(title: str) -> tuple[str, str]:
    # Google News titles end in " - Source Name"; Thai outlets often add
    # "| Outlet | date" too. Outlet names (e.g. "The Bangkok Insight") must not
    # be read as the event location.
    m = re.match(r"^(.*)\s+-\s+([^-]+)$", title)
    title, source = (m.group(1).strip(), m.group(2).strip()) if m else (title.strip(), "")
    parts = [p.strip() for p in title.split(" | ")]
    while len(parts) > 1 and len(parts[-1]) <= 40:
        parts.pop()
    return " | ".join(parts), source


def parse_rss(xml_bytes: bytes) -> list[Article]:
    root = ET.fromstring(xml_bytes)
    out = []
    for item in root.iter("item"):
        raw = item.findtext("title") or ""
        title, source = _split_source(raw)
        src_el = item.find("source")
        if src_el is not None and src_el.text:
            source = src_el.text.strip()
        try:
            published = parsedate_to_datetime(item.findtext("pubDate") or "")
        except (TypeError, ValueError):
            published = datetime.now(timezone.utc)
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        out.append(Article(title, source, item.findtext("link") or "", published))
    return out


def fetch_query(query: str, thai: bool = False, days: int = 3, timeout: float = 15) -> list[Article]:
    q = quote_plus(f"{query} when:{days}d")
    url = RSS_URL.format(q=q, hl="th" if thai else "en-US", gl="TH" if thai else "US",
                         lang="th" if thai else "en")
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "unrest-watch/0.1"})
    r.raise_for_status()
    return parse_rss(r.content)


def _norm(title: str) -> str:
    return re.sub(r"\W+", " ", title.lower()).strip()


def collect(days: int = 3, extra_queries: list[str] | None = None,
            log=lambda msg: None) -> list[Article]:
    """Fetch all queries; skip ones that fail so one bad feed doesn't stop the run."""
    jobs = [(q, False) for q in QUERIES_EN] + [(q, True) for q in QUERIES_TH]
    jobs += [(q, bool(re.search(r"[฀-๿]", q))) for q in (extra_queries or [])]
    seen, out = set(), []
    for query, thai in jobs:
        try:
            articles = fetch_query(query, thai=thai, days=days)
        except (requests.RequestException, ET.ParseError) as e:
            log(f"ข้ามคำค้น '{query}': {e}")
            continue
        for a in articles:
            key = _norm(a.title)
            if key and key not in seen:
                seen.add(key)
                out.append(a)
    return out


def load_sample(path: Path = SAMPLE_JSON) -> list[Article]:
    with open(path, encoding="utf-8") as f:
        return [Article.from_dict(d) for d in json.load(f)]


def save_articles(articles: list[Article], path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump([a.to_dict() for a in articles], f, ensure_ascii=False, indent=1)
