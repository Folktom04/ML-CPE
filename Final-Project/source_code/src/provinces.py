"""Day 21: coordinates of Thailand's 77 provinces for the app's "pick a province" fallback.

Used when the user denies location permission (or prefers not to use GPS): the app then asks
``/predict`` for the provincial capital's coordinates. The coordinates are looked up once with
the Open-Meteo Geocoding API (data from GeoNames, CC BY 4.0; see ``docs/datasets.md``) instead
of being typed by hand. For each province the capital town is taken: GeoNames feature code
``PPLA`` (seat of a first-order administrative division) or ``PPLC`` (Bangkok), and its
``admin1`` must be the province that was searched for, otherwise the build fails.

Run from ``Final-Project/``::

    .venv\\Scripts\\python.exe -m src.provinces   (with PYTHONPATH=source_code)

Raw responses are cached in ``dataset/raw/geocoding/``; the table is written to
``source_code/app/src/data/provinces.json``.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import requests
from src.fetch_data import ROOT, get_json, make_session

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
CACHE_DIR = ROOT / "dataset" / "raw" / "geocoding"
APP_JSON = ROOT / "source_code" / "app" / "src" / "data" / "provinces.json"
CAPITAL_CODES = ("PPLC", "PPLA")
SOURCE = "Open-Meteo Geocoding API (GeoNames, CC BY 4.0)"

log = logging.getLogger(__name__)

# (English name used in the search, Thai name, other English spellings of the province)
PROVINCES: list[tuple[str, str, tuple[str, ...]]] = [
    ("Bangkok", "กรุงเทพมหานคร", ("Krung Thep Maha Nakhon",)),
    ("Krabi", "กระบี่", ()),
    ("Kanchanaburi", "กาญจนบุรี", ()),
    ("Kalasin", "กาฬสินธุ์", ()),
    ("Kamphaeng Phet", "กำแพงเพชร", ()),
    ("Khon Kaen", "ขอนแก่น", ()),
    ("Chanthaburi", "จันทบุรี", ()),
    ("Chachoengsao", "ฉะเชิงเทรา", ()),
    ("Chon Buri", "ชลบุรี", ("Chonburi",)),
    ("Chai Nat", "ชัยนาท", ("Chainat",)),
    ("Chaiyaphum", "ชัยภูมิ", ()),
    ("Chumphon", "ชุมพร", ()),
    ("Chiang Rai", "เชียงราย", ()),
    ("Chiang Mai", "เชียงใหม่", ()),
    ("Trang", "ตรัง", ()),
    ("Trat", "ตราด", ()),
    ("Tak", "ตาก", ()),
    ("Nakhon Nayok", "นครนายก", ()),
    ("Nakhon Pathom", "นครปฐม", ()),
    ("Nakhon Phanom", "นครพนม", ()),
    ("Nakhon Ratchasima", "นครราชสีมา", ()),
    ("Nakhon Si Thammarat", "นครศรีธรรมราช", ()),
    ("Nakhon Sawan", "นครสวรรค์", ()),
    ("Nonthaburi", "นนทบุรี", ()),
    ("Narathiwat", "นราธิวาส", ()),
    ("Nan", "น่าน", ()),
    ("Bueng Kan", "บึงกาฬ", ("Bueng Kal", "Bungkan")),
    ("Buri Ram", "บุรีรัมย์", ("Buriram",)),
    ("Pathum Thani", "ปทุมธานี", ()),
    ("Prachuap Khiri Khan", "ประจวบคีรีขันธ์", ()),
    ("Prachin Buri", "ปราจีนบุรี", ("Prachinburi",)),
    ("Pattani", "ปัตตานี", ()),
    ("Phra Nakhon Si Ayutthaya", "พระนครศรีอยุธยา", ("Ayutthaya",)),
    ("Phayao", "พะเยา", ()),
    ("Phangnga", "พังงา", ("Phang Nga", "Phang-nga")),
    ("Phatthalung", "พัทลุง", ()),
    ("Phichit", "พิจิตร", ()),
    ("Phitsanulok", "พิษณุโลก", ()),
    ("Phetchaburi", "เพชรบุรี", ()),
    ("Phetchabun", "เพชรบูรณ์", ()),
    ("Phrae", "แพร่", ()),
    ("Phuket", "ภูเก็ต", ()),
    ("Maha Sarakham", "มหาสารคาม", ()),
    ("Mukdahan", "มุกดาหาร", ()),
    ("Mae Hong Son", "แม่ฮ่องสอน", ()),
    ("Yasothon", "ยโสธร", ()),
    ("Yala", "ยะลา", ()),
    ("Roi Et", "ร้อยเอ็ด", ()),
    ("Ranong", "ระนอง", ()),
    ("Rayong", "ระยอง", ()),
    ("Ratchaburi", "ราชบุรี", ()),
    ("Lop Buri", "ลพบุรี", ("Lopburi",)),
    ("Lampang", "ลำปาง", ()),
    ("Lamphun", "ลำพูน", ()),
    ("Loei", "เลย", ()),
    ("Si Sa Ket", "ศรีสะเกษ", ("Sisaket",)),
    ("Sakon Nakhon", "สกลนคร", ()),
    ("Songkhla", "สงขลา", ()),
    ("Satun", "สตูล", ()),
    ("Samut Prakan", "สมุทรปราการ", ()),
    ("Samut Songkhram", "สมุทรสงคราม", ()),
    ("Samut Sakhon", "สมุทรสาคร", ()),
    ("Sa Kaeo", "สระแก้ว", ()),
    ("Saraburi", "สระบุรี", ()),
    ("Sing Buri", "สิงห์บุรี", ("Singburi",)),
    ("Sukhothai", "สุโขทัย", ()),
    ("Suphan Buri", "สุพรรณบุรี", ("Suphanburi",)),
    ("Surat Thani", "สุราษฎร์ธานี", ()),
    ("Surin", "สุรินทร์", ()),
    ("Nong Khai", "หนองคาย", ()),
    ("Nong Bua Lam Phu", "หนองบัวลำภู", ("Nong Bua Lamphu",)),
    ("Ang Thong", "อ่างทอง", ()),
    ("Amnat Charoen", "อำนาจเจริญ", ()),
    ("Udon Thani", "อุดรธานี", ()),
    ("Uttaradit", "อุตรดิตถ์", ()),
    ("Uthai Thani", "อุทัยธานี", ()),
    ("Ubon Ratchathani", "อุบลราชธานี", ()),
]


def normalize_name(name: str) -> str:
    """Lower-case a place name and drop spaces, dashes and the words "province"/"changwat".

    Args:
        name: Place or province name.

    Returns:
        Comparable key, e.g. ``"Chon Buri"`` and ``"Chonburi Province"`` -> ``"chonburi"``.
    """
    key = re.sub(r"\b(province|changwat)\b", "", name.lower())
    return re.sub(r"[\s\-']", "", key)


def cache_key(query: str) -> str:
    """File-safe cache name that keeps different spellings apart ("Phang Nga" != "Phangnga").

    Args:
        query: Search text.

    Returns:
        Lower-case name with every non-alphanumeric run replaced by ``_``.
    """
    return re.sub(r"[^a-z0-9]+", "_", query.lower()).strip("_")


def pick_capital(results: list[dict[str, Any]], names: tuple[str, ...]) -> dict[str, Any] | None:
    """The provincial capital among geocoding results, or None.

    Args:
        results: ``results`` list of an Open-Meteo geocoding response.
        names: Accepted English names of the province (for the ``admin1`` check).

    Returns:
        The most populous Thai result whose feature code is in ``CAPITAL_CODES`` and whose
        ``admin1`` is one of ``names``; None if there is none.
    """
    keys = {normalize_name(n) for n in names}
    ok = [
        r
        for r in results
        if r.get("country_code") == "TH"
        and r.get("feature_code") in CAPITAL_CODES
        and normalize_name(str(r.get("admin1", ""))) in keys
    ]
    return max(ok, key=lambda r: r.get("population") or 0, default=None)


def lookup_province(
    name_en: str, aliases: tuple[str, ...] = (), session: requests.Session | None = None
) -> dict[str, Any]:
    """Geocode one province's capital (tries the name, then each alias; cached per query).

    Args:
        name_en: English province name.
        aliases: Other spellings to try when the name finds no capital.
        session: HTTP session (retrying one by default).

    Returns:
        The chosen geocoding result.

    Raises:
        LookupError: If no capital of that province is found under any spelling.
    """
    names = (name_en, *aliases)
    for query in names:
        params = {"name": query, "count": 20, "language": "en", "countryCode": "TH"}
        cache = CACHE_DIR / f"{cache_key(query)}.json"
        payload = get_json(GEOCODING_URL, params, cache, session=session, timeout=30)
        hit = pick_capital(payload.get("results") or [], names)
        if hit is not None:
            return hit
    raise LookupError(f"no provincial capital found for {name_en!r} (tried {names})")


def build_table(session: requests.Session | None = None) -> list[dict[str, Any]]:
    """All 77 provinces with the capital's coordinates, in the order of ``PROVINCES``.

    Args:
        session: HTTP session (retrying one by default).

    Returns:
        Rows ``{name_th, name_en, lat, lon, geonames_id, feature_code}`` (coordinates rounded
        to 0.01°, the resolution the API caches and the database stores).
    """
    session = session or make_session()
    rows = []
    for name_en, name_th, aliases in PROVINCES:
        hit = lookup_province(name_en, aliases, session=session)
        rows.append(
            {
                "name_th": name_th,
                "name_en": name_en,
                "lat": round(float(hit["latitude"]), 2),
                "lon": round(float(hit["longitude"]), 2),
                "geonames_id": int(hit["id"]),
                "feature_code": hit["feature_code"],
            }
        )
    return rows


def write_app_json(rows: list[dict[str, Any]], path: Path = APP_JSON) -> Path:
    """Write the province table for the app, with its source and licence.

    Args:
        rows: Output of ``build_table``.
        path: Target file.

    Returns:
        The written path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"source": SOURCE, "provinces": rows}
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    out = write_app_json(build_table())
    print(f"wrote {out}")
