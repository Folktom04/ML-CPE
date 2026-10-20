"""Prompts for each task. Few-shot examples keep small models on format."""

LANGUAGES = {
    "th": ("Thai", "ไทย"),
    "en": ("English", "อังกฤษ"),
    "zh": ("Simplified Chinese", "จีน"),
    "ja": ("Japanese", "ญี่ปุ่น"),
    "ko": ("Korean", "เกาหลี"),
    "fr": ("French", "ฝรั่งเศส"),
    "de": ("German", "เยอรมัน"),
    "es": ("Spanish", "สเปน"),
    "vi": ("Vietnamese", "เวียดนาม"),
    "lo": ("Lao", "ลาว"),
    "my": ("Burmese", "พม่า"),
    "km": ("Khmer", "เขมร"),
    "ms": ("Malay", "มลายู"),
    "id": ("Indonesian", "อินโดนีเซีย"),
}

# ---------- 1. Spell correction ----------

SPELL_SYSTEM = (
    "คุณคือผู้ตรวจพิสูจน์อักษรมืออาชีพ หน้าที่คือแก้คำผิดในข้อความของผู้ใช้เท่านั้น\n"
    "สิ่งที่ต้องแก้: คำสะกดผิด พิมพ์ผิด ตัวอักษรซ้ำเกิน วรรณยุกต์ผิด การันต์ผิด "
    "คำที่ใช้ผิดความหมาย (เช่น คะ/ค่ะ, นะคะ/นะค่ะ, เลี้ยง/เลี่ยง) และการเว้นวรรคที่ผิด\n"
    "กฎ:\n"
    "- ห้ามเปลี่ยนสำนวน ระดับภาษา ลำดับคำ หรือความหมาย\n"
    "- ห้ามเพิ่มหรือตัดเนื้อหา ห้ามอธิบาย ห้ามใส่เครื่องหมาย ** หรือ markdown\n"
    "- คงชื่อเฉพาะ ตัวเลข วันที่ ลิงก์ และเครื่องหมายวรรคตอนไว้ตามเดิม\n"
    "- ถ้าไม่มีคำผิด ให้ตอบข้อความเดิมทุกตัวอักษร\n"
    "- ข้อความภาษาอื่นให้แก้ตามหลักภาษานั้น\n"
    "ตอบเฉพาะข้อความที่แก้แล้วเท่านั้น"
)

SPELL_EXAMPLES = [
    ("วันนี้อากาศร้อนมากกก ผมเลยไม่อยากออกไปไหนเลยยย แต่ต้องไปซื้อของที่ห้างเพาะของหมดแล้ว",
     "วันนี้อากาศร้อนมาก ผมเลยไม่อยากออกไปไหนเลย แต่ต้องไปซื้อของที่ห้างเพราะของหมดแล้ว"),
    ("ขอบคุณนะค่ะ ที่ช่วยอธิบายให้เข้าใจ ดิฉันจะพยายามทำให้ดีที่สุดคะ",
     "ขอบคุณนะคะ ที่ช่วยอธิบายให้เข้าใจ ดิฉันจะพยายามทำให้ดีที่สุดค่ะ"),
    ("I recieve your mesage yesterday and I will definately reply tommorow.",
     "I received your message yesterday and I will definitely reply tomorrow."),
]

# ---------- 2. Tone / register rewriting ----------

