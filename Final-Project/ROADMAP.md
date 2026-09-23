# UV Guard — Roadmap 30 วัน

วันเริ่ม: 2026-09-23 · วันจบ: 2026-10-22
ติ๊ก `[x]` เมื่อเสร็จ · งานค้างให้เขียนโน้ตใต้ข้อนั้นขึ้นต้นด้วย `> ค้าง:`

---

## Phase 1: ข้อมูล + ฟิสิกส์ (วัน 1–5)

### วัน 1 — ตั้งโปรเจกต์ + ดึงข้อมูล
- [x] ตั้ง venv + `requirements.txt` + ติดตั้งแพ็กเกจ
- [x] `source_code/src/fetch_data.py` ดึงข้อมูลรายชั่วโมงย้อนหลัง 2–3 ปีของปทุมธานี (uv_index, uv_index_clear_sky, cloud_cover, relative_humidity_2m, temperature_2m)
- [x] ดึง Air Quality API (aerosol_optical_depth, dust, pm2_5, ozone)
- [x] ดึง NASA POWER hourly (ALLSKY_SFC_UVA, ALLSKY_SFC_UVB, ALLSKY_SFC_UV_INDEX, CLRSKY_SFC_SW_DWN, ALLSKY_SFC_SW_DWN, CLOUD_AMT) ช่วงเวลาเดียวกัน
  > หมายเหตุ: community AG ส่งหน่วย MJ/m²/hr → แปลงเป็น W/m² แล้วใน `convert_nasapower_units`; ALLSKY_SFC_UV_INDEX เป็น UVI อยู่แล้ว ("W m-2 x 40")
  > ตรวจวัน 2: จุดยอด UV ของ NASA POWER (~05 UTC) เร็วกว่า Open-Meteo (~05–06 UTC) ประมาณ 1 ชม. — เช็ก convention ของ timestamp ก่อน merge; UVI สูงสุดของ Open-Meteo แค่ 9.3; ozone ผิวพื้นมีค่าสูงผิดปกติ (สูงสุด 666 µg/m³)
- [ ] สมัคร NASA Earthdata account (ใช้ดึง OMI ในวัน 2) (ทำเอง)
  > ค้าง: ผู้ใช้ต้องสมัครเองที่ https://urs.earthdata.nasa.gov แล้วใส่ EARTHDATA_USERNAME / EARTHDATA_PASSWORD ใน `.env`
→ `dataset/raw/openmeteo_*.csv`, `dataset/raw/nasapower_*.csv`

### วัน 2 — ข้อมูลตรวจสอบ + ทำความสะอาด + EDA
- [ ] ดึง TEMIS UV index รายวัน (ฟ้าใส + มีเมฆ) ของจุดที่ใกล้ปทุมธานีที่สุด → `dataset/validation/temis_*.csv`
- [ ] ดึง OMI OMUVB (UVI + irradiance 305/310/324/380 nm) ด้วย earthaccess → `dataset/validation/omi_*.csv`
- [ ] **ห้ามใช้ TEMIS / OMI ในการฝึกหรือ tuning** เก็บไว้ทดสอบวัน 10 เท่านั้น
- [ ] รวมไฟล์ฝึก (Open-Meteo + NASA POWER) ตามเวลา UTC, จัดการ missing values, ตัดช่วงกลางคืน
- [ ] กราฟ UV ตามชั่วโมง / เดือน / ฤดูกาล
- [ ] Correlation heatmap
- [ ] เทียบ UVI ของ Open-Meteo กับ NASA POWER (ดูว่าสองแหล่งต่างกันแค่ไหน)
→ `source_code/notebooks/01_eda.ipynb`

### วัน 3 — UVI ฟ้าใส (Madronich)
- [ ] `source_code/src/physics.py`: มุมเซนิทด้วย pvlib
- [ ] `uvi_clear()` ตามสูตรใน rules
- [ ] เทียบกับ uv_index_clear_sky ของ Open-Meteo
→ `source_code/src/physics.py`

### วัน 4 — UVA / UVB ฟ้าใส (spectrl2)
- [ ] คำนวณสเปกตรัมด้วย `pvlib.spectrum.spectrl2`
- [ ] อินทิเกรต UVB (300–315 nm) และ UVA (315–400 nm)
- [ ] เทียบ UVA/UVB ฟ้าใสกับ NASA POWER ในวันที่ฟ้าเปิด (ตรวจหน่วย W/m² ให้ตรงกัน)
- [ ] Unit test โมดูลฟิสิกส์
→ `source_code/tests/test_physics.py`

