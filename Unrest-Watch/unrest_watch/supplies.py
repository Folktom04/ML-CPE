"""Emergency stockpile planner built around the Thai 5 food groups (อาหารหลัก 5 หมู่).

หมู่ 1 โปรตีน (เนื้อสัตว์ ไข่ นม ถั่ว)    -> measured in grams of protein
หมู่ 2 คาร์โบไฮเดรต (ข้าว แป้ง)            -> grams of carbohydrate
หมู่ 3 เกลือแร่ (ผัก)                       -> vegetable servings (1 ทัพพี ~ 80 g)
หมู่ 4 วิตามิน (ผลไม้)                      -> fruit servings
หมู่ 5 ไขมัน (น้ำมัน ถั่วเปลือกแข็ง)       -> grams of fat
Energy (kcal) and water are checked on top of the five groups.

Daily needs are rounded from the Thai DRI 2020 (กรมอนามัย) and are a planning
guide, not medical advice.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

GROUPS_TH = {
    1: "หมู่ 1 โปรตีน (เนื้อสัตว์ ไข่ นม ถั่ว)",
    2: "หมู่ 2 คาร์โบไฮเดรต (ข้าว แป้ง)",
    3: "หมู่ 3 เกลือแร่ (ผัก)",
    4: "หมู่ 4 วิตามิน (ผลไม้)",
    5: "หมู่ 5 ไขมัน (น้ำมัน ถั่ว)",
}
# Which nutrient total stands for each group
GROUP_METRIC = {1: "protein", 2: "carb", 3: "veg", 4: "fruit", 5: "fat"}
METRIC_TH = {"kcal": "พลังงาน", "protein": "โปรตีน", "carb": "คาร์โบไฮเดรต",
             "veg": "ผัก", "fruit": "ผลไม้", "fat": "ไขมัน", "water": "น้ำดื่ม"}


@dataclass(frozen=True)
class Need:
    kcal: float
    protein: float  # g
    carb: float     # g
    fat: float      # g
    veg: float      # servings
    fruit: float    # servings
    water: float    # litres to drink + basic hygiene


PROFILES = {
    "adult":   Need(kcal=2000, protein=60, carb=275, fat=55, veg=3, fruit=2, water=4.0),
    "child":   Need(kcal=1400, protein=40, carb=195, fat=40, veg=2, fruit=2, water=3.0),
    "elderly": Need(kcal=1700, protein=55, carb=230, fat=47, veg=3, fruit=2, water=3.5),
}


@dataclass(frozen=True)
class Item:
    key: str
    name_th: str
    unit_th: str
    group: int
    kcal: float
    protein: float
    carb: float
    fat: float
    veg: float = 0.0
    fruit: float = 0.0
    water: float = 0.0       # litres this unit provides
    cook_water: float = 0.0  # litres needed to cook one unit
    shelf_days: int = 365


CATALOG: dict[str, Item] = {i.key: i for i in [
    # หมู่ 1 โปรตีน
    Item("canned_fish", "ปลากระป๋องในซอสมะเขือเทศ", "กระป๋อง 155 ก.", 1, 230, 22, 5, 13, shelf_days=1095),
    Item("canned_tuna", "ทูน่ากระป๋อง", "กระป๋อง 165 ก.", 1, 130, 28, 0, 1.5, shelf_days=1095),
    Item("uht_milk", "นม UHT รสจืด", "กล่อง 200 มล.", 1, 130, 6.4, 10, 7, water=0.2, shelf_days=180),
    Item("dried_beans", "ถั่วเขียว/ถั่วแดงแห้ง", "ถุง 1 กก.", 1, 3400, 240, 600, 12, cook_water=3.0, shelf_days=365),
    Item("eggs", "ไข่ไก่", "แผง 30 ฟอง", 1, 2250, 190, 12, 150, cook_water=1.0, shelf_days=21),
    # หมู่ 2 คาร์โบไฮเดรต
    Item("rice", "ข้าวสาร", "ถุง 5 กก.", 2, 18000, 350, 3950, 30, cook_water=8.0, shelf_days=365),
    Item("instant_noodles", "บะหมี่กึ่งสำเร็จรูป", "ซอง 55 ก.", 2, 250, 5, 35, 10, cook_water=0.4, shelf_days=180),
    Item("crackers", "แครกเกอร์/ขนมปังกรอบ", "ห่อ 250 ก.", 2, 1150, 22, 175, 40, shelf_days=270),
    # หมู่ 3 เกลือแร่ (ผัก)
    Item("canned_veg", "ผักรวมกระป๋อง", "กระป๋อง 400 ก.", 3, 150, 6, 28, 1, veg=3, shelf_days=730),
    Item("canned_corn", "ข้าวโพดหวานกระป๋อง", "กระป๋อง 425 ก.", 3, 230, 7, 48, 3, veg=3, shelf_days=730),
    Item("pickled_greens", "ผักกาดดองกระป๋อง", "กระป๋อง 140 ก.", 3, 50, 1, 10, 0, veg=1.5, shelf_days=730),
    # หมู่ 4 วิตามิน (ผลไม้)
    Item("canned_fruit", "ผลไม้กระป๋อง (ลิ้นจี่/สับปะรด)", "กระป๋อง 565 ก.", 4, 300, 1, 75, 0, fruit=4, shelf_days=730),
    Item("dried_fruit", "ผลไม้อบแห้ง (กล้วยตาก/ลูกเกด)", "ห่อ 200 ก.", 4, 600, 5, 150, 1, fruit=5, shelf_days=270),
    Item("fruit_juice", "น้ำผลไม้ 100% UHT", "กล่อง 1 ลิตร", 4, 450, 3, 105, 0, fruit=4, water=1.0, shelf_days=270),
    # หมู่ 5 ไขมัน
    Item("cooking_oil", "น้ำมันพืช", "ขวด 1 ลิตร", 5, 8200, 0, 0, 920, shelf_days=540),
    Item("peanuts", "ถั่วลิสงอบ", "ห่อ 500 ก.", 5, 2900, 130, 80, 250, shelf_days=180),
    # น้ำ
    Item("water", "น้ำดื่ม", "แพ็ค 6 ขวด × 1.5 ลิตร", 0, 0, 0, 0, 0, water=9.0, shelf_days=730),
]}

# How each group's need is split between items (only items whose shelf life
# covers the plan are used; the rest of the share is spread over the others).
SHARES = {
    2: {"rice": 0.70, "instant_noodles": 0.15, "crackers": 0.15},
    1: {"canned_fish": 0.35, "canned_tuna": 0.15, "uht_milk": 0.20, "dried_beans": 0.15, "eggs": 0.15},
    3: {"canned_veg": 0.5, "canned_corn": 0.3, "pickled_greens": 0.2},
    4: {"canned_fruit": 0.4, "dried_fruit": 0.4, "fruit_juice": 0.2},
    5: {"cooking_oil": 0.6, "peanuts": 0.4},
}

CHECKLIST = {
    "green": ["ยาประจำตัว 7 วัน", "ไฟฉาย + ถ่านสำรอง", "พาวเวอร์แบงก์ชาร์จเต็ม",
              "ชุดปฐมพยาบาล", "สำเนาเอกสารสำคัญ (บัตรประชาชน ทะเบียนบ้าน พาสปอร์ต)"],
    "yellow": ["เงินสดย่อย (ระบบธนาคาร/ATM อาจล่ม)", "วิทยุใช้ถ่าน/ไขลาน", "น้ำมันรถเต็มถัง",
               "ผงเกลือแร่ ORS", "วิตามินรวม (ชดเชยผักผลไม้สด)", "แก๊สกระป๋อง + เตาพกพา"],
    "orange": ["ยาประจำตัว 30 วัน", "ถุงขยะ/ทิชชูเปียก/สบู่ (สุขอนามัย)", "ยากันยุง",
               "นกหวีด + แผนนัดพบครอบครัว", "กระเป๋าฉุกเฉินพร้อมหยิบ (go-bag)", "เม็ดฟอกน้ำ/เครื่องกรองน้ำ"],
    "red": ["วางแผนเส้นทางอพยพ 2 เส้นทาง", "ติดตามประกาศทางการ (ปภ. 1784)",
            "แจ้งญาติ/สถานทูตถึงที่อยู่ของคุณ", "อยู่ห่างจากจุดชุมนุมและสถานที่ราชการ"],
}
LEVEL_ORDER = ["green", "yellow", "orange", "red"]


@dataclass
class Household:
    adults: int = 1
    children: int = 0
    elderly: int = 0

    def daily_need(self) -> Need:
        counts = {"adult": self.adults, "child": self.children, "elderly": self.elderly}
        fields = Need.__dataclass_fields__
        total = {f: sum(getattr(PROFILES[k], f) * n for k, n in counts.items()) for f in fields}
        return Need(**total)

    @property
    def size(self) -> int:
        return self.adults + self.children + self.elderly


def _totals(quantities: dict[str, float]) -> dict[str, float]:
    t = dict.fromkeys(["kcal", "protein", "carb", "fat", "veg", "fruit", "water", "cook_water"], 0.0)
    for key, qty in quantities.items():
        item = CATALOG[key]
        for f in t:
            t[f] += getattr(item, f) * qty
    return t


def _usable_shares(group: int, days: int) -> dict[str, float]:
    shares = {k: s for k, s in SHARES[group].items() if CATALOG[k].shelf_days >= days}
    total = sum(shares.values())
    return {k: s / total for k, s in shares.items()}


def plan(household: Household, days: int) -> dict:
    """Shopping list that covers all 5 groups, energy and water for `days` days."""
    need = household.daily_need()
    req = {f: getattr(need, f) * days for f in Need.__dataclass_fields__}
    qty: dict[str, float] = {}

    def fill(group: int, amount: float) -> None:
        metric = GROUP_METRIC[group]
        for key, share in _usable_shares(group, days).items():
            per_unit = getattr(CATALOG[key], metric)
            if amount > 0 and per_unit > 0:
                qty[key] = qty.get(key, 0) + math.ceil(amount * share / per_unit)

    fill(2, req["carb"] * 0.85)                         # staples first, veg/fruit add carbs too
    fill(1, max(req["protein"] * 0.5, req["protein"] - _totals(qty)["protein"]))
    fill(3, req["veg"])
    fill(4, req["fruit"])
    fill(5, max(req["fat"] * 0.25, req["fat"] - _totals(qty)["fat"]))

    # top up energy with rice (cheap, keeps a year)
    short = req["kcal"] - _totals(qty)["kcal"]
    if short > 0:
        qty["rice"] = qty.get("rice", 0) + math.ceil(short / CATALOG["rice"].kcal)

    t = _totals(qty)
    water_need = req["water"] + t["cook_water"] - t["water"]
    qty["water"] = max(0, math.ceil(water_need / CATALOG["water"].water))
    return {"days": days, "household": household, "quantities": qty,
            "coverage": days_supported(qty, household)}


def days_supported(inventory: dict[str, float], household: Household) -> dict:
    """How many days the given stock lasts, per nutrient, and which one runs out first."""
    unknown = [k for k in inventory if k not in CATALOG]
    if unknown:
        raise KeyError(f"ไม่รู้จักรายการ: {', '.join(unknown)} (ดูรายการด้วย --list-items)")
    need = household.daily_need()
    t = _totals(inventory)
    water_for_cooking = t["cook_water"]
    per_metric = {}
    for m in ["kcal", "protein", "carb", "fat", "veg", "fruit"]:
        per_metric[m] = t[m] / getattr(need, m)
    # cooking water is used up front, the rest is drunk
    per_metric["water"] = max(0.0, t["water"] - water_for_cooking) / need.water
    limiting = min(per_metric, key=per_metric.get)
    groups = {g: per_metric[GROUP_METRIC[g]] for g in GROUPS_TH}
    survival = min(per_metric["kcal"], per_metric["water"])  # can live on, but unbalanced
    return {"per_metric": per_metric, "groups": groups, "balanced_days": per_metric[limiting],
            "survival_days": survival, "limiting": limiting}


def checklist(level: str) -> list[str]:
    out = []
    for lv in LEVEL_ORDER[: LEVEL_ORDER.index(level) + 1]:
        out += CHECKLIST[lv]
    return out
