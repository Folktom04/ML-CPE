"""Tests for src.risk."""

import json
from pathlib import Path

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


def test_assess_alerts_follow_alert_uvi_not_the_displayed_range():
    # point 9.5 above q90 8.0: the displayed range is widened, warnings still use q90
    r = risk.assess(9.5, (6.0, 9.5), "II", alert_uvi=8.0)
    assert r["uvi_range"] == [6.0, 9.5]
    assert r["alert_uvi"] == 8.0 and r["alert_level_index"] == risk.level_index(8.0)
    assert r["burn_minutes"] == risk.burn_minutes(8.0, "II")
    assert r["advice"] == risk.advice(8.0, "II")
    assert risk.assess(7.0, (5.5, 9.0), "II")["alert_uvi"] == 9.0  # default: upper bound


def test_assess_low_uv_and_bad_range():
    r = risk.assess(0.1, (0.0, 0.3), 3)
    assert r["burn_minutes"] is None and r["level"] == "ต่ำ"
    assert not any("นาที" in a for a in r["advice"])
    with pytest.raises(ValueError):
        risk.assess(5, (6, 4), "I")
    # the upper bound is never below the point estimate
    assert risk.assess(8, (6, 7.5), "I")["uvi_range"][1] == 8


CASES = json.loads((Path(__file__).parent / "who_rounding_cases.json").read_text(encoding="utf-8"))
LEVEL_OF_THRESHOLD = {6: 2, 8: 3, 11: 4}  # app alert choices = lower bound of สูง/สูงมาก/รุนแรงมาก


@pytest.mark.parametrize("uvi,level", CASES["cases"])
def test_one_rounding_rule_for_levels_card_and_alerts(uvi, level):
    """who_level (chart hours, API), assess (main card) and the alert checks agree."""
    from src.metrics import who_level

    assert int(who_level(uvi)) == level
    r = risk.assess(uvi, (max(uvi, 0), max(uvi, 0)), "III", alert_uvi=uvi)
    assert r["level_index"] == level and r["alert_level_index"] == level
    assert r["level"] == risk.WHO_LEVELS[level]
    for threshold, lvl in LEVEL_OF_THRESHOLD.items():
        # an alert fires exactly when the shown level is at or above the threshold's level
        assert risk.reaches_alert(uvi, threshold) == (level >= lvl)
        # "safe again" (alert - 2) is never true while the alert would still fire
        assert not (risk.is_safe_again(uvi, threshold - 2) and risk.reaches_alert(uvi, threshold))


def test_7_8_is_very_high_and_reaches_alert_8():
    assert risk.assess(7.8, (7.0, 8.2), "III")["level"] == "สูงมาก"
    assert risk.reaches_alert(7.8, 8) and not risk.reaches_alert(7.49, 8)
    assert risk.is_safe_again(5.49, 6) and not risk.is_safe_again(5.5, 6)