STYLES = {
    "polite": {
        "th": "สุภาพ",
        "desc": "ภาษาสุภาพ ใช้ในชีวิตประจำวันกับผู้ใหญ่หรือคนที่ไม่สนิท ใช้คำลงท้าย ครับ/ค่ะ "
                "ใช้คำสุภาพแทนคำหยาบหรือคำกันเอง (เช่น กิน→ทาน, กู→ผม/ดิฉัน) น้ำเสียงนุ่มนวล ให้เกียรติ",
        "en": "polite and courteous everyday tone (please, thank you, would you), warm and respectful",
    },
    "formal": {
        "th": "ทางการ",
        "desc": "ภาษาทางการแบบหนังสือราชการหรือจดหมายธุรกิจ ใช้คำศัพท์ทางการ "
                "(เช่น กิน→รับประทาน, บอก→แจ้ง, ช่วย→อนุเคราะห์, ไม่ได้→ไม่สามารถ) ประโยคสมบูรณ์ "
                "ไม่ใช้คำลงท้าย นะ จ้ะ ครับ ค่ะ ไม่ใช้ภาษาพูด ไม่ใช้คำฟุ่มเฟือยหรือขออภัยเกินเหตุ",
        "en": "formal, official register suitable for business letters or official documents; no contractions or slang",
    },
    "casual": {
        "th": "เป็นกันเอง",
        "desc": "ภาษาพูดแบบเป็นกันเองกับเพื่อนหรือคนสนิท สั้น กระชับ เป็นธรรมชาติ "
                "ใช้สรรพนาม เรา/ฉัน/เธอ และคำลงท้ายเบาๆ (นะ, น้า, เลย, อะ, ล่ะ) ไม่ใช้ ครับ/ค่ะ ไม่หยาบคาย ไม่ใส่อีโมจิ",
        "en": "friendly, relaxed conversational tone, contractions are fine, no slang that is rude, no emoji",
    },
    "academic": {
        "th": "วิชาการ",
        "desc": "ภาษาวิชาการสำหรับรายงานหรือบทความ เป็นกลาง ไม่ใช้สรรพนามบุรุษที่หนึ่งเมื่อเลี่ยงได้ "
                "ใช้ศัพท์ที่แม่นยำ ประโยคเชื่อมโยงเป็นเหตุเป็นผล",
        "en": "academic register for reports and papers: objective, precise vocabulary, impersonal",
    },
    "business": {
        "th": "ธุรกิจ/อีเมลงาน",
        "desc": "ภาษาสำหรับอีเมลหรือข้อความในที่ทำงาน สุภาพ ชัดเจน ตรงประเด็น "
                "ใช้คำลงท้าย ครับ/ค่ะ ได้ ไม่ยืดยาว",
        "en": "professional workplace tone for emails: clear, concise, polite, to the point",
    },
}

GENDER_HINT = {
    "male": "ผู้เขียนเป็นผู้ชาย: ถ้าระดับภาษานี้ใช้สรรพนามหรือคำลงท้าย ให้ใช้ ผม / ครับ",
    "female": "ผู้เขียนเป็นผู้หญิง: ถ้าระดับภาษานี้ใช้สรรพนามหรือคำลงท้าย ให้ใช้ ดิฉัน หรือ ฉัน / ค่ะ หรือ คะ (คำถามใช้ คะ)",
    "neutral": "ไม่ทราบเพศผู้เขียน: เลี่ยงสรรพนามบุรุษที่หนึ่งและคำลงท้ายที่ระบุเพศเมื่อทำได้",
}

STYLE_SYSTEM = (
    "คุณคือบรรณาธิการภาษาไทยมืออาชีพ งานของคุณคือปรับ \"ระดับภาษา\" ของข้อความต้นฉบับให้เป็นแบบ \"{name}\"\n"
    "ลักษณะของระดับภาษานี้: {desc}\n"
    "{gender}\n"
    "กฎสำคัญ:\n"
    "- เปลี่ยนเฉพาะถ้อยคำและน้ำเสียง ห้ามเปลี่ยนเนื้อหา: คงทุกข้อเท็จจริง (ชื่อ ตัวเลข วันที่ เวลา สถานที่ ประเภทการลา ฯลฯ) "
    "และคงเจตนาเดิม (บอกเล่า / ขอร้อง / ถาม / ตำหนิ) ผู้เขียนและมุมมองต้องเป็นคนเดิม\n"
    "- ห้ามเพิ่มข้อมูลที่ต้นฉบับไม่มี ห้ามเติมคำขึ้นต้นหรือลงท้ายจดหมาย หรือช่องว่างให้กรอก เช่น [ชื่อ]\n"
    "- ถ้าต้นฉบับเป็นระดับภาษานี้อยู่แล้ว ให้แก้น้อยที่สุด\n"
    "- ความยาวใกล้เคียงต้นฉบับ แก้คำผิดไปด้วยถ้ามี\n"
    "- ตอบเป็นภาษาไทยเท่านั้น ห้ามอธิบาย ห้ามใส่อีโมจิ ห้ามใส่ markdown\n"
    "ตอบเฉพาะข้อความที่ปรับแล้วเท่านั้น"
)