### วัน 5 — Feature engineering + target
- [ ] cos(SZA), sin/cos ชั่วโมงและเดือน
- [ ] target CMF = uv_index / uv_index_clear_sky (Open-Meteo)
- [ ] target CMF_A = UVA_POWER / UVA_ฟ้าใส และ CMF_B = UVB_POWER / UVB_ฟ้าใส
- [ ] features จากทั้งสองแหล่ง: เมฆ Open-Meteo + CLOUD_AMT และ clear-sky index (ALLSKY / CLRSKY SW) ของ NASA POWER
- [ ] บันทึก dataset
→ `dataset/processed/train.parquet`

**Checkpoint วัน 5: Dataset พร้อมฝึก**

---

## Phase 2: ML หลัก (วัน 6–10)

### วัน 6 — Baseline + XGBoost
- [ ] Linear Regression baseline
- [ ] XGBoost ทำนาย CMF
- [ ] วัด MAE / RMSE / R² บนสเกล UVI

### วัน 7 — Multi-Output + TimeSeriesSplit
- [ ] MultiOutputRegressor ทำนาย [CMF_UVI, CMF_A, CMF_B] (target UVA/UVB จาก NASA POWER)
- [ ] TimeSeriesSplit 5 folds
- [ ] ตรวจ data leakage

### วัน 8 — Optuna tuning
- [ ] กำหนด search space
- [ ] รัน 50–100 trials
- [ ] บันทึก best params

### วัน 9 — Quantile Regression
- [ ] quantile 0.1 / 0.5 / 0.9
- [ ] ตรวจ coverage ของช่วง (~80%)

### วัน 10 — ประเมินผล + Risk Engine
- [ ] Confusion matrix + Recall ระดับสูง
- [ ] **ทดสอบอิสระ:** เทียบค่าช่วงเที่ยงวันกับ TEMIS (UVI) และ OMI (UVI, 305/310 nm ≈ UVB, 324/380 nm ≈ UVA) รายงาน MAE แยกตามแหล่ง
- [ ] `source_code/src/risk.py`: ระดับ WHO, MED, เวลาผิวไหม้, คำแนะนำ SPF/PA
- [ ] บันทึกโมเดลทั้งหมด

**Checkpoint วัน 10: MAE < 1.0 UVI**

---

## Phase 3: ML ขั้นสูง (วัน 11–15)

### วัน 11 — LSTM: เตรียมข้อมูล
- [ ] sliding window 48 ชม. → 24 ชม.
- [ ] scale + แบ่งตามเวลา

### วัน 12 — LSTM: ฝึกและเทียบผล
- [ ] ฝึก LSTM/GRU พยากรณ์ 6–24 ชม.
- [ ] เทียบกับพยากรณ์ Open-Meteo

### วัน 13 — CNN: เตรียม dataset (ไม่ใช้ภาพถ่ายเอง)
- [ ] ดาวน์โหลด CCSN, SWIMCAT, SWIMSEG, SKIPP'D (หรือ CloudCV) + ตรวจ license
- [ ] แปลงภาพ fisheye ให้ใกล้ภาพมือถือ (crop กลางภาพ, perspective transform)
- [ ] augmentation (ความสว่าง, white balance, blur, หมุน) + แบ่ง train/val/test

### วัน 14 — CNN: Transfer Learning
- [ ] MobileNetV3 pre-train ด้วย CCSN + SWIMCAT (สภาพท้องฟ้า)
- [ ] head สัดส่วนเมฆจาก SWIMSEG + baseline red/blue ratio
- [ ] head ค่าการลดแสงจาก SKIPP'D / CloudCV + ประเมินผลบน test split

### วัน 15 — Ensemble (Stacking)
- [ ] CNN features → XGBoost
- [ ] meta-model + เทียบกับโมเดลเดี่ยว

**Checkpoint วัน 15: LSTM + CNN + Ensemble ทำงาน**

---

## Phase 4: Backend + แอป (วัน 16–21)

### วัน 16 — FastAPI endpoints
- [ ] `/predict`, `/forecast`, `/sky-image`, `/health`

### วัน 17 — PostgreSQL schema
- [ ] users, push_tokens, measurements, notifications_log
- [ ] SQLAlchemy models + migration

