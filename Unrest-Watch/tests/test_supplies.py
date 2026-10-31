import pytest

from unrest_watch.supplies import (CATALOG, GROUP_METRIC, Household, checklist,
                                   days_supported, plan)


@pytest.mark.parametrize("household", [Household(1), Household(2, 2, 0), Household(2, 1, 2)])
@pytest.mark.parametrize("days", [3, 7, 14, 30])
def test_plan_covers_all_five_groups_and_water(household, days):
    p = plan(household, days)
    cov = p["coverage"]
    for metric, d in cov["per_metric"].items():
        assert d >= days, f"{metric} only lasts {d:.1f} of {days} days"
    used_groups = {CATALOG[k].group for k, q in p["quantities"].items() if q}
    assert {1, 2, 3, 4, 5} <= used_groups


def test_short_shelf_life_items_skipped_for_long_plans():
    assert plan(Household(2), 30)["quantities"].get("eggs", 0) == 0
    assert plan(Household(2), 7)["quantities"].get("eggs", 0) > 0


def test_days_supported_finds_bottleneck():
    # lots of rice and water, nothing else: survive on energy, but no veg/fruit
    c = days_supported({"rice": 2, "water": 10}, Household(1))
    assert c["limiting"] in {"veg", "fruit"}
    assert c["balanced_days"] == 0
    assert c["survival_days"] > 10


def test_cooking_water_is_subtracted():
    dry = days_supported({"water": 1}, Household(1))["per_metric"]["water"]
    with_rice = days_supported({"water": 1, "rice": 1}, Household(1))["per_metric"]["water"]
    assert with_rice < dry


def test_unknown_item_raises():
    with pytest.raises(KeyError):
        days_supported({"caviar": 3}, Household(1))


def test_checklist_grows_with_level():
    assert len(checklist("green")) < len(checklist("yellow")) < len(checklist("red"))


def test_group_metric_mapping_is_complete():
    assert set(GROUP_METRIC) == {1, 2, 3, 4, 5}
