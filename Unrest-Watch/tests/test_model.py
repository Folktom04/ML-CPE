import pytest

from unrest_watch.model import UnrestClassifier, casualty_boost, evaluate, is_planned


@pytest.fixture(scope="module")
def model():
    return UnrestClassifier().fit()


def test_cross_validation_is_reasonable():
    r = evaluate()
    assert r["macro_f1"] > 0.75
    assert r["relevance_accuracy"] > 0.82


@pytest.mark.parametrize("text", [
    "Riot Platforms (RIOT) stock jumps after bitcoin rally",
    "Peach Riot x KPop Demon Hunters collab comes to Pop Mart",
    "Riot Games teases new Valorant agent",
    "ทีมชาติไทยบุกถล่มคู่แข่ง 3-0 ศึกฟุตบอลอาเซียน",
])
def test_noise_is_filtered(model, text):
    assert not model.predict([text])[0].relevant


@pytest.mark.parametrize("text,label", [
    ("Riot police fire tear gas at protesters near parliament", "riot"),
    ("ตำรวจควบคุมฝูงชนสลายการชุมนุม ยิงแก๊สน้ำตา", "riot"),
    ("Car bomb explodes outside police headquarters, 12 killed", "terrorism"),
    ("Junta airstrike kills 30 villagers", "armed_conflict"),
    ("Military seizes power and suspends constitution", "coup"),
    ("Teachers march to ministry demanding pay rise", "protest"),
])
def test_event_types(model, text, label):
    p = model.predict([text])[0]
    assert p.label == label and p.relevant


def test_casualty_boost_scales_with_deaths():
    assert casualty_boost("Protest held in square") == 0
    assert casualty_boost("Clash leaves 3 dead") == 0.5
    assert casualty_boost("Bombing kills dozens") == 1.0
    assert casualty_boost("Airstrike kills 120 people") == 1.5
    assert casualty_boost("โดรนโจมตีโรงไฟฟ้า ไฟดับทั้งเมือง") == 0  # "ดับ" = blackout, not death


def test_planned_detection():
    assert is_planned("Activists plan mass rally this weekend")
    assert is_planned("กลุ่มผู้ชุมนุมนัดรวมตัวใหญ่วันเสาร์นี้")
    assert not is_planned("เคยถูกยิง 13 นัด")  # "นัด" = gunshots here
    assert not is_planned("Police dispersed the crowd last night")
