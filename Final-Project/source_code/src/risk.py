"""Risk Engine: WHO level, minutes to sunburn by Fitzpatrick skin type, SPF/PA advice.

Domain constants (project rules): 1 UVI = 0.025 W/m² erythemal; minutes to burn =
MED / (UVI × 0.025 × 60); warnings always use the UPPER quantile of UVI (q90 after CQR,
day 9). The displayed level follows the point estimate; the alert level, burn time and advice
follow the upper bound. Output is an estimate for education and warning, not a medical diagnosis.
"""

from __future__ import annotations

import math
from typing import Any

from src.metrics import WHO_LEVELS, WHO_LEVELS_EN, who_level

ERYTHEMAL_WM2_PER_UVI = 0.025
MED_J_M2 = {"I": 200, "II": 250, "III": 350, "IV": 450, "V": 600, "VI": 1000}
MIN_UVI_FOR_BURN = 0.5  # below this the burn time is not meaningful (night, dawn)
WHO_COLORS = ["#3E9B4F", "#D9A400", "#E36B12", "#D22F3A", "#8A3FC2"]
DISCLAIMER = "ค่านี้เป็นการประมาณเพื่อการศึกษาและการเตือนเท่านั้น ไม่ใช่การวินิจฉัยทางการแพทย์"
ADVICE = [
    ["ออกกลางแจ้งได้ตามปกติ", "ถ้าอยู่กลางแจ้งนานหรืออยู่ใกล้น้ำ/ทราย ควรใส่แว่นกันแดด"],
    [
        "ทาครีมกันแดด SPF 30+ PA+++ ถ้าอยู่กลางแจ้งนานกว่า 30 นาที",
        "สวมหมวกและแว่นกันแดด",
        "หาที่ร่มช่วงใกล้เที่ยงวัน",
    ],
    [
        "ทาครีมกันแดด SPF 30+ PA+++ และทาซ้ำทุก 2 ชั่วโมง",
        "สวมเสื้อแขนยาว หมวกปีกกว้าง และแว่นกันแดด",
        "ลดเวลากลางแจ้งช่วง 10:00–15:00 น.",
    ],
    [
        "ทาครีมกันแดด SPF 50+ PA++++ และทาซ้ำทุก 2 ชั่วโมง",
        "หลีกเลี่ยงแดดช่วง 10:00–15:00 น. อยู่ในที่ร่มให้มากที่สุด",
        "สวมเสื้อแขนยาว หมวกปีกกว้าง และแว่นกันแดดที่กัน UV",
    ],
    [
        "หลีกเลี่ยงการออกกลางแจ้ง ผิวอาจไหม้ได้ภายในไม่กี่นาที",
        "ถ้าจำเป็นต้องออก ทาครีมกันแดด SPF 50+ PA++++ และทาซ้ำทุก 2 ชั่วโมง",
        "สวมเสื้อแขนยาว หมวกปีกกว้าง แว่นกันแดด และกางร่ม",
    ],
]


def normalize_skin_type(skin_type: str | int) -> str:
    """Return the Fitzpatrick skin type as a Roman numeral ``"I"`` … ``"VI"``.

    Args:
        skin_type: Roman numeral (any case) or integer 1-6.

    Returns:
        Upper-case Roman numeral.
    """
    roman = list(MED_J_M2)
    if isinstance(skin_type, int) and not isinstance(skin_type, bool):
        if 1 <= skin_type <= 6:
            return roman[skin_type - 1]
    elif isinstance(skin_type, str) and skin_type.strip().upper() in MED_J_M2:
        return skin_type.strip().upper()
    raise ValueError(f"unknown skin type {skin_type!r}; use I-VI or 1-6")


def level_index(uvi: float) -> int:
    """WHO level index 0-4 of one UVI value (via ``metrics.who_level``).

    Args:
        uvi: UV index.

    Returns:
        0 = ต่ำ … 4 = รุนแรงมาก.
    """
    return int(who_level(uvi))


def burn_minutes(uvi_upper: float, skin_type: str | int) -> int | None:
    """Minutes until the MED is reached at a constant UVI (rounded down, conservative).

    Args:
        uvi_upper: Upper-quantile UVI (q90 after CQR).
        skin_type: Fitzpatrick type.

    Returns:
        Whole minutes, or None when ``uvi_upper < MIN_UVI_FOR_BURN``.
    """
    med = MED_J_M2[normalize_skin_type(skin_type)]
    if uvi_upper is None or not math.isfinite(uvi_upper) or uvi_upper < MIN_UVI_FOR_BURN:
        return None
    return int(med / (uvi_upper * ERYTHEMAL_WM2_PER_UVI * 60))


def advice(uvi_upper: float, skin_type: str | int) -> list[str]:
    """Thai SPF/PA and behaviour advice for the level of the upper bound.

    Args:
        uvi_upper: Upper-quantile UVI.
        skin_type: Fitzpatrick type.

    Returns:
        List of Thai sentences (level advice + burn-time sentence when meaningful).
    """
    lines = list(ADVICE[level_index(uvi_upper)])
    minutes = burn_minutes(uvi_upper, skin_type)
    if minutes is not None and level_index(uvi_upper) >= 1:
        st = normalize_skin_type(skin_type)
        lines.append(f"ผิวชนิด {st} อาจไหม้แดดภายในประมาณ {minutes} นาที ถ้าไม่ป้องกัน")
    return lines


def assess(uvi: float, uvi_range: tuple[float, float], skin_type: str | int) -> dict[str, Any]:
    """Full risk assessment for one moment.

    Args:
        uvi: Point estimate of UVI.
        uvi_range: ``(lower, upper)``; the upper bound drives warnings.
        skin_type: Fitzpatrick type.

    Returns:
        Dict with ``uvi``, ``uvi_range``, ``level`` (Thai, point estimate), ``level_en``,
        ``level_index``, ``color``, ``alert_level`` / ``alert_level_index`` (upper bound),
        ``skin_type``, ``burn_minutes``, ``advice`` and ``disclaimer``.
    """
    lo, hi = float(uvi_range[0]), float(uvi_range[1])
    if lo > hi:
        raise ValueError("uvi_range must be (lower, upper)")
    hi = max(hi, float(uvi))
    i, j = level_index(uvi), level_index(hi)
    st = normalize_skin_type(skin_type)
    return {
        "uvi": float(uvi),
        "uvi_range": [lo, hi],
        "level": WHO_LEVELS[i],
        "level_en": WHO_LEVELS_EN[i],
        "level_index": i,
        "color": WHO_COLORS[i],
        "alert_level": WHO_LEVELS[j],
        "alert_level_index": j,
        "skin_type": st,
        "burn_minutes": burn_minutes(hi, st),
        "advice": advice(hi, st),
        "disclaimer": DISCLAIMER,
    }
