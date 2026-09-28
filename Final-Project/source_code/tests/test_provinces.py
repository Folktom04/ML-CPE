"""Tests for src.provinces and the app's provinces.json (day 21)."""

import json

import pytest
from src import inference as inf
from src import provinces as prov

TABLE = json.loads(prov.APP_JSON.read_text(encoding="utf-8"))


def res(name, admin1, code="PPLA", country="TH", pop=1000, lat=14.0, lon=100.5):
    return {
        "id": 1,
        "name": name,
        "admin1": admin1,
        "feature_code": code,
        "country_code": country,
        "population": pop,
        "latitude": lat,
        "longitude": lon,
    }


def test_normalize_and_cache_key():
    assert prov.normalize_name("Chon Buri") == prov.normalize_name("Chonburi Province")
    assert prov.normalize_name("Phang-nga") == "phangnga"
    assert prov.cache_key("Phang Nga") != prov.cache_key("Phangnga")  # the day-21 bug
    assert prov.cache_key("Nong Bua Lam Phu") == "nong_bua_lam_phu"


def test_pick_capital_needs_capital_code_country_and_admin1():
    results = [
        res("Ban Phang Ngon", "Chanthaburi", code="PPL"),
        res("Phang Nga", "Phang Nga", pop=9676),
        res("Phang Nga", "Phang Nga", country="MY", pop=99999),
        res("Phang Nga village", "Krabi"),
    ]
    hit = prov.pick_capital(results, ("Phangnga", "Phang Nga"))
    assert hit["name"] == "Phang Nga" and hit["country_code"] == "TH"
    assert prov.pick_capital(results[:1], ("Phangnga",)) is None
    assert prov.pick_capital([res("Bangkok", "Bangkok", code="PPLC")], ("Bangkok",))


def test_lookup_tries_aliases_and_fails_loudly(monkeypatch, tmp_path):
    queries = []

    def fake_get_json(url, params, cache_path, session=None, timeout=0):
        queries.append((params["name"], cache_path.name))
        ok = params["name"] == "Phang Nga"
        return {"results": [res("Phang Nga", "Phang Nga")] if ok else []}

    monkeypatch.setattr(prov, "get_json", fake_get_json)
    monkeypatch.setattr(prov, "CACHE_DIR", tmp_path)
    assert prov.lookup_province("Phangnga", ("Phang Nga",))["name"] == "Phang Nga"
    assert queries == [("Phangnga", "phangnga.json"), ("Phang Nga", "phang_nga.json")]
    with pytest.raises(LookupError):
        prov.lookup_province("Atlantis", ("Atlantis City",))


def test_build_and_write(monkeypatch, tmp_path):
    monkeypatch.setattr(prov, "PROVINCES", [("Bangkok", "กรุงเทพมหานคร", ())])
    bkk = res("Bangkok", "Bangkok", "PPLC", lat=13.754, lon=100.5014)
    monkeypatch.setattr(prov, "lookup_province", lambda *a, **k: bkk)
    rows = prov.build_table(session=object())
    assert (rows[0]["lat"], rows[0]["lon"], rows[0]["feature_code"]) == (13.75, 100.5, "PPLC")
    out = prov.write_app_json(rows, tmp_path / "p.json")
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["source"] == prov.SOURCE and doc["provinces"][0]["name_th"] == "กรุงเทพมหานคร"


def test_app_table_has_77_unique_provinces_inside_thailand():
    rows = TABLE["provinces"]
    assert TABLE["source"] == "Open-Meteo Geocoding API (GeoNames, CC BY 4.0)"
    assert len(rows) == 77 == len(prov.PROVINCES)
    assert len({x["name_th"] for x in rows}) == 77 and len({x["name_en"] for x in rows}) == 77
    assert len({(x["lat"], x["lon"]) for x in rows}) == 77
    assert all(inf.in_thailand(x["lat"], x["lon"]) for x in rows)
    assert {x["feature_code"] for x in rows} == {"PPLA", "PPLC"}
    by_en = {x["name_en"]: x for x in rows}
    bkk = by_en["Bangkok"]
    assert (bkk["lat"], bkk["lon"]) == pytest.approx((13.75, 100.5), abs=0.05)
    pt, cm = by_en["Pathum Thani"], by_en["Chiang Mai"]
    assert inf.distance_km(pt["lat"], pt["lon"], 14.02, 100.52) < 5
    assert inf.distance_km(cm["lat"], cm["lon"], 18.79, 98.98) < 5