### วัน 18 — Expo: หน้าหลัก
- [ ] สร้างโปรเจกต์ Expo + Expo Router
- [ ] การ์ด UV + ระดับสี
- [ ] การ์ด UVA / UVB + เวลาผิวไหม้

### วัน 19 — Expo: กราฟ + ตั้งค่า
- [ ] กราฟพยากรณ์รายชั่วโมง
- [ ] แบบสอบถามประเภทผิว 5 ข้อ
- [ ] หน้าตั้งค่าการแจ้งเตือน

### วัน 20 — กล้อง + เซนเซอร์แสง
- [ ] expo-camera ส่งภาพไป `/sky-image`
- [ ] LightSensor (Android) + ตรวจทิศทางมือถือ

### วัน 21 — เชื่อมครบวงจร
- [ ] flow ติดตั้ง → อนุญาตสิทธิ์ → ตอบคำถามผิว → เห็นผล
- [ ] ไม่อนุญาตตำแหน่ง → เลือกจังหวัดเอง

**Checkpoint วัน 21: แอปครบวงจร**

---

## Phase 5: ระบบแจ้งเตือน (วัน 22–24)

### วัน 22 — Local notification
- [ ] สรุปรายวัน 07:00
- [ ] ปุ่มออกแดด → เตือนที่ 80% ของเวลาผิวไหม้
- [ ] ปุ่มทาครีมแล้ว → เตือนทาซ้ำ 2 ชม.

### วัน 23 — Remote push
- [ ] APScheduler ทุก 30 นาที
- [ ] Expo Push Service
- [ ] cooldown + hysteresis + ช่วงเงียบ

### วัน 24 — ทดสอบบนมือถือจริง
- [ ] Android
- [ ] iOS (development build)
- [ ] ทดสอบทุกประเภทการแจ้งเตือน

**Checkpoint วัน 24: แจ้งเตือนบนมือถือจริง**

---

## Phase 6: ตรวจสอบ + ปิดงาน (วัน 25–30)

### วัน 25 — ภาคสนามด้วยมือถือ
- [ ] ใช้แอปเก็บข้อมูล: lux, ทิศทางมือถือ, เวลา, GPS ในหลายสภาพ (กลางแดด / ร่มไม้ / ใต้หลังคา / เมฆมาก) → `dataset/field/`
- [ ] ทดลองฟีเจอร์ถ่ายท้องฟ้าในแอปเพื่อเดโมเท่านั้น (ไม่นำภาพไปฝึกโมเดล)
- [ ] เทียบค่า UV ที่ระบบประเมินกับ Open-Meteo ณ เวลาและตำแหน่งเดียวกัน
- [ ] calibrate ค่า lux ของมือถือ → ตัวแยก "กลางแดด / ในร่ม" (exposure factor)

### วัน 26 — ทดสอบทั้งระบบ
- [ ] API + แอป + แจ้งเตือนพร้อมกัน
- [ ] บันทึกผลความแม่นยำสุดท้าย

### วัน 27 — วันสำรอง
- [ ] แก้บั๊กที่ค้าง

### วัน 28 — README + Diagram
- [ ] README (ติดตั้ง, วิธีใช้, ผลลัพธ์, ภาพหน้าจอ)
- [ ] diagram สถาปัตยกรรม

### วัน 29 — รายงาน
- [ ] บทนำ, ทฤษฎี, วิธีการ, ผลลัพธ์, ข้อจำกัด, งานต่อยอด

### วัน 30 — สไลด์ + วิดีโอเดโม
- [ ] สไลด์นำเสนอ
- [ ] วิดีโอเดโม 3–5 นาที

---

## ส่วนเสริม (ทำเมื่อมีเวลาเหลือ)
- [ ] Himawari cloud products (JAXA P-Tree) เป็น features ความหนาเมฆ
- [ ] ติดต่อขอข้อมูลวัด UV ภาคพื้นดินที่นครปฐม (ม.ศิลปากร) ใช้เป็น ground truth

## ถ้าช้ากว่าแผน ตัดตามลำดับนี้
1. CNN ภาพท้องฟ้า (วัน 13–15)
2. เซนเซอร์แสงมือถือ + calibrate
3. การเก็บข้อมูลภาคสนาม (วัน 25) เหลือแค่ทดสอบในที่เดียว
