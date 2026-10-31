from unrest_watch.geo import default_gazetteer, haversine_km


def test_haversine_bangkok_chiang_mai():
    assert 570 < haversine_km(13.7563, 100.5018, 18.7883, 98.9853) < 600


def test_city_beats_country():
    g = default_gazetteer()
    assert g.locate("Myanmar junta airstrike near Mandalay").name == "Mandalay"
    assert g.locate("ตำรวจสลายการชุมนุมที่กรุงเทพฯ").name == "Bangkok"


def test_short_aliases_are_case_sensitive():
    g = default_gazetteer()
    assert g.locate("Protesters told us to leave") is None
    assert g.locate("US troops deployed").name == "United States"


def test_generic_thai_word_is_not_a_place():
    # "คนไทยในฝรั่งเศส" = Thais in France: the event is in France
    assert default_gazetteer().locate("สถานทูตเตือนคนไทยในฝรั่งเศส เลี่ยงพื้นที่ชุมนุม").name == "France"


def test_country_of():
    g = default_gazetteer()
    assert g.country_of(13.75, 100.5) == "Thailand"
    assert g.country_of(48.85, 2.35) == "France"
