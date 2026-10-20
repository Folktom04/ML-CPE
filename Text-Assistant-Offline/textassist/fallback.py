"""Basic rule-based mode used when no model file is present.

Much weaker than the LLM, but works with only PyThaiNLP and pyspellchecker.
"""
import re

from .textutil import tokenize

# Commonly misspelt Thai words (wrong -> right).
THAI_COMMON_MISSPELLINGS = {
    "อนุญาติ": "อนุญาต", "โอกาศ": "โอกาส", "ศรีษะ": "ศีรษะ", "กระเพรา": "กะเพรา",
    "ผัดไท": "ผัดไทย", "เปอร์เซ็น": "เปอร์เซ็นต์", "อีเมล์": "อีเมล", "ลายเซ็นต์": "ลายเซ็น",
    "สังเกตุ": "สังเกต", "ผลลัพท์": "ผลลัพธ์", "รสชาด": "รสชาติ", "ไอศครีม": "ไอศกรีม",
    "กระทันหัน": "กะทันหัน", "เครื่องสำอางค์": "เครื่องสำอาง", "ปิคนิค": "ปิกนิก",
    "คลีนิค": "คลินิก", "คลินิค": "คลินิก", "โควต้า": "โควตา", "ช็อคโกแลต": "ช็อกโกแลต",
    "ซีรี่ย์": "ซีรีส์", "ซีรี่ส์": "ซีรีส์", "แคทตาล็อก": "แคตตาล็อก",
    "บรรได": "บันได", "บันทัด": "บรรทัด", "ทะเลสาป": "ทะเลสาบ",
    "สัปปะรด": "สับปะรด", "ผาสุข": "ผาสุก", "พิศดาร": "พิสดาร",
    "สะบาย": "สบาย", "เพาะว่า": "เพราะว่า", "กะเพาะ": "กระเพาะ",
    "เกมส์": "เกม", "ไม๊": "ไหม",
    "นะค่ะ": "นะคะ", "ไหมค่ะ": "ไหมคะ", "หรือเปล่าค่ะ": "หรือเปล่าคะ",
}


def _collapse_repeats(text: str) -> str:
    # "มากกกก" / "เลยยย" at the end of a word -> "มาก" / "เลย"
    text = re.sub(r"([฀-๿])\1{2,}(?=\s|$|[!?.,])", r"\1", text)
    # "soooo" -> "so", "!!!!" -> "!"
    text = re.sub(r"([A-Za-z])\1{2,}", r"\1", text)
    return re.sub(r"([!?.])\1{2,}", r"\1", text)


def spell_correct(text: str) -> str:
    text = _collapse_repeats(text)
    for wrong in sorted(THAI_COMMON_MISSPELLINGS, key=len, reverse=True):
        text = text.replace(wrong, THAI_COMMON_MISSPELLINGS[wrong])
    if re.search(r"[A-Za-z]{3,}", text):
        text = _english_spell(text)
    return text


_en_checker = None


def _english_spell(text: str) -> str:
    global _en_checker
    if _en_checker is None:
        from spellchecker import SpellChecker
        _en_checker = SpellChecker(language="en")

    def fix(m: re.Match) -> str:
        w = m.group(0)
        if len(w) < 3 or w.isupper() or w.lower() in _en_checker:
            return w
        c = _en_checker.correction(w.lower())
        if not c:
            return w
        return c.capitalize() if w[0].isupper() else c

    return re.sub(r"[A-Za-z]+", fix, text)


# ---------- tone rewriting (Thai only) ----------

PARTICLES = {"นะ", "น้า", "จ้า", "จ้ะ", "จ๊ะ", "ว่ะ", "วะ", "โว้ย", "เว้ย", "อะ", "อ่ะ", "เนอะ", "สิ", "ดิ",
             "ครับ", "ค่ะ", "คะ", "คับ", "ครัช", "งับ", "เด้อ", "นะครับ", "นะคะ"}

