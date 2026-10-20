"""Tests that run without model files (a fake LLM stands in for llama.cpp)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from textassist import Settings, TextAssistant  # noqa: E402
from textassist import fallback, textutil  # noqa: E402


class FakeLLM:
    """Returns canned answers and records the prompts it got."""

    def __init__(self, reply, models=("general", "translate")):
        self.reply = reply
        self.models = set(models)
        self.calls = []

    def available(self, key):
        return key in self.models

    def chat(self, key, messages, max_tokens=1024, temperature=None):
        self.calls.append((key, messages))
        return self.reply(messages[-1]["content"]) if callable(self.reply) else self.reply


def make(reply, models=("general", "translate")):
    llm = FakeLLM(reply, models)
    return TextAssistant(Settings(model_dir=Path("/nonexistent")), llm=llm), llm


# ----- text utilities -----

def test_detect_language():
    assert textutil.detect_language("สวัสดีครับ") == "th"
    assert textutil.detect_language("Hello there") == "en"
    assert textutil.detect_language("こんにちは") == "ja"
    assert textutil.detect_language("你好") == "zh"


def test_clean_output_strips_labels_and_markdown():
    assert textutil.clean_output("ประโยคที่แก้แล้ว: **วันนี้** ร้อน") == "วันนี้ ร้อน"
    assert textutil.clean_output('"Hello"') == "Hello"
    assert textutil.clean_output("Translation: Hi") == "Hi"


def test_split_paragraphs_keeps_layout():
    text = "ย่อหน้าแรก\n\nย่อหน้าที่สอง\nบรรทัดสาม"
    assert "".join(textutil.split_paragraphs(text)) == text


def test_keep_spelling_fixes_only():
    before = "ขอบคุณที่ช่วยอนุญาติให้ดิฉันลางาน"
    after = "ขอบคุณที่ช่วยอนุญาตให้ดิฉันลาหยุด"
    out = textutil.keep_spelling_fixes_only(before, after)
    assert "อนุญาต" in out and "อนุญาติ" not in out  # spelling fix kept
    assert out.endswith("ลางาน")                       # rewording undone


def test_keep_spelling_fixes_does_not_drop_negation():
    assert textutil.keep_spelling_fixes_only("ฉันไม่ชอบกาแฟ", "ฉันชอบกาแฟ") == "ฉันไม่ชอบกาแฟ"


def test_missing_numbers():
    assert textutil.missing_numbers("นัดวันที่ 5 เวลา 10:30", "นัดวันที่ 5") == ["10:30"]
    assert textutil.missing_numbers("ราคา ๑๒๐ บาท", "costs 120 baht") == []


def test_fix_thai_register():
    assert textutil.fix_thai_register("ไปกินข้าวกันครับ", "casual", "male") == "ไปกินข้าวกัน"
    assert textutil.fix_thai_register("ขอบคุณค่ะ", "polite", "male") == "ขอบคุณครับ"
    assert textutil.fix_thai_register("ดิฉัน/ผมขอบคุณครับ/ค่ะ", "polite", "female") == "ดิฉันขอบคุณค่ะ"


def test_diff_segments_rebuild_both_sides():
    before, after = "ร้านปิดเพาะฝนตก", "ร้านปิดเพราะฝนตก"
    segs = textutil.diff_segments(before, after)
    assert "".join(s["text"] for s in segs if s["op"] != "ins") == before
    assert "".join(s["text"] for s in segs if s["op"] != "del") == after


# ----- rule-based fallback -----

def test_fallback_spell():
    assert fallback.spell_correct("อนุญาติให้ใช้ได้") == "อนุญาตให้ใช้ได้"
    assert fallback.spell_correct("ร้อนมากกกก วันนี้") == "ร้อนมาก วันนี้"
    assert fallback.spell_correct("I recieve it") == "I receive it"


def test_fallback_style():
    assert fallback.rewrite_style("กูกินข้าว", "formal") == "ข้าพเจ้ารับประทานข้าว"
    assert fallback.rewrite_style("กูกินข้าว", "polite", "male") == "ผมทานข้าวครับ"


def test_no_model_uses_rules():
    a, _ = make("unused", models=())
    r = a.correct("ขอบคุณนะค่ะ")
    assert r.engine == "rules" and r.text == "ขอบคุณนะคะ" and r.warnings
    with pytest.raises(RuntimeError):
        a.translate("สวัสดี", "en")


# ----- with the (fake) model -----

def test_correct_uses_model_and_reports_changes():
    a, llm = make("ร้านปิดเพราะเจ้าของไม่สบาย")
    r = a.correct("ร้านปิดเพาะเจ้าของไม่สะบาย")
    assert r.text == "ร้านปิดเพราะเจ้าของไม่สบาย"
    assert {"from": "เพาะ", "to": "เพราะ"} in r.changes
    assert r.extra["diff"]


def test_correct_rejects_rewrite():
    a, _ = make("เนื้อหาที่ต่างจากต้นฉบับไปอย่างสิ้นเชิงโดยไม่มีอะไรเหมือนเดิมเลย")
    r = a.correct("อนุญาติให้ใช้ห้องประชุมได้ตั้งแต่บ่ายสองโมง")
    assert r.text == "อนุญาตให้ใช้ห้องประชุมได้ตั้งแต่บ่ายสองโมง"  # fell back to rules
    assert r.warnings


def test_correct_keeps_paragraphs():
    a, llm = make(lambda t: t)
    text = "บรรทัดหนึ่ง\n\nบรรทัดสอง"
    assert a.correct(text).text == text
    assert len(llm.calls) == 2


def test_rewrite_thai_and_english_prompts():
    a, llm = make("ข้าพเจ้าขอลาป่วยครับ")
    r = a.rewrite("กูป่วย", "formal", "male")
    assert r.text == "ข้าพเจ้าขอลาป่วย"  # ครับ removed in formal register
    assert "ทางการ" in llm.calls[-1][1][0]["content"]

    a, llm = make("I would like to know.")
    a.rewrite("I wanna know", "formal")
    assert llm.calls[-1][1][0]["content"].startswith("You are a professional editor")


def test_rewrite_warns_on_lost_numbers():
    a, _ = make("ขอลาวันที่ห้า")
    assert a.rewrite("ขอลาวันที่ 5", "polite").warnings


def test_rewrite_unknown_style():
    a, _ = make("x")
    with pytest.raises(ValueError):
        a.rewrite("ข้อความ", "pirate")


def test_translate_routes_models():
    a, llm = make("Hello")
    r = a.translate("สวัสดี", "en")
    assert r.engine == "translate" and r.extra["source"] == "th"

    a, llm = make("こんにちは")
    r = a.translate("สวัสดี", "ja")
    assert r.engine == "general"
    assert "Japanese" in llm.calls[-1][1][0]["content"]

    a, llm = make("Hello", models=("general",))
    assert a.translate("สวัสดี", "en").engine == "general"


def test_translate_glossary_and_back():
    a, llm = make(lambda t: "สวัสดี" if "English text into Thai" in t else "Contact HR")
    r = a.translate("ติดต่อฝ่ายบุคคล", "en", glossary={"ฝ่ายบุคคล": "HR"}, back_translate=True)
    assert 'Translate "ฝ่ายบุคคล" as "HR"' in llm.calls[0][1][-1]["content"]
    assert r.extra["back_translation"] == "สวัสดี"


def test_translate_same_language():
    a, llm = make("x")
    assert a.translate("hello", "en").text == "hello" and not llm.calls
