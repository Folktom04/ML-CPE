"""Tiny offline gazetteer: finds the place a headline talks about, and distances."""
from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PLACES_CSV = Path(__file__).parent / "data" / "places.csv"            # hand-curated, wins ties
WORLD_CSV = Path(__file__).parent / "data" / "world_places.csv"      # GeoNames, CC BY 4.0
_THAI = re.compile(r"[\u0E00-\u0E7F]")
_WORD = re.compile(r"[^\W\d_]+(?:-[^\W\d_]+)*")
_KIND_RANK = {"city": 0, "region": 1, "country": 2}
MAX_NGRAM = 4
# "Russian drone strike on Ukrainian city": the place after the preposition is
# where it happened.
_PREP = re.compile(r"(?:\b(?:in|on|at|near|across|inside|into|over|outside)|ใน|ที่|ณ)\s*$", re.I)


@dataclass(frozen=True)
class Place:
    name: str
    kind: str  # "city", "region" (state/province) or "country"
    country: str
    lat: float
    lon: float
    radius_km: float
    continent: str = ""


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


def _read(path: Path):
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            place = Place(row["name"], row["kind"], row["country"], float(row["lat"]),
                          float(row["lon"]), float(row["radius_km"]), row.get("continent") or "")
            aliases = [row["name"]] + [a for a in (row["aliases"] or "").split("|") if a]
            yield place, aliases


class Gazetteer:
    """Finds the most specific place a headline mentions.

    The curated list is matched with regexes (it has odd aliases like "U.S."
    and demonyms). The large GeoNames list is matched by looking up the
    headline's 1-4 word sequences, exactly as capitalised in the data, so
    "nice weather" is not Nice, France.
    """

    def __init__(self, path: Path = PLACES_CSV, world_path: Path | None = WORLD_CSV) -> None:
        self.places: list[Place] = []
        self._patterns: list[tuple[re.Pattern, Place, int]] = []
        self._world_latin: dict[str, Place] = {}
        self._world_thai: list[tuple[str, Place]] = []
        if world_path is not None and world_path.exists():
            for place, aliases in _read(world_path):
                self.places.append(place)
                for alias in aliases:
                    if _THAI.search(alias):
                        self._world_thai.append((alias, place))
                        continue
                    old = self._world_latin.get(alias)
                    # same name in several places: keep the more specific, then bigger one
                    if old is None or (_KIND_RANK[place.kind], -place.radius_km) < \
                            (_KIND_RANK[old.kind], -old.radius_km):
                        self._world_latin[alias] = place
        curated = set()
        for place, aliases in _read(path):
            self.places.insert(0, place)
            for alias in aliases:
                world = self._world_latin.get(alias)
                if place.kind == "country" and world and world.kind != "country" and alias != place.name:
                    continue  # "São Paulo" listed under Brazil: the city entry is more precise
                self._patterns.append((_alias_pattern(alias), place, len(alias)))
                curated.add(alias.lower())
        # the curated entry wins when both lists know a name
        self._world_latin = {a: p for a, p in self._world_latin.items() if a.lower() not in curated}
        self._world_thai = [(a, p) for a, p in self._world_thai if a.lower() not in curated]

    def _hits(self, text: str):
        for pattern, place, length in self._patterns:
            m = pattern.search(text)
            if m:
                yield (_KIND_RANK[place.kind], m.start(), 0, -length, place)
        words = list(_WORD.finditer(text))
        for i in range(len(words)):
            for n in range(1, MAX_NGRAM + 1):
                if i + n > len(words):
                    break
                start, end = words[i].start(), words[i + n - 1].end()
                cand = text[start:end]
                if n > 1 and cand != " ".join(w.group() for w in words[i:i + n]):
                    break  # words not separated by single spaces
                place = self._world_latin.get(cand)
                if place:
                    yield (_KIND_RANK[place.kind], start, 1, -len(cand), place)
        for alias, place in self._world_thai:
            pos = text.find(alias)
            if pos >= 0:
                yield (_KIND_RANK[place.kind], pos, 1, -len(alias), place)

    def locate(self, text: str) -> Place | None:
        """Most specific place: city > state/province > country, then one that
        follows "in/on/at", then the earliest mention."""
        def key(h):
            kind, pos, prio, neg_len, _ = h
            return (kind, not _PREP.search(text[max(0, pos - 12):pos]), pos, prio, neg_len)
        best = min(self._hits(text), key=key, default=None)
        return best[4] if best else None

    def find(self, name: str) -> Place | None:
        key = name.strip().lower()
        for p in self.places:
            if p.name.lower() == key:
                return p
        return self.locate(name)

    def country_of(self, lat: float, lon: float) -> str | None:
        """Country of the nearest known city."""
        best = min((p for p in self.places if p.kind == "city"),
                   key=lambda p: haversine_km(lat, lon, p.lat, p.lon))
        return best.country


_REGIONS = {
    "เอเชียตะวันออกเฉียงใต้": ["Thailand", "Myanmar", "Cambodia", "Laos", "Malaysia", "Vietnam",
                               "Indonesia", "Philippines", "Singapore", "Brunei", "Timor Leste"],
    "เอเชียตะวันออก/ใต้/กลาง": ["China", "Taiwan", "Japan", "South Korea", "North Korea", "India",
                                "Pakistan", "Bangladesh", "Nepal", "Sri Lanka", "Afghanistan", "Kazakhstan"],
    "ตะวันออกกลาง": ["Kuwait", "Bahrain", "Oman", "Iran", "Iraq", "Syria", "Lebanon", "Israel", "Palestine", "Jordan", "Saudi Arabia",
                     "Yemen", "United Arab Emirates", "Qatar", "Turkey"],
    "แอฟริกา": ["Egypt", "Libya", "Tunisia", "Algeria", "Morocco", "Sudan", "South Sudan", "Ethiopia",
                "Somalia", "Kenya", "Uganda", "DR Congo", "Nigeria", "Niger", "Mali", "Burkina Faso",
                "Chad", "Cameroon", "Mozambique", "South Africa", "Madagascar"],
    "ยุโรป/รัสเซีย": ["United Kingdom", "Ireland", "France", "Germany", "Netherlands", "Belgium", "Spain",
                      "Portugal", "Italy", "Greece", "Serbia", "Kosovo", "Poland", "Ukraine", "Russia",
                      "Belarus", "Georgia", "Armenia", "Azerbaijan", "Hungary", "Romania", "Bulgaria",
                      "Slovakia", "Sweden"],
    "อเมริกา": ["Haiti", "Mexico", "United States", "Puerto Rico", "Canada", "Colombia", "Venezuela",
                "Ecuador", "Peru", "Bolivia", "Chile", "Argentina", "Brazil"],
    "โอเชียเนีย": ["Australia", "New Zealand", "Papua New Guinea"],
}
REGION_OF = {country: region for region, names in _REGIONS.items() for country in names}


_CONTINENT = {"AS": "เอเชียตะวันออก/ใต้/กลาง", "EU": "ยุโรป/รัสเซีย", "AF": "แอฟริกา",
              "NA": "อเมริกา", "SA": "อเมริกา", "OC": "โอเชียเนีย"}


def region_of(place: "Place") -> str:
    return REGION_OF.get(place.country) or _CONTINENT.get(place.continent, "อื่น ๆ")


@lru_cache(maxsize=1)
def default_gazetteer() -> Gazetteer:
    return Gazetteer()
