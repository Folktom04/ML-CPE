"""Collects unrest headlines from Google News RSS (English + Thai)."""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
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
# Google News editions used for the English queries, so coverage is not
# only what US outlets report.
EDITIONS_EN = [("en-US", "US"), ("en-GB", "GB"), ("en-IN", "IN"), ("en-NG", "NG")]

# World news feeds read directly (title only; the classifier drops the
# non-unrest stories).
DIRECT_FEEDS = {
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "DW": "https://rss.dw.com/rdf/rss-en-world",
    "France 24": "https://www.france24.com/en/rss",
    "The Guardian": "https://www.theguardian.com/world/rss",
    "Sky News": "https://feeds.skynews.com/feeds/rss/world.xml",
    "UN News": "https://news.un.org/feed/subscribe/en/news/all/rss.xml",
    "ReliefWeb": "https://reliefweb.int/updates/rss.xml",
    "Crisis Group": "https://www.crisisgroup.org/rss.xml",
}

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


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(el: ET.Element, *names: str) -> ET.Element | None:
    for c in el:
        if _local(c.tag) in names:
            return c
    return None


def _parse_date(text: str) -> datetime:
    text = (text or "").strip()
    try:
        d = parsedate_to_datetime(text)  # RSS 2.0
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(text.replace("Z", "+00:00"))  # RDF / Atom
        except ValueError:
            d = datetime.now(timezone.utc)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def parse_rss(xml_bytes: bytes, default_source: str = "") -> list[Article]:
    """Reads RSS 2.0, RSS 1.0 (RDF) and Atom feeds."""
    root = ET.fromstring(xml_bytes)
    out = []
    for item in root.iter():
        if _local(item.tag) not in ("item", "entry"):
            continue
        t = _child(item, "title")
        raw = (t.text or "").strip() if t is not None else ""
        if default_source:  # direct feed: no " - Source" suffix to split off
            title, source = raw, default_source
        else:
            title, source = _split_source(raw)
        src_el = _child(item, "source")
        if src_el is not None and src_el.text:
            source = src_el.text.strip()
        link_el = _child(item, "link")
        link = ""
        if link_el is not None:
            link = (link_el.text or link_el.get("href") or "").strip()
        date_el = _child(item, "pubDate", "date", "published", "updated")
        published = _parse_date(date_el.text if date_el is not None else "")
        if title:
            out.append(Article(title, source, link, published))
    return out


def _get(url: str, timeout: float) -> bytes:
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0 (compatible; unrest-watch/0.2)"})
    r.raise_for_status()
    return r.content


def fetch_query(query: str, thai: bool = False, days: int = 3, timeout: float = 15,
                edition: tuple[str, str] = ("en-US", "US")) -> list[Article]:
    q = quote_plus(f"{query} when:{days}d")
    hl, gl = ("th", "TH") if thai else edition
    url = RSS_URL.format(q=q, hl=hl, gl=gl, lang="th" if thai else "en")
    return parse_rss(_get(url, timeout))


def fetch_feed(name: str, url: str, timeout: float = 15) -> list[Article]:
    return parse_rss(_get(url, timeout), default_source=name)


def _norm(title: str) -> str:
    return re.sub(r"\W+", " ", title.lower()).strip()


def collect(days: int = 3, extra_queries: list[str] | None = None, world: bool = False,
            log=lambda msg: None, workers: int = 8) -> list[Article]:
    """Fetch every source in parallel; a failing source is skipped, not fatal.

    world=True adds more Google News editions and the direct world news feeds.
    """
    editions = EDITIONS_EN if world else EDITIONS_EN[:1]
    jobs = [(f"Google News {ed[1]}: {q}", lambda q=q, ed=ed: fetch_query(q, days=days, edition=ed))
            for ed in editions for q in QUERIES_EN]
    jobs += [(f"Google News TH: {q}", lambda q=q: fetch_query(q, thai=True, days=days))
             for q in QUERIES_TH + [q for q in (extra_queries or []) if re.search(r"[\u0E00-\u0E7F]", q)]]
    jobs += [(f"Google News: {q}", lambda q=q: fetch_query(q, days=days))
             for q in (extra_queries or []) if not re.search(r"[\u0E00-\u0E7F]", q)]
    if world:
        jobs += [(name, lambda n=name, u=url: fetch_feed(n, u)) for name, url in DIRECT_FEEDS.items()]

    def run(job):
        name, fn = job
        try:
            return fn()
        except (requests.RequestException, ET.ParseError) as e:
            log(f"ข้ามแหล่ง '{name}': {e}")
            return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    seen, out = set(), []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for articles in pool.map(run, jobs):
            for a in articles:
                key = _norm(a.title)
                if key and key not in seen and a.published >= cutoff:
                    seen.add(key)
                    out.append(a)
    return out


def load_sample(path: Path = SAMPLE_JSON) -> list[Article]:
    with open(path, encoding="utf-8") as f:
        return [Article.from_dict(d) for d in json.load(f)]


def save_articles(articles: list[Article], path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump([a.to_dict() for a in articles], f, ensure_ascii=False, indent=1)