POLITE_MAP = {"กู": "{I}", "ข้า": "{I}", "มึง": "คุณ", "แก": "คุณ", "แดก": "ทาน", "กิน": "ทาน",
              "เออ": "", "ว่ะ": "", "วะ": "", "โว้ย": "", "เว้ย": "", "ตาย": "เสียชีวิต"}

FORMAL_MAP = {"กู": "ข้าพเจ้า", "ผม": "ข้าพเจ้า", "ฉัน": "ข้าพเจ้า", "ดิฉัน": "ข้าพเจ้า", "เรา": "ข้าพเจ้า",
              "มึง": "ท่าน", "แก": "ท่าน", "เธอ": "ท่าน", "คุณ": "ท่าน",
              "กิน": "รับประทาน", "ทาน": "รับประทาน", "แดก": "รับประทาน", "บอก": "แจ้ง",
              "อยาก": "ประสงค์", "ทำไม": "เหตุใด", "เพราะ": "เนื่องจาก", "ตอนนี้": "ขณะนี้",
              "เดี๋ยวนี้": "ปัจจุบัน", "เยอะ": "จำนวนมาก", "ไหม": "หรือไม่", "มั้ย": "หรือไม่",
              "หรือเปล่า": "หรือไม่", "เลย": "", "จัง": "", "มากๆ": "อย่างยิ่ง", "แต่ว่า": "แต่",
              "ป่วย": "เจ็บป่วย", "ตาย": "เสียชีวิต", "หมอ": "แพทย์", "บ้าน": "ที่พักอาศัย"}

CASUAL_MAP = {"ข้าพเจ้า": "เรา", "กระผม": "ผม", "ดิฉัน": "เรา", "ท่าน": "คุณ",
              "รับประทาน": "กิน", "ทาน": "กิน", "เนื่องจาก": "เพราะ", "ขณะนี้": "ตอนนี้",
              "ประสงค์": "อยาก", "แจ้ง": "บอก", "หรือไม่": "ไหม", "เหตุใด": "ทำไม",
              "ครับ": "", "ค่ะ": "", "คะ": "", "กรุณา": "", "โปรด": ""}


def _map_token(tok: str, mapping: dict[str, str]) -> str:
    if tok in mapping:
        return mapping[tok]
    # Compound words such as "กินข้าว": swap the known prefix if the rest is a real word.
    from pythainlp.corpus import thai_words
    for key in sorted(mapping, key=len, reverse=True):
        rest = tok[len(key):]
        if tok.startswith(key) and rest and rest in thai_words():
            return mapping[key] + rest
    return tok


def _end_particle(gender: str) -> str:
    return {"male": "ครับ", "female": "ค่ะ"}.get(gender, "ครับ/ค่ะ")


def rewrite_style(text: str, style: str, gender: str = "neutral") -> str:
    """Word-swap rewriting for Thai. English text is returned unchanged."""
    if not re.search(r"[฀-๿]", text):
        return text
    mapping = {"polite": POLITE_MAP, "business": POLITE_MAP, "formal": FORMAL_MAP,
               "academic": FORMAL_MAP, "casual": CASUAL_MAP}.get(style, {})
    me = {"male": "ผม", "female": "ดิฉัน"}.get(gender, "ฉัน")
    sentences = re.split(r"(\s{1,}|\n)", text)
    out = []
    for s in sentences:
        if not s.strip():
            out.append(s)
            continue
        toks = [_map_token(t, mapping).replace("{I}", me) for t in tokenize(s)]
        if style in ("formal", "academic"):
            toks = [t for t in toks if t not in PARTICLES]
        joined = "".join(toks).strip()
        if style in ("polite", "business") and joined and not any(joined.endswith(p) for p in ("ครับ", "ค่ะ", "คะ")):
            joined += _end_particle(gender)
        out.append(joined)
    return re.sub(r"[ ]{2,}", " ", "".join(out)).strip()
