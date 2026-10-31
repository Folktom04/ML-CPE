from datetime import datetime, timedelta, timezone

import pytest

from unrest_watch.collector import load_sample
from unrest_watch.geo import default_gazetteer
from unrest_watch.model import UnrestClassifier
from unrest_watch.pipeline import Event, build_events
from unrest_watch.risk import assess, level_for


@pytest.fixture(scope="module")
def sample():
    articles = load_sample()
    events, dropped = build_events(articles, UnrestClassifier().fit())
    return events, dropped, max(a.published for a in articles)


def _score(sample, place):
    events, _, now = sample
    p = default_gazetteer().find(place)
    return assess(events, p.lat, p.lon, now=now)


def test_noise_dropped_and_duplicates_merged(sample):
    events, dropped, _ = sample
    assert dropped >= 5
    bangkok_riots = [e for e in events if e.place and e.place.name == "Bangkok" and e.label == "riot"]
    assert len(bangkok_riots) == 1 and bangkok_riots[0].n_sources == 2  # Thai + English report


def test_risk_falls_with_distance(sample):
    bkk, cnx, phuket = (_score(sample, p).score for p in ["Bangkok", "Chiang Mai", "Phuket"])
    assert bkk > cnx and bkk > phuket
    assert _score(sample, "Bangkok").level in {"yellow", "orange"}
    assert _score(sample, "Phuket").level == "green"


def test_planned_events_listed_as_upcoming(sample):
    a = _score(sample, "Bangkok")
    assert any("นัดรวมตัว" in t.event.title for t in a.upcoming)


def test_coup_affects_whole_country():
    g = default_gazetteer()
    now = datetime(2026, 10, 31, tzinfo=timezone.utc)
    coup = Event("Military seizes power", "coup", 0.95, 4.0, False,
                 g.find("Thailand"), now - timedelta(hours=2), ["A", "B", "C"])
    phuket = g.find("Phuket")
    a = assess([coup], phuket.lat, phuket.lon, now=now)
    assert a.level != "green"
    far = g.find("Paris")
    assert assess([coup], far.lat, far.lon, now=now).level == "green"


def test_many_far_events_do_not_saturate():
    g = default_gazetteer()
    now = datetime(2026, 10, 31, tzinfo=timezone.utc)
    paris = g.find("Paris")
    events = [Event(f"riot {i}", "riot", 0.9, 3.5, False, paris, now, ["x"]) for i in range(300)]
    bkk = g.find("Bangkok")
    assert assess(events, bkk.lat, bkk.lon, now=now).level == "green"


def test_levels():
    assert level_for(0.0)[0] == "green"
    assert level_for(0.3)[0] == "yellow"
    assert level_for(0.5)[0] == "orange"
    assert level_for(0.99)[0] == "red"
