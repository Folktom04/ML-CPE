"""TextAssistant: spell correction, tone rewriting and translation, all offline."""
from dataclasses import dataclass, field

from . import fallback
from .config import Settings
from .llm import LocalLLM
from .prompts import (GENDER_HINT, LANGUAGES, SPELL_EXAMPLES, SPELL_SYSTEM, STYLE_INPUT, STYLE_INPUT_EN, STYLE_SYSTEM,
                      STYLE_SYSTEM_EN, STYLES, TRANSLATE_SYSTEM, few_shot, glossary_rules, style_examples)
from .textutil import (clean_output, detect_language, diff_segments, fix_thai_register, keep_spelling_fixes_only,
                       missing_numbers, similarity, split_paragraphs, word_changes)


@dataclass
class Result:
    text: str
    engine: str                    # model name or "rules"
    changes: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"text": self.text, "engine": self.engine, "changes": self.changes,
                "warnings": self.warnings, **self.extra}


class TextAssistant:
    def __init__(self, settings: Settings | None = None, llm: LocalLLM | None = None):
        self.settings = settings or Settings()
        self.llm = llm or LocalLLM(self.settings)

    # ----- helpers -----
    @property
    def general(self) -> str:
        return self.settings.general_model

    def status(self) -> dict:
        return {
            "general_model": self.llm.available(self.general),
            "translate_model": self.llm.available("translate"),
            "model_dir": str(self.settings.model_dir),
        }

    def _per_paragraph(self, text: str, fn) -> str:
        """Run fn on each paragraph; keep blank lines and layout as they were."""
        return "".join(p if not p.strip() else fn(p) for p in split_paragraphs(text))

    def _ask(self, model: str, system: str | None, examples: list[tuple[str, str]], text: str) -> str:
        msgs = ([{"role": "system", "content": system}] if system else []) + few_shot(examples)
        msgs.append({"role": "user", "content": text})
        max_tokens = min(self.settings.n_ctx // 2, max(256, len(text) * 3))
        return clean_output(self.llm.chat(model, msgs, max_tokens=max_tokens), source=text)

    # ----- 1. spell correction -----
    def correct(self, text: str) -> Result:
        if not text.strip():
            return Result(text, "none")
        if not self.llm.available(self.general):
            fixed = fallback.spell_correct(text)
            return Result(fixed, "rules", word_changes(text, fixed),
                          ["ไม่พบโมเดล AI จึงใช้โหมดพื้นฐาน (ตรวจได้เฉพาะคำผิดที่พบบ่อย)"],
                          {"diff": diff_segments(text, fixed)})
        warnings = []

        def fix(p: str) -> str:
            out = self._ask(self.general, SPELL_SYSTEM, SPELL_EXAMPLES, p)
            if "ต้นฉบับ:" in out:
                out = out.split("ต้นฉบับ:", 1)[-1].strip()
            # A spell checker should change little. A big change means the model rewrote the text.
            if len(p) > 15 and similarity(p, out) < 0.6:
                warnings.append("โมเดลเปลี่ยนข้อความมากเกินไปในบางย่อหน้า จึงใช้ผลจากโหมดพื้นฐานแทน")
                return fallback.spell_correct(p)
            # Undo word swaps that are not spelling fixes (e.g. "ลางาน" -> "ลาหยุด").
            return keep_spelling_fixes_only(p, out)

        fixed = self._per_paragraph(text, fix)
        return Result(fixed, self.general, word_changes(text, fixed), warnings, {"diff": diff_segments(text, fixed)})

    # ----- 2. tone rewriting -----
    def rewrite(self, text: str, style: str = "polite", gender: str = "neutral") -> Result:
        if style not in STYLES:
            raise ValueError(f"Unknown style '{style}'. Choose from: {', '.join(STYLES)}")
        if not text.strip():
            return Result(text, "none")
        if not self.llm.available(self.general):
            out = fallback.rewrite_style(text, style, gender)
            return Result(out, "rules", warnings=["ไม่พบโมเดล AI จึงใช้โหมดพื้นฐาน (แทนคำแบบง่าย รองรับเฉพาะภาษาไทย)"])
        s = STYLES[style]
        thai = detect_language(text) == "th"
        if thai:
            system = STYLE_SYSTEM.format(name=s["th"], desc=s["desc"],
                                         gender=GENDER_HINT.get(gender, GENDER_HINT["neutral"]))
            wrap = STYLE_INPUT
        else:
            system, wrap = STYLE_SYSTEM_EN.format(en=s["en"]), STYLE_INPUT_EN
        examples = style_examples(style, gender, thai)

        def one(p: str) -> str:
            out = self._ask(self.general, system, examples, wrap.format(text=p))
            return fix_thai_register(out, style, gender) if thai else out

        out = self._per_paragraph(text, one)
        return Result(out, self.general, warnings=self._number_warnings(text, out), extra={"style": style})

    @staticmethod
    def _number_warnings(src: str, out: str) -> list[str]:
        miss = missing_numbers(src, out)
        return [f"ตัวเลขจากต้นฉบับหายไป: {', '.join(miss)} (โปรดตรวจสอบ)"] if miss else []

    def rewrite_all(self, text: str, styles: list[str] | None = None, gender: str = "neutral") -> dict[str, Result]:
        return {s: self.rewrite(text, s, gender) for s in (styles or ["polite", "formal", "casual"])}

    # ----- 3. translation -----
    def translate(self, text: str, target: str = "en", source: str = "auto",
                  glossary: dict[str, str] | None = None, style: str | None = None,
                  back_translate: bool = False) -> Result:
        if target not in LANGUAGES:
            raise ValueError(f"Unknown target language '{target}'. Choose from: {', '.join(LANGUAGES)}")
        if not text.strip():
            return Result(text, "none")
        src = detect_language(text) if source == "auto" else source
        if src not in LANGUAGES:
            raise ValueError(f"Unknown source language '{src}'")
        if src == target:
            return Result(text, "none", warnings=["ภาษาต้นทางและปลายทางเป็นภาษาเดียวกัน"],
                          extra={"source": src, "target": target})

        use_typhoon_translate = {src, target} == {"th", "en"} and self.llm.available("translate")
        model = "translate" if use_typhoon_translate else self.general
        if not self.llm.available(model):
            raise RuntimeError("การแปลต้องใช้โมเดล AI แต่ยังไม่พบไฟล์โมเดล ให้รัน: python download_models.py")

        rules = glossary_rules(glossary)
        if style:
            rules.append(f"Write the translation in this tone: {STYLES[style]['en']}.")
        src_name, tgt_name = LANGUAGES[src][0], LANGUAGES[target][0]

        if use_typhoon_translate:
            # Prompt format recommended by the Typhoon Translate model card.
            def tr(p: str) -> str:
                if rules:
                    numbered = "\n".join(f"{i}. {r}" for i, r in enumerate(rules, 1))
                    prompt = (f"Translate the following {src_name} text into {tgt_name}, strictly following the "
                              f"rules below and return only the translated text.\nRules:\n{numbered}\nSource Text:\n{p}")
                else:
                    prompt = f"Translate the following {src_name} text into {tgt_name}.\n\n{p}"
                return self._ask(model, None, [], prompt)
        else:
            rule_text = "".join(f"- {r}\n" for r in rules)
            system = TRANSLATE_SYSTEM.format(src=src_name, tgt=tgt_name, rules=rule_text)

            def tr(p: str) -> str:
                return self._ask(model, system, [], p)

        out = self._per_paragraph(text, tr)
        res = Result(out, model, warnings=self._number_warnings(text, out), extra={"source": src, "target": target})
        if back_translate:
            # Translate back so the user can check that the meaning survived.
            res.extra["back_translation"] = self.translate(out, target=src, source=target).text
        return res
