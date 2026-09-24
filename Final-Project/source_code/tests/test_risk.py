"""Tests for src.risk."""

import pytest

from src import risk


def test_normalize_skin_type_accepts_roman_and_int():
    assert risk.normalize_skin_type("iii") == "III"
    assert risk.normalize_skin_type(6) == "VI"
    for bad in (0, 7, "VII", True, None):
        with pytest.raises(ValueError):
            risk.normalize_skin_type(bad)


def test_burn_minutes_formula():
    # MED / (UVI * 0.025 * 60): type II (250 J/m²) at UVI 10 -> 250 / 15 = 16.7 -> 16
    assert risk.burn_minutes(10, "II") == 16
    assert risk.burn_minutes(10, "VI") == 66  # 1000 / 15
    assert risk.burn_minutes(12, "I") < risk.burn_minutes(6, "I")
    assert risk.burn_minutes(0.2, "I") is None
    assert risk.burn_minutes(float("nan"), "I") is None


def test_level_index_matches_who_bands():
    assert [risk.level_index(u) for u in (0, 2.4, 2.5, 5, 7.4, 7.5, 10.4, 10.5, 14)] == [
        0,
        0,
        1,
        1,
        2,
        3,
        3,
        4,
        4,
    ]


def test_assess_uses_upper_bound_for_warnings():
    r = risk.assess(7.0, (5.5, 9.0), "II")
    assert r["level"] == "สูง" and r["level_en"] == "High" and r["color"] == "#E36B12"
    assert r["alert_level"] == "สูงมาก" and r["alert_level_index"] == 3
    assert r["burn_minutes"] == risk.burn_minutes(9.0, "II")
    assert any("SPF 50+" in a for a in r["advice"])
    assert any(str(r["burn_minutes"]) in a for a in r["advice"])
    assert "ไม่ใช่การวินิจฉัยทางการแพทย์" in r["disclaimer"]


def test_assess_low_uv_and_bad_range():
    r = risk.assess(0.1, (0.0, 0.3), 3)
    assert r["burn_minutes"] is None and r["level"] == "ต่ำ"
    assert not any("นาที" in a for a in r["advice"])
    with pytest.raises(ValueError):
        risk.assess(5, (6, 4), "I")
    # the upper bound is never below the point estimate
    assert risk.assess(8, (6, 7.5), "I")["uvi_range"][1] == 8
