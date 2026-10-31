"""ML classifier: tells unrest news apart from noise and sorts it into event types.

TF-IDF (word + character n-grams, so Thai works without a word segmenter)
feeding a logistic regression. Trains in well under a second on the seed set.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import FunctionTransformer

DATA_DIR = Path(__file__).parent / "data"
TRAIN_CSV = DATA_DIR / "train_headlines.csv"

LABELS_TH = {
    "none": "ไม่เกี่ยวข้อง",
    "protest": "การชุมนุม/ประท้วง",
    "riot": "จลาจล/ปะทะ",
    "armed_conflict": "การสู้รบ/สงคราม",
    "terrorism": "ก่อการร้าย/ระเบิด/กราดยิง",
    "coup": "รัฐประหาร/วิกฤตการเมือง",
}

# Base severity (1-5) of each event type, before casualty adjustments.
BASE_SEVERITY = {
    "none": 0.0,
    "protest": 2.0,
    "riot": 3.5,
    "coup": 4.0,
    "armed_conflict": 4.5,
    "terrorism": 4.5,
}

MIN_CONFIDENCE = 0.40  # below this an article is treated as noise

_DEATH = re.compile(
    r"(\d+)?\s*(?:people\s+)?(?:kill(?:s|ed|ing)?|dead|deaths?|die[ds]?)|เสียชีวิต|ดับ\s*\d+|ตาย",
    re.IGNORECASE,
)
_NUMBER_WORDS = {"dozens": 24, "scores": 40, "hundreds": 200, "thousands": 2000}
_BIG_NUMBER = re.compile(r"\b(\d{2,})\b")
_PLANNED = re.compile(
    r"\b(plan(?:s|ned)?|to hold|will|braces? for|ahead of|this weekend|tomorrow|"
    r"next week|threaten(?:s|ed)?|calls? for|alert)\b|นัด(?:ชุมนุม|รวมตัว|หยุดงาน|หมาย|ม็อบ)|เตรียม(?:ชุมนุม|เคลื่อน|ยกระดับ|อพยพ)|พรุ่งนี้|สัปดาห์หน้า|ขู่",
    re.IGNORECASE,
)


# Domain keywords per class. With only a few hundred training headlines these
# give the model prior knowledge the text features alone can't learn yet.
LEXICON = {
    "protest": r"protest|rally|rallies|march|demonstrat|strike|walk(?:ed)? out|sit-in|vigil|"
               r"ชุมนุม|ประท้วง|ม็อบ|รวมตัว|เดินขบวน|คัดค้าน|หยุดงาน|ผละงาน",
    "riot": r"riot police|tear gas|water cannon|rubber bullet|baton|clash|loot|torch|ablaze|"
            r"unrest|curfew|crackdown|storm(?:ed|s)? |violent|violence|disperse|rioting|rioters|"
            r"แก๊สน้ำตา|สลาย|ปะทะ|จลาจล|เคอร์ฟิว|วุ่นวาย|กระสุนยาง|ขว้างปา|เผายาง",
    "armed_conflict": r"air ?strike|air raid|shelling|shells|artillery|missile|rocket|drone|offensive|"
                      r"front ?line|troops|rebels|fighting|battle|militia|ceasefire|siege|warplane|"
                      r"fighter jet|mortar|soldiers|military base|"
                      r"สู้รบ|ปืนใหญ่|โจมตีทางอากาศ|ขีปนาวุธ|โดรนโจมตี|ทิ้งระเบิด|ยิงปะทะ|ยิงถล่ม|ถล่ม",
    "terrorism": r"bomb|explosi|blast|suicide|gunm[ae]n|shooting|hostage|grenade|terror|"
                 r"extremist|militants|ied\b|"
                 r"ระเบิด|กราดยิง|ลอบยิง|ซุ่มยิง|ก่อความไม่สงบ|ตัวประกัน|คนร้าย",
    "coup": r"coup|martial law|junta|seiz\w* power|takeover|constitution|impeach|ousted?|ouster|"
            r"dissolve|decree|state of emergency|political crisis|"
            r"รัฐประหาร|ยึดอำนาจ|อัยการศึก|รัฐธรรมนูญ|ยุบสภา|พ้นตำแหน่ง|ฉุกเฉิน|วิกฤตการเมือง",
    "none": r"stock|shares|bitcoin|crypto|games?\b|gaming|league|champion|film|movie|trailer|"
            r"collab|concert|fans|football|festival|album|charts?\b|box office|tour\b|"
            r"weather|forecast|rain\b|typhoon|cyclone|anniversary|commemorat|trade\b|tourism|"
            r"หุ้น|เกม|ฟุตบอล|คอนเสิร์ต|ภาพยนตร์|ทีมชาติ|แชมป์|ศิลปิน|อากาศ|ฝน|พายุ|อุตุ|"
            r"รำลึก|ครบรอบ|การค้า|ท่องเที่ยว|ดิจิทัล|ลักลอบ|แรงงานต่างด้าว|ศุลกากร|บูรณาการ|ถอดบทเรียน",
}
_LEXICON_RE = {k: re.compile(v, re.IGNORECASE) for k, v in LEXICON.items()}


def _lexicon_counts(texts) -> sparse.csr_matrix:
    rows = [[min(3, len(rx.findall(t))) for rx in _LEXICON_RE.values()] for t in texts]
    return sparse.csr_matrix(np.asarray(rows, dtype=float))


def build_pipeline() -> Pipeline:
    features = FeatureUnion([
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)),
        ("lexicon", FunctionTransformer(_lexicon_counts)),
    ])
    clf = LogisticRegression(C=10.0, max_iter=3000, class_weight="balanced")
    return Pipeline([("features", features), ("clf", clf)])


def load_training_data(path: Path = TRAIN_CSV) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df.dropna(subset=["text", "label"])


@dataclass
class Prediction:
    label: str
    confidence: float
    severity: float
    planned: bool

    @property
    def relevant(self) -> bool:
        return self.label != "none" and self.confidence >= MIN_CONFIDENCE


def casualty_boost(text: str) -> float:
    """Extra severity (0-1.5) when the headline mentions deaths."""
    if not _DEATH.search(text):
        return 0.0
    numbers = [int(n) for n in _BIG_NUMBER.findall(text)]
    lower = text.lower()
    numbers += [v for word, v in _NUMBER_WORDS.items() if word in lower]
    biggest = max(numbers, default=1)
    if biggest >= 50:
        return 1.5
    if biggest >= 10:
        return 1.0
    return 0.5


def is_planned(text: str) -> bool:
    """True when the headline talks about something that has not happened yet."""
    return bool(_PLANNED.search(text))


class UnrestClassifier:
    def __init__(self) -> None:
        self.pipeline = build_pipeline()
        self.fitted = False

    def fit(self, df: pd.DataFrame | None = None) -> "UnrestClassifier":
        df = load_training_data() if df is None else df
        self.pipeline.fit(df["text"], df["label"])
        self.fitted = True
        return self

    def predict(self, texts: list[str]) -> list[Prediction]:
        if not self.fitted:
            self.fit()
        if not texts:
            return []
        probs = self.pipeline.predict_proba(texts)
        classes = self.pipeline.classes_
        out = []
        for text, p in zip(texts, probs):
            i = int(np.argmax(p))
            label, conf = str(classes[i]), float(p[i])
            sev = 0.0
            if label != "none":
                sev = min(5.0, max(1.0, BASE_SEVERITY[label] + casualty_boost(text)))
            out.append(Prediction(label, conf, sev, label != "none" and is_planned(text)))
        return out


def evaluate(folds: int = 5, seed: int = 42) -> dict:
    """Stratified k-fold cross-validation on the seed set."""
    df = load_training_data()
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    pred = cross_val_predict(build_pipeline(), df["text"], df["label"], cv=cv)
    y = df["label"].to_numpy()
    relevant_true = y != "none"
    relevant_pred = pred != "none"
    return {
        "n": len(df),
        "macro_f1": float(f1_score(y, pred, average="macro")),
        "accuracy": float((pred == y).mean()),
        "relevance_accuracy": float((relevant_true == relevant_pred).mean()),
        "report": classification_report(y, pred, zero_division=0),
    }