STYLE_SYSTEM_EN = (
    "You are a professional editor. Rewrite the source text in this tone: {en}.\n"
    "Rules:\n"
    "- Change only wording and tone. Keep every fact (names, numbers, dates, times, places) and the original intent "
    "(statement / request / question / complaint) from the same writer's point of view.\n"
    "- Do not add information, greetings, sign-offs or placeholders such as [Name].\n"
    "- If the text already fits this tone, change as little as possible. Fix spelling mistakes too.\n"
    "- Answer in the same language as the source text. No explanations, emoji or markdown.\n"
    "Output only the rewritten text."
)

STYLE_INPUT = "ต้นฉบับ:\n{text}"
STYLE_INPUT_EN = "Source text:\n{text}"

_EX1 = "พรุ่งนี้กูไม่ไปทำงานนะ ป่วยว่ะ ฝากบอกหัวหน้าด้วย"
_EX2 = "ขอแจ้งให้ทราบว่าการประชุมในวันพรุ่งนี้ถูกเลื่อนออกไปเป็นวันศุกร์ กรุณาเตรียมเอกสารมาด้วย"
_EX4 = "ส่งของช้าฉิบหาย สั่งตั้งแต่อาทิตย์ที่แล้วยังไม่ได้เลย"
_EN1 = "Hey, can u send me the file? need it asap"
_EN2 = "The delivery is super late, I ordered it last week and still got nothing."

# Thai examples per style and speaker gender ("*" = any gender).
STYLE_EXAMPLES = {
    "polite": {
        "male": [(_EX1, "พรุ่งนี้ผมขอลาหยุดงานนะครับ เพราะไม่สบาย รบกวนช่วยแจ้งหัวหน้าให้ด้วยครับ"),
                 (_EX4, "สินค้าจัดส่งช้ามากครับ ผมสั่งตั้งแต่สัปดาห์ที่แล้วแต่ยังไม่ได้รับเลยครับ")],
        "female": [(_EX1, "พรุ่งนี้ดิฉันขอลาหยุดงานนะคะ เพราะไม่สบาย รบกวนช่วยแจ้งหัวหน้าให้ด้วยค่ะ"),
                   (_EX4, "สินค้าจัดส่งช้ามากค่ะ ดิฉันสั่งตั้งแต่สัปดาห์ที่แล้วแต่ยังไม่ได้รับเลยค่ะ")],
        "neutral": [(_EX1, "พรุ่งนี้ขอลาหยุดงานนะ เพราะไม่สบาย รบกวนช่วยแจ้งหัวหน้าให้ด้วย"),
                    (_EX4, "สินค้าจัดส่งช้ามาก สั่งตั้งแต่สัปดาห์ที่แล้วแต่ยังไม่ได้รับเลย")],
    },
    "formal": {
        "*": [(_EX1, "ข้าพเจ้าขอลาป่วยในวันพรุ่งนี้ จึงขอความกรุณาแจ้งให้ผู้บังคับบัญชาทราบด้วย"),
              (_EX4, "การจัดส่งสินค้าล่าช้าเป็นอย่างมาก โดยได้สั่งซื้อตั้งแต่สัปดาห์ที่ผ่านมา แต่ยังไม่ได้รับสินค้า"),
              ("เรียนคณบดี ข้าพเจ้าขออนุญาตลากิจในวันที่ 3 มีนาคม 2568",
               "เรียนคณบดี ข้าพเจ้าขออนุญาตลากิจในวันที่ 3 มีนาคม 2568")],
    },
    "casual": {
        "*": [(_EX2, "ประชุมพรุ่งนี้เลื่อนไปวันศุกร์นะ อย่าลืมเอาเอกสารมาด้วยล่ะ"),
              (_EX1, "พรุ่งนี้เราไม่ไปทำงานนะ ป่วยอะ ฝากบอกหัวหน้าให้หน่อย"),
              ("ข้าพเจ้าขออนุญาตลากิจในวันที่ 3 มีนาคม", "ขอลากิจวันที่ 3 มีนาคมนะ")],
    },
    "academic": {
        "*": [("คนไทยเดี๋ยวนี้เล่นมือถือกันเยอะมาก วันๆ ไม่ทำอะไรเลย",
               "ปัจจุบันประชากรไทยมีแนวโน้มใช้งานโทรศัพท์เคลื่อนที่เป็นระยะเวลานานในแต่ละวัน"),
              (_EX4, "การจัดส่งสินค้ามีความล่าช้าอย่างมีนัยสำคัญ กล่าวคือ สินค้าที่สั่งซื้อตั้งแต่สัปดาห์ก่อนยังไม่ได้รับการส่งมอบ")],
    },
    "business": {
        "male": [(_EX1, "พรุ่งนี้ผมขอลาป่วยหนึ่งวันครับ รบกวนช่วยแจ้งหัวหน้าให้ด้วยนะครับ"),
                 (_EX4, "สินค้าที่ผมสั่งไว้ตั้งแต่สัปดาห์ที่แล้วยังไม่ได้รับเลยครับ การจัดส่งล่าช้ามากครับ")],
        "female": [(_EX1, "พรุ่งนี้ดิฉันขอลาป่วยหนึ่งวันค่ะ รบกวนช่วยแจ้งหัวหน้าให้ด้วยนะคะ"),
                   (_EX4, "สินค้าที่ดิฉันสั่งไว้ตั้งแต่สัปดาห์ที่แล้วยังไม่ได้รับเลยค่ะ การจัดส่งล่าช้ามากค่ะ")],
        "neutral": [(_EX1, "ขอลาป่วยในวันพรุ่งนี้หนึ่งวัน รบกวนช่วยแจ้งหัวหน้าให้ด้วย"),
                    (_EX4, "สินค้าที่สั่งไว้ตั้งแต่สัปดาห์ที่แล้วยังไม่ได้รับ การจัดส่งล่าช้ามาก")],
    },
}

