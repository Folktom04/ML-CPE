from datetime import datetime, timedelta, timezone

from unrest_watch.cli import main
from unrest_watch.collector import parse_rss
from unrest_watch.geo import default_gazetteer
from unrest_watch.pipeline import Event
from unrest_watch.world import LiveTracker, ago_th, recent, region

NOW = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)
G = default_gazetteer()


def ev(title, label="riot", place="Paris", hours=1.0, sev=3.5, sources=("A", "B")):
    return Event(title, label, 0.9, sev, False, G.find(place) if place else None,
                 NOW - timedelta(hours=hours), list(sources), headlines=[title])


def test_world_gazetteer_knows_small_conflict_cities():
    assert G.locate("Russian shelling in Sumy region").name == "Sumy"
    assert G.locate("13 killed by airstrike in Taiz").country == "Yemen"
    assert G.locate("Nigerian troops kill militants in Borno").kind == "region"


def test_place_after_preposition_wins():
    assert G.locate("Russia drone strike on Ukrainian railway station").name == "Ukraine"


def test_curated_names_win_and_city_beats_country_alias():
    assert G.locate("Protest in São Paulo").name == "São Paulo"
    assert G.find("Bangkok").country == "Thailand"


def test_regions():
    assert region(ev("x", place="Bangkok")) == "เอเชียตะวันออกเฉียงใต้"
    assert region(ev("x", place="Taiz")) == "ตะวันออกกลาง"
    assert region(ev("x", place="Sumy")) == "ยุโรป/รัสเซีย"


def test_recent_filters_old_and_unlocated_single_source():
    events = [ev("fresh"), ev("old", hours=40),
              ev("nowhere, one source", place=None, sources=("A",)),
              ev("nowhere, confirmed", place=None, sev=4.5, sources=("A", "B", "C"))]
    titles = [e.title for e in recent(events, NOW, hours=24)]
    assert "fresh" in titles and "nowhere, confirmed" in titles
    assert "old" not in titles and "nowhere, one source" not in titles


def test_recent_ranks_severe_first():
    events = [ev("protest", label="protest", sev=2.0), ev("bombing", label="terrorism", sev=5.0)]
    assert recent(events, NOW, 24)[0].title == "bombing"


def test_live_tracker_reports_only_changes():
    t = LiveTracker()
    first = [ev("Clashes in Paris", hours=1)]
    assert [c.is_new for c in t.update(first, NOW)] == [True]
    assert t.update(first, NOW + timedelta(minutes=5)) == []  # nothing changed

    later = NOW + timedelta(minutes=10)
    newer_report = Event("Clashes in Paris", "riot", 0.9, 3.5, False, G.find("Paris"),
                         later, ["A", "B", "C"], headlines=["Clashes in Paris", "Paris riots spread"])
    fresh = Event("Bomb in Taiz", "terrorism", 0.9, 5.0, False, G.find("Taiz"), later, ["A"],
                  headlines=["Bomb in Taiz"])
    old_but_unseen = ev("Old protest in Rome", label="protest", place="Rome", hours=10)
    changes = t.update([newer_report, fresh, old_but_unseen], later)
    assert {(c.event.title, c.is_new) for c in changes} == {("Clashes in Paris", False),
                                                            ("Bomb in Taiz", True)}


def test_ago_th():
    assert ago_th(NOW - timedelta(minutes=5), NOW) == "5 นาทีที่แล้ว"
    assert ago_th(NOW - timedelta(hours=3), NOW) == "3 ชม.ที่แล้ว"
    assert ago_th(NOW - timedelta(days=3), NOW) == "3 วันที่แล้ว"


def test_parse_rdf_and_atom():
    rdf = b"""<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
      xmlns="http://purl.org/rss/1.0/" xmlns:dc="http://purl.org/dc/elements/1.1/">
      <item><title>Clashes - in the capital</title><link>http://dw/1</link>
      <dc:date>2026-10-31T07:26:00Z</dc:date></item></rdf:RDF>"""
    a = parse_rss(rdf, default_source="DW")[0]
    assert a.title == "Clashes - in the capital" and a.source == "DW"  # no suffix split
    assert a.published == datetime(2026, 10, 31, 7, 26, tzinfo=timezone.utc)
    atom = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Riot in port city</title>
      <link href="http://x/a"/><updated>2026-10-31T01:00:00Z</updated></entry></feed>"""
    a = parse_rss(atom, default_source="X")[0]
    assert a.url == "http://x/a" and a.title == "Riot in port city"


def test_cli_world_offline(capsys):
    assert main(["--world", "--offline", "--hours", "72"]) == 0
    out = capsys.readouterr().out
    assert "ทั่วโลก" in out and "แยกตามภูมิภาค" in out and "Mogadishu" in out
