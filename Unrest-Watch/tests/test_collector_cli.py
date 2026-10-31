import json

from unrest_watch.cli import main
from unrest_watch.collector import parse_rss

RSS = b"""<?xml version="1.0"?><rss><channel>
<item><title>Clashes erupt in capital - Reuters</title><link>http://x/1</link>
<pubDate>Sat, 31 Oct 2026 06:37:00 GMT</pubDate><source url="http://r">Reuters</source></item>
<item><title>Port workers strike over arms shipments | The Bangkok Insight - Bangkok Insight</title><link>http://x/3</link><pubDate>Sat, 31 Oct 2026 06:37:00 GMT</pubDate></item>
<item><title>No source suffix here</title><link>http://x/2</link><pubDate>bad date</pubDate></item>
</channel></rss>"""


def test_parse_rss():
    items = parse_rss(RSS)
    assert items[0].title == "Clashes erupt in capital"
    assert items[0].source == "Reuters"
    assert items[0].published.tzinfo is not None
    assert items[1].title == "Port workers strike over arms shipments"
    assert items[2].title == "No source suffix here"


def test_cli_offline_json(capsys):
    assert main(["--offline", "--place", "Bangkok", "--adults", "2", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["level"] in {"green", "yellow", "orange", "red"}
    assert out["plan"]["balanced_days"] >= out["plan"]["days"]


def test_cli_text_with_inventory(tmp_path, capsys):
    inv = tmp_path / "inv.json"
    inv.write_text(json.dumps({"rice": 1, "canned_fish": 10, "water": 2}))
    assert main(["--offline", "--place", "เชียงใหม่", "--inventory", str(inv)]) == 0
    text = capsys.readouterr().out
    assert "หมู่ 1" in text and "หมู่ 5" in text and "ของที่คุณมีอยู่" in text


def test_cli_unknown_place():
    assert main(["--offline", "--place", "Atlantis"]) == 2
