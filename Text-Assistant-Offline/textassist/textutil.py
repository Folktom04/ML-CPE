"""Small text helpers: language detection, output cleanup, chunking, word diff."""
import difflib
import re

_THAI = re.compile(r"[฀-๿]")
_LATIN = re.compile(r"[A-Za-z]")
_CJK = re.compile(r"[一-鿿]")
_KANA = re.compile(r"[぀-ヿ]")
_HANGUL = re.compile(r"[가-힯]")
_LAO = re.compile(r"[຀-໿]")


def detect_language(text: str) -> str:
    """Rough script-based guess. Returns an ISO code such as 'th' or 'en'."""
    counts = {
        "th": len(_THAI.findall(text)),
        "en": len(_LATIN.findall(text)),
        "zh": len(_CJK.findall(text)),
        "ja": len(_KANA.findall(text)) * 3,  # kana means Japanese even with kanji
        "ko": len(_HANGUL.findall(text)),
        "lo": len(_LAO.findall(text)),
    }
    lang, n = max(counts.items(), key=lambda kv: kv[1])
    return lang if n else "en"


# Labels a model sometimes puts before its answer.
_PREFIX = re.compile(
    r"^\s*(?:ประโยคที่แก้(?:ไข)?แล้ว|ข้อความที่แก้(?:ไข)?แล้ว|ข้อความที่เขียนใหม่|ผลลัพธ์|คำแปล|แก้ไขแล้ว|"
    r"corrected(?: text| sentence)?|rewritten(?: text)?|translation|output|answer)\s*[:：]\s*",
    re.IGNORECASE,
)


def clean_output(text: str, source: str = "") -> str:
    """Strip markdown, labels and wrapping quotes the model may add."""
    t = text.strip()
    t = re.sub(r"<think>.*?</think>", "", t, flags=re.DOTALL).strip()
    t = re.sub(r"^```[a-z]*\n?|\n?```$", "", t).strip()
    t = _PREFIX.sub("", t)
    if "**" not in source:
        t = t.replace("**", "")
    if "__" not in source:
        t = re.sub(r"__(.+?)__", r"\1", t)
    pairs = [('"', '"'), ("“", "”"), ("'", "'"), ("「", "」")]
    for a, b in pairs:
        if len(t) >= 2 and t.startswith(a) and t.endswith(b) and not (source.startswith(a) and source.endswith(b)):
            t = t[1:-1].strip()
    return t


def split_paragraphs(text: str, max_chars: int = 1500) -> list[str]:
    """Split on blank lines / newlines so long texts fit in the model's context.

    Returns pieces that, joined back, reproduce the original layout:
    separators ("\n", "\n\n") are kept as their own items.
    """
    parts = re.split(r"(\n+)", text)
    out: list[str] = []
    for p in parts:
        if not p or p.startswith("\n") or len(p) <= max_chars:
            out.append(p)
            continue
        # Very long paragraph: cut at spaces (Thai uses spaces between sentences).
        buf = ""
        for piece in p.split():
            if buf and len(buf) + len(piece) + 1 > max_chars:
                out.append(buf)
                out.append(" ")
                buf = piece
            else:
                buf = f"{buf} {piece}" if buf else piece
        if buf:
            out.append(buf)
    return out


def tokenize(text: str) -> list[str]:
    """Word tokens with spaces kept, so tokens join back to the exact text."""
    if _THAI.search(text):
        from pythainlp.tokenize import word_tokenize
        return word_tokenize(text, engine="newmm", keep_whitespace=True)
    return re.findall(r"\s+|\w+|[^\w\s]", text)


def word_changes(before: str, after: str) -> list[dict]:
    """List of {'from': ..., 'to': ...} word replacements between two texts."""
    a, b = tokenize(before), tokenize(after)
    changes = []
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        src, dst = "".join(a[i1:i2]), "".join(b[j1:j2])
        if src.strip() == dst.strip():
            continue
        changes.append({"from": src, "to": dst})
    return changes


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(a=a, b=b, autojunk=False).ratio()


def keep_spelling_fixes_only(before: str, after: str, min_ratio: float = 0.5) -> str:
    """Rebuild `after`, but undo edits that look like rewording rather than spelling fixes.

    A spelling fix keeps most letters of the word ("เพาะ" -> "เพราะ"). A word that shares
    few letters with the original ("ลางาน" -> "ลาหยุด") is put back as it was.
    Deleting stray letters or a doubled word is kept; deleting or adding whole words is undone.
    """
    a, b = tokenize(before), tokenize(after)
    out = []
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        src, dst = "".join(a[i1:i2]), "".join(b[j1:j2])
        if op == "equal":
            out.append(src)
        elif op == "delete":
            # Dropping a stray letter is fine; dropping a whole word (e.g. "ไม่") may flip the meaning.
            out.append("" if len(src.strip()) <= 2 or src.strip() == "".join(a[max(0, i1 - 1):i1]).strip() else src)
        elif op == "insert":
            out.append(dst if len(dst.strip()) <= 2 else "")  # model added a whole new word
        else:  # replace
            out.append(dst if similarity(src, dst) >= min_ratio else src)
    return "".join(out)


_NUM = re.compile(r"[0-9๐-๙][0-9๐-๙,.:/]*")
_THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")


def missing_numbers(source: str, output: str) -> list[str]:
    """Numbers in the source that do not appear in the output (dates, prices, times...)."""
    def nums(t: str) -> set[str]:
        return {n.translate(_THAI_DIGITS).rstrip(".,:/").replace(",", "") for n in _NUM.findall(t)}
    have = nums(output)
    return sorted(n for n in nums(source) if n and n not in have)


_END = r"(?=[\s.!?]|$)"


def fix_thai_register(text: str, style: str, gender: str) -> str:
    """Fix particles and pronouns the model sometimes gets wrong for the chosen style."""
    me = {"male": "ผม", "female": "ดิฉัน"}.get(gender, "")
    end = {"male": "ครับ", "female": "ค่ะ"}.get(gender, "")
    t = re.sub(r"(ดิฉัน/ผม|ผม/ดิฉัน)", me, text)
    t = re.sub(r"(ครับ/ค่ะ|ค่ะ/ครับ)", end, t)
    if style in ("casual", "formal", "academic"):
        # These registers do not use ครับ/ค่ะ.
        t = re.sub(r"\s?(ครับผม|ครับ|ค่ะ|คะ)" + _END, "", t)
    elif gender == "male":
        t = re.sub(r"(ค่ะ|คะ)" + _END, "ครับ", t).replace("ดิฉัน", "ผม")
    elif gender == "female":
        t = re.sub(r"ครับ" + _END, "ค่ะ", t)
    return re.sub(r"[ ]{2,}", " ", t).strip()


def diff_segments(before: str, after: str) -> list[dict]:
    """[{'op': 'same'|'del'|'ins', 'text': ...}] for showing corrections inline."""
    a, b = tokenize(before), tokenize(after)
    segs = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op == "equal":
            segs.append({"op": "same", "text": "".join(a[i1:i2])})
            continue
        if i2 > i1:
            segs.append({"op": "del", "text": "".join(a[i1:i2])})
        if j2 > j1:
            segs.append({"op": "ins", "text": "".join(b[j1:j2])})
    return segs
