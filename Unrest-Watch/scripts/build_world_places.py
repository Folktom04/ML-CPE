"""Builds unrest_watch/data/world_places.csv from GeoNames dumps.

Download into one folder (https://download.geonames.org/export/dump/):
  cities15000.zip (unzip it), countryInfo.txt, admin1CodesASCII.txt
then run:  python scripts/build_world_places.py <that folder>

GeoNames data is CC BY 4.0 (https://www.geonames.org).
"""
from __future__ import annotations

import csv
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "unrest_watch" / "data" / "world_places.csv"
MIN_CITY_POP = 100_000
MIN_ADMIN_POP = 300_000

# GeoNames name -> name used in places.csv
COUNTRY_RENAME = {
    "Democratic Republic of the Congo": "DR Congo",
    "The Netherlands": "Netherlands",
    "Palestinian Territory": "Palestine",
}
# City / region names that are also everyday English words or common first
# names; matching them would put events in the wrong place.
BLOCK = {
    "of", "the", "mobile", "reading", "nice", "bath", "split", "university", "university city",
    "victoria", "florence", "jackson", "lincoln", "hamilton", "washington", "independence",
    "orange", "sandy", "eagle", "sunrise", "deal", "march", "may", "police", "union", "concord",
    "columbia", "georgia", "jordan", "chad", "niger", "lafayette", "franklin", "henderson",
    "temple", "pearland", "plano", "irving", "garland", "frederick", "peoria", "joliet",
    "salem", "troy", "warren", "clinton", "marion", "aurora", "carmel", "denton", "edison",
    "gary", "kent", "norman", "pasadena", "spring", "vista", "west", "east", "north", "south",
    "central", "western", "eastern", "northern", "southern", "capital", "capital region",
    "centre", "center", "coast", "islands", "national capital", "federal capital territory",
    "orient", "littoral", "lakes", "highlands", "plateau", "upper", "lower", "middle",
    "white", "red sea", "mid", "bay", "island", "river", "liberty", "phoenix", "corona",
    "santa", "san", "la", "le", "el", "al", "most", "batman", "mandi", "gaza strip",
    "nation", "gold coast", "sunshine coast", "media", "progreso", "victory", "trump",
}
_SUFFIX = re.compile(r"\s+(oblast|province|region|governorate|state|prefecture|district|"
                     r"department|county|division|territory|krai|republic|voivodeship)$", re.I)
_THAI = re.compile(r"^[฀-๿\s]+$")


def thai_aliases(alt: str) -> list[str]:
    return sorted({a.strip() for a in alt.split(",") if _THAI.match(a.strip()) and len(a.strip()) >= 4})


def main(src: Path) -> None:
    countries = {}
    for line in open(src / "countryInfo.txt", encoding="utf-8"):
        if line.startswith("#"):
            continue
        f = line.rstrip("\n").split("\t")
        iso, name, area, continent = f[0], f[4], f[6], f[8]
        countries[iso] = {"name": COUNTRY_RENAME.get(name, name), "continent": continent,
                          "area": float(area or 1000)}

    admin_names = {}
    for line in open(src / "admin1CodesASCII.txt", encoding="utf-8"):
        code, name, ascii_name, _ = line.rstrip("\n").split("\t")
        admin_names[code] = ascii_name

    cities, capitals = [], {}
    admin_members = defaultdict(list)
    for line in open(src / "cities15000.txt", encoding="utf-8"):
        f = line.rstrip("\n").split("\t")
        name, ascii_name, alt = f[1], f[2], f[3]
        lat, lon, fcode, iso, admin1, pop = float(f[4]), float(f[5]), f[7], f[8], f[10], int(f[14] or 0)
        if iso not in countries:
            continue
        admin_members[f"{iso}.{admin1}"].append((lat, lon, pop))
        if fcode == "PPLC":
            capitals[iso] = (lat, lon)
        if pop >= MIN_CITY_POP or fcode == "PPLC":
            cities.append((name, ascii_name, alt, lat, lon, iso, pop))

    rows = []
    for name, ascii_name, alt, lat, lon, iso, pop in cities:
        aliases = {ascii_name} - {name} if ascii_name != name else set()
        radius = round(min(60, max(15, 8 * math.log10(pop / 1e4 + 1) * 4)))
        rows.append([name, "city", countries[iso]["name"], lat, lon, radius,
                     "|".join(sorted(aliases) + thai_aliases(alt)), countries[iso]["continent"]])

    for code, members in admin_members.items():
        name = admin_names.get(code)
        total = sum(p for *_, p in members)
        if not name or total < MIN_ADMIN_POP:
            continue
        iso = code.split(".")[0]
        lat = sum(la * p for la, _, p in members) / total
        lon = sum(lo * p for _, lo, p in members) / total
        spread = max(math.dist((lat, lon), (la, lo)) for la, lo, _ in members) * 111
        short = _SUFFIX.sub("", name)
        aliases = {name} - {short}
        rows.append([short, "region", countries[iso]["name"], round(lat, 4), round(lon, 4),
                     round(min(400, max(30, spread))), "|".join(sorted(aliases)),
                     countries[iso]["continent"]])

    for iso, c in countries.items():
        lat, lon = capitals.get(iso, (None, None))
        if lat is None:
            continue
        rows.append([c["name"], "country", c["name"], lat, lon,
                     round(min(2500, max(30, math.sqrt(c["area"]) / 2))), "", c["continent"]])

    kept = []
    for r in rows:
        if r[0].lower() in BLOCK or len(r[0]) < 4:
            continue
        r[6] = "|".join(a for a in r[6].split("|") if a and a.lower() not in BLOCK)
        kept.append(r)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "kind", "country", "lat", "lon", "radius_km", "aliases", "continent"])
        w.writerows(kept)
    by_kind = defaultdict(int)
    for r in kept:
        by_kind[r[1]] += 1
    print(f"wrote {len(kept)} places to {OUT} ({dict(by_kind)})")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
