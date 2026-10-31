"""Tiny offline gazetteer: finds the place a headline talks about, and distances."""
from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PLACES_CSV = Path(__file__).parent / "data" / "places.csv"
_THAI = re.compile(r"[฀-๿]")


@dataclass(frozen=True)
class Place:
    name: str
    kind: str  # "city" or "country"
    country: str
    lat: float
    lon: float
    radius_km: float


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _alias_pattern(alias: str) -> re.Pattern:
    if _THAI.search(alias):  # Thai has no spaces between words
        return re.compile(re.escape(alias))
    flags = 0 if len(alias) <= 3 else re.IGNORECASE  # "US" must not match "us"
    return re.compile(r"(?<![\w.])" + re.escape(alias) + r"(?![\w])", flags)


class Gazetteer:
    def __init__(self, path: Path = PLACES_CSV) -> None:
        self.places: list[Place] = []
        self._patterns: list[tuple[re.Pattern, Place, int]] = []
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                place = Place(row["name"], row["kind"], row["country"], float(row["lat"]),
                              float(row["lon"]), float(row["radius_km"]))
                self.places.append(place)
                names = [row["name"]] + [a for a in (row["aliases"] or "").split("|") if a]
                for alias in names:
                    self._patterns.append((_alias_pattern(alias), place, len(alias)))

    def locate(self, text: str) -> Place | None:
        """Most specific place in the text: cities beat countries, then earliest mention."""
        hits = []
        for pattern, place, length in self._patterns:
            m = pattern.search(text)
            if m:
                hits.append((place.kind != "city", m.start(), -length, place))
        if not hits:
            return None
        hits.sort(key=lambda h: h[:3])
        return hits[0][3]

    def find(self, name: str) -> Place | None:
        key = name.strip().lower()
        for p in self.places:
            if p.name.lower() == key:
                return p
        return self.locate(name)

    def country_of(self, lat: float, lon: float) -> str | None:
        """Country of the nearest known place (good enough for 'same country' checks)."""
        best = min(self.places, key=lambda p: haversine_km(lat, lon, p.lat, p.lon))
        return best.country


@lru_cache(maxsize=1)
def default_gazetteer() -> Gazetteer:
    return Gazetteer()