STYLE_EXAMPLES_EN = {
    "polite": [(_EN1, "Hi, could you please send me the file? I need it as soon as possible. Thank you."),
               (_EN2, "I'm afraid the delivery is quite late. I placed my order last week and haven't received it yet.")],
    "formal": [(_EN1, "Could you kindly send me the file? It is required urgently."),
               (_EN2, "The delivery has been significantly delayed. The order was placed last week and has not yet been received.")],
    "casual": [("Could you kindly send me the file? It is required urgently.", "Hey, can you send me the file? Need it pretty urgently."),
               (_EN2, "The delivery's really late. I ordered it last week and still haven't got it.")],
    "academic": [(_EN2, "The delivery was substantially delayed: the order, placed one week earlier, had not been received.")],
    "business": [(_EN1, "Hi, could you please send me the file? I need it urgently. Thanks."),
                 (_EN2, "My order from last week still hasn't arrived. The delivery is significantly delayed.")],
}


def style_examples(style: str, gender: str, thai: bool = True) -> list[tuple[str, str]]:
    if not thai:
        return [(STYLE_INPUT_EN.format(text=u), a) for u, a in STYLE_EXAMPLES_EN[style]]
    ex = STYLE_EXAMPLES[style]
    pairs = ex.get(gender) or ex.get("*") or ex.get("neutral") or []
    return [(STYLE_INPUT.format(text=u), a) for u, a in pairs]


# ---------- 3. Translation ----------

TRANSLATE_SYSTEM = (
    "You are a professional translator. Translate the user's text from {src} into {tgt}.\n"
    "Rules:\n"
    "- Translate faithfully and completely: keep every fact, name, number, date and nuance; do not summarise.\n"
    "- Use natural, idiomatic {tgt} as a native speaker would write it, keeping the original tone and register.\n"
    "- Keep line breaks, lists and formatting.\n"
    "{rules}"
    "- Output only the translation, with no notes, explanations or quotes."
)


def glossary_rules(glossary: dict[str, str] | None) -> list[str]:
    if not glossary:
        return []
    return [f'Translate "{k}" as "{v}".' for k, v in glossary.items()]


def few_shot(examples: list[tuple[str, str]]) -> list[dict]:
    msgs = []
    for u, a in examples:
        msgs += [{"role": "user", "content": u}, {"role": "assistant", "content": a}]
    return msgs
