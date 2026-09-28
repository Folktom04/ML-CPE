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
  > หมายเหตุ (แก้วัน 2): เปลี่ยนจาก community AG เป็น **RE** เพราะ AG ปัดเป็น 0.01 MJ/hr (ขั้นละ 2.78 W/m²) ทำให้ UVB แทบเป็น 0 ทั้งหมด ส่วน RE ให้ Wh/m² ต่อชั่วโมง ซึ่งเท่ากับ W/m² เฉลี่ย; ALLSKY_SFC_UV_INDEX เป็น UVI อยู่แล้ว ("W m-2 x 40")
  > ตรวจแล้ววัน 2: timestamp ต่างกัน 1 ชม. จริง (POWER ใช้ label ต้นชั่วโมง, Open-Meteo ใช้ปลายชั่วโมง) → เลื่อน POWER +1 ชม. ใน `preprocess.py`; ozone > 400 µg/m³ ตั้งเป็น NaN แล้ว interpolate
- [x] สมัคร NASA Earthdata account (ใช้ดึง OMI ในวัน 2) (ทำเอง)
  > หมายเหตุ: ต้อง authorize แอป "NASA GESDISC DATA ARCHIVE" ในหน้า Earthdata ด้วย ไม่อย่างนั้นจะเจอ `EulaNotAccepted`
→ `dataset/raw/openmeteo_*.csv`, `dataset/raw/nasapower_*.csv`

### วัน 2 — ข้อมูลตรวจสอบ + ทำความสะอาด + EDA
- [x] ดึง TEMIS UV index รายวัน (ฟ้าใส + มีเมฆ) ของจุดที่ใกล้ปทุมธานีที่สุด → `dataset/validation/temis_*.csv`
  > หมายเหตุ: สถานี Bangkok (13.667N, 100.612E) มีเฉพาะ **ฟ้าใส** (คอลัมน์ฟ้ามีเมฆเป็น -1 เพราะอยู่นอกพื้นที่ MSG) ได้ `temis_select_2023.csv` (365 แถว) และ `temis_holdout_2025.csv` (ยังไม่ได้เปิดดู; ตั้งแต่วัน 6 ไม่เขียนปี 2024 แล้วเพราะซ้อนกับ dev)
- [x] ดึง OMI OMUVB (UVI + irradiance 305/310/324/380 nm) ด้วย earthaccess → `dataset/validation/omi_*.csv`
  > ดึงเฉพาะปี 2023 → `omi_select_2023.csv` (364 วัน, missing 24%) ตรวจพิกเซลแล้ว: CSUVindex เทียบ TEMIS ได้ MAE 0.97, r 0.86 ส่วนปี 2025 ให้รัน `--split test` ในวัน 10 (ไม่ใช้ปี 2024)
- [x] **ห้ามใช้ TEMIS / OMI ในการฝึกหรือ tuning**: ปี 2023 ใช้ได้เฉพาะเลือกแหล่ง target ใน `02_source_selection.ipynb` ส่วนปี 2025 เก็บไว้ทดสอบวัน 10 และไม่ใช้ปี 2024 (ซ้อนกับ dev) (กฎอยู่ใน `.agents/rules/00-project-context.md` และบังคับผ่าน `load_validation()`)
- [x] รวมไฟล์ฝึก (Open-Meteo + NASA POWER) ตามเวลา UTC, จัดการ missing values, ตัดช่วงกลางคืน → `dataset/processed/train_merged.parquet` (13,280 ชม. กลางวัน)
- [x] กราฟ UV ตามชั่วโมง / เดือน / ฤดูกาล
- [x] Correlation heatmap
- [x] เทียบ UVI ของ Open-Meteo กับ NASA POWER (ดูว่าสองแหล่งต่างกันแค่ไหน)
  > รายชั่วโมง: MAE 1.09, bias −0.05, r 0.87
- [x] `02_source_selection.ipynb` เลือกแหล่ง target (Open-Meteo vs NASA POWER) ด้วย TEMIS/OMI ปี 2023 เท่านั้น
  > **เกณฑ์ที่ประกาศไว้ก่อนดูผล:** ตัวชี้วัดหลักคือ MAE ของ UVI ฟ้ามีเมฆเทียบ OMI `UVindex` ตอนเที่ยงสุริยะ ปี 2023 จะเลือก NASA POWER ก็ต่อเมื่อ MAE ต่ำกว่า Open-Meteo เกิน 0.3 UVI ไม่อย่างนั้นใช้ Open-Meteo
  > **ผล: NASA POWER** — MAE (n=275): Open-Meteo **2.428** vs NASA POWER **1.143** (ต่างกัน 1.285 > 0.3) bias −2.34 vs −0.99, r 0.40 vs 0.78; Open-Meteo อิ่มตัวที่ ~9.3 และ clear-sky ต่ำกว่า TEMIS 3.5 UVI → ตาราง `docs/source_selection_2023.csv`
  > **ตัดสินแล้ว (ผู้ใช้ยืนยัน):** ground truth และ target ทั้ง CMF_UVI, CMF_A, CMF_B มาจาก NASA POWER โดยตัวหารของ CMF_UVI คือ `uvi_clear()` (Madronich วัน 3) ส่วน Open-Meteo ใช้เป็น features ได้ และยังเป็นแหล่ง input ตอน inference / field validation เพราะ NASA POWER ไม่ใช่ข้อมูล real-time (แก้ใน `.agents/rules/00-project-context.md` แล้ว)
→ `source_code/notebooks/01_eda.ipynb`, `source_code/notebooks/02_source_selection.ipynb`

### วัน 3 — UVI ฟ้าใส (Madronich)
- [x] `source_code/src/physics.py`: มุมเซนิทด้วย pvlib
- [x] `uvi_clear()` ตามสูตรใน rules
- [x] ozone climatology รายเดือนจาก NASA POWER TO3 ปี 2023–2025 → `source_code/models/ozone_climatology_v1.json` (243–278 DU) ใช้เป็นค่าเริ่มต้นทั้งตอนฝึกและตอนใช้งาน และใช้เติม TO3 ที่ขาด
  > เทียบกับ TO3 จริง: climatology ต่างเฉลี่ย 2.2% ของ UVI (p95 4.2%) ส่วน 300 DU ต่ำเป็นระบบ −15.2% (ถึง −23% ในเดือนหนาว)
- [x] เทียบกับ uv_index_clear_sky ของ Open-Meteo และ ALLSKY_SFC_UV_INDEX ของ NASA POWER ในชั่วโมงที่ฟ้าเปิด (ใช้ข้อมูลฝึกเท่านั้น ห้ามใช้ TEMIS/OMI)
  > หมายเหตุ: `uvi_clear()` คือตัวหารของ CMF_UVI (ตัดสินในวัน 2)
  > Open-Meteo clear-sky: bias −1.45 UVI, r 0.99 (รูปร่างตรง ระดับต่ำ); NASA POWER ชั่วโมงฟ้าเปิด (n=1,659): ได้ 0.72 เท่าของ Madronich (bias −1.9) และอัตราส่วนลดลงตาม AOD (0.80 → 0.66, r −0.47) → **CMF จะรวมผลของฝุ่นละอองด้วย ในวันฟ้าเปิดจึงอยู่ราว 0.7–0.8** วัน 5 ต้องใส่ AOD/PM2.5 เป็น feature
- [x] เลือกว่าตัวหารของ CMF คำนวณที่จุดกึ่งกลางชั่วโมง หรือเป็นค่าเฉลี่ยทั้งชั่วโมง
  > **ตัดสินแล้ว (ผู้ใช้ยืนยัน): ใช้ค่าเฉลี่ยทั้งชั่วโมง** `uvi_clear_interval(..., substeps=CMF_SUBSTEPS)` (= 12) เพราะ NASA POWER เป็นค่าเฉลี่ยรายชั่วโมง ถ้าใช้จุดกึ่งกลางจะต่างกัน < 1% ช่วงกลางวัน แต่ 6–10% (สูงสุด 13%) ในชั่วโมงแรกและสุดท้ายของวัน; แก้ rules แล้ว และ spectrl2 วัน 4 ต้องเฉลี่ยแบบเดียวกัน
→ `source_code/src/physics.py`, `source_code/notebooks/03_clear_sky.ipynb`

### วัน 4 — UVA / UVB ฟ้าใส (spectrl2)
- [x] คำนวณสเปกตรัมด้วย `pvlib.spectrum.spectrl2` → `clear_sky_spectrum()`, `uva_uvb_clear_interval()` ใน `physics.py`
  > **ตัดสินแล้ว (ผู้ใช้เลือกแบบ A):** ตัวหารของ CMF_A/CMF_B ใช้ **AOD = 0** เพื่อให้ CMF ทั้งสามตัวมีความหมายเดียวกันคือ "เมฆ + ฝุ่น" ร่วมกับ ozone climatology, ไอน้ำ 4 cm และค่าเฉลี่ยทั้งชั่วโมง (`CMF_SUBSTEPS`) แก้ rules แล้ว
- [x] อินทิเกรต UVB (300–315 nm) และ UVA (315–400 nm)
  > **ข้อจำกัด:** กริดของ SPECTRL2 เริ่มที่ 300 nm และช่วง UVB มี**แค่ 4 จุด** (300, 305, 310, 315 nm, ห่างกัน 5 nm) อินทิเกรตแบบ trapezoid ส่วน NASA POWER นิยาม UVB เป็น 280–315 nm อัตราส่วนในวันฟ้าเปิดของ UVB (0.85) ใกล้กับ UVA (0.87) แปลว่าส่วน 280–300 nm ที่ขาดไปมีผลน้อย แต่ความผิดพลาดจากกริดหยาบยังประเมินตรงไม่ได้ ต้องเขียนลงรายงาน
- [x] เทียบ UVA/UVB ฟ้าใสกับ NASA POWER ในวันที่ฟ้าเปิด (ตรวจหน่วย W/m² ให้ตรงกัน)
  > หน่วยตรงกัน: ชั่วโมงฟ้าเปิด (n=1,680) r 0.97; แบบ A: NASA/SPECTRL2 = 0.87 (UVA), 0.85 (UVB) และลดลงตาม AOD (0.93 → 0.80/0.77) เป็นแพทเทิร์นเดียวกับ CMF_UVI; แบบ B (AOD จริง) ได้ ≈ 1.10 และ**เพิ่มขึ้น**ตาม AOD แปลว่าลด UV มากเกินไปเมื่อฝุ่นหนา ส่วนไอน้ำไม่มีผล (0%) และ 300 DU ทำให้ UVB ต่ำ 14%
- [x] Unit test โมดูลฟิสิกส์
→ `source_code/tests/test_physics.py`, `source_code/notebooks/04_clear_sky_uva_uvb.ipynb`

### วัน 5 — Feature engineering + target
- [x] cos(SZA), sin/cos ชั่วโมงและเดือน
- [x] target CMF_UVI = NASA POWER ALLSKY_SFC_UV_INDEX / `uvi_clear_interval(..., substeps=CMF_SUBSTEPS)` (Madronich เฉลี่ยทั้งชั่วโมง + ozone climatology)
- [x] target CMF_A = UVA_POWER / UVA_ฟ้าใส และ CMF_B = UVB_POWER / UVB_ฟ้าใส (spectrl2 เฉลี่ยทั้งชั่วโมง)
  > CMF (p01–p99): UVI 0.25–0.88 (ค่ามัธยฐาน 0.63), A 0.31–0.96 (0.74), B 0.33–1.00 (0.75) มีแค่ `cmf_b` ~1% ที่เกิน 1 ยังไม่ clip เรื่องนี้จะตัดสินในวัน 6 (ตัดสินแล้ว: clip เฉพาะค่าทำนาย CMF เป็น [0, 1] ไม่ clip target ดูวัน 6 และ `train_cmf.py` `CMF_MIN`/`CMF_MAX`); CMF ลดลงตอนดวงอาทิตย์ต่ำ (UVI ~0.4 ที่ 17:30) จึงยังขึ้นกับเรขาคณิตด้วย
- [x] ~~features จากทั้งสองแหล่ง: เมฆ Open-Meteo + CLOUD_AMT และ clear-sky index (ALLSKY / CLRSKY SW) ของ NASA POWER~~ → **features มาจาก Open-Meteo หรือคำนวณจากเวลา/ตำแหน่งเท่านั้น** (ผู้ใช้ตัดสินในวัน 5 และเขียนลง rules แล้ว)
  > ตัด feature ทุกตัวที่มาจาก NASA POWER ออก (CLOUD_AMT, ALLSKY/CLRSKY SW, clear-sky index, TO3) เพราะไม่มีตอนใช้งานจริง และเป็น target leakage (แหล่งเดียวกับ target) แทนด้วย Open-Meteo `cloud_cover_low/mid/high`, `shortwave/direct/diffuse_radiation`, `precipitation` และ `om_kt` = shortwave / GHI ฟ้าใส (Haurwitz) รวม 23 features; `om_kt` สัมพันธ์กับ CMF_UVI +0.65 ซึ่งใกล้กับ clear-sky index ของ NASA ที่ตัดออก (+0.59)
- [x] บันทึก dataset → `dataset/processed/train.parquet` (11,173 ชม.) และสเปก `source_code/models/dataset_spec_v1.json` (รายการ feature/target สำหรับวัน 6 ขึ้นไปและ API)
→ `dataset/processed/train.parquet`, `source_code/src/features.py`, `source_code/notebooks/05_dataset.ipynb`

**Checkpoint วัน 5: Dataset พร้อมฝึก** → ✅ ตรวจแล้ว (`/checkpoint`): 11,156 แถว × 39 คอลัมน์ (2023: 3,712 / 2024: 3,726 / 2025: 3,718), features 23 ตัวครบ ไม่มีค่าหาย ไม่มี timestamp ซ้ำ ไม่มีคอลัมน์ NASA ใน features; CMF_UVI median 0.63 (5–95 %: 0.37–0.83)

---

## Phase 2: ML หลัก (วัน 6–10)

### วัน 6 — Baseline + XGBoost
> **การแบ่งข้อมูล (ตัดสินวัน 6, `src/splits.py`):** Train = 2023, Dev = 2024 (ใช้เทียบโมเดล, Optuna และ TimeSeriesSplit วัน 6–9) ส่วน **Test = 2025 ห้ามโหลด ดู หรือคำนวณ metric จนถึงวัน 10** (ทั้ง NASA POWER และ TEMIS/OMI) และไม่ใช้ TEMIS/OMI ปี 2024 เพราะซ้อนกับ dev
> **จุดที่เคยใช้ปี 2025 ก่อนวัน 6:** ozone climatology v1 สร้างจาก TO3 2023–2025 → **สร้างใหม่เป็น v2 จาก 2023–2024** แล้ว build `train.parquet` ใหม่; notebook EDA 01/03/04/05 และการประมาณ lag/เกณฑ์ ozone ใน `preprocess` เคยใช้ข้อมูลทั้ง 3 ปี (ไม่มีการเลือกโมเดลจากผลเหล่านั้น) ให้จดเป็นข้อจำกัดในรายงาน
- [x] Linear Regression baseline
- [x] XGBoost ทำนาย CMF → `source_code/models/cmf_xgb_v1.json` + `cmf_xgb_v1_metrics.json` (params คงที่ ยังไม่ tune)
- [x] วัด MAE / RMSE / R² บนสเกล UVI → `docs/baseline_dev_2024.csv`, `source_code/notebooks/06_baseline.ipynb`
  > **dev 2024 (สเกล UVI):** XGBoost MAE **0.462** / RMSE 0.718 / R² 0.943; Linear 0.473; CMF คงที่ 0.703; Open-Meteo `uv_index` ตรง ๆ 1.252 — ค่าที่ทำนาย clip CMF เป็น [0, 1] แต่ไม่ clip target
  > ⚠️ recall ระดับ**สูงมาก** 0.79 แต่ระดับ**รุนแรงมาก**แค่ **0.11** (6/53 ชม.; โมเดลทำนาย CMF 0.71 ขณะที่ค่าจริง 0.81 ตอนเที่ยงวันฟ้าเปิด) → วัน 9 ต้องตรวจ recall ด้วย q90 ซึ่งเป็นค่าที่ใช้เตือนจริงตาม rules

### วัน 7 — Multi-Output + TimeSeriesSplit
- [x] ทดลอง sample_weight (ไม่ถ่วง / `uvi_clear` / `uvi_clear²`) กับ XGBoost CMF_UVI บน dev 2024 → `docs/weight_experiment_dev_2024.csv`
  > MAE 0.462 / 0.459 / 0.461; recall สูงมาก 0.79 / 0.79 / 0.80; recall รุนแรงมาก 0.11 / 0.09 / 0.11 ใช้กฎที่ประกาศไว้ก่อน (ตัดแบบที่ MAE แย่กว่าค่าต่ำสุด > 0.02 แล้วเลือกแบบที่ recall เฉลี่ยของระดับเตือนสูงสุด) ได้ **`uvi_clear²`** แต่ความต่างอยู่ในระดับ noise **การถ่วงน้ำหนักจึงไม่ได้แก้ recall ระดับรุนแรงมาก** เพราะชั่วโมงระดับนี้มี NASA เฉลี่ย 10.98 ซึ่งอยู่เหนือเส้นแบ่ง 10.5 เพียงเล็กน้อย → ต้องเตือนด้วย q90 ในวัน 9
- [x] MultiOutputRegressor ทำนาย [CMF_UVI, CMF_A, CMF_B] (target UVA/UVB จาก NASA POWER) → `source_code/models/cmf_multi_xgb_v1.joblib` + metrics
  > dev 2024: UVI MAE 0.461 (R² 0.942), UVA MAE 2.93 W/m², UVB MAE 0.086 W/m² ใช้ weight `uvi_clear²` ชุดเดียวกันกับทุก target (ข้อจำกัดของ MultiOutputRegressor)
- [x] TimeSeriesSplit 5 folds (เฉพาะในช่วง 2023–2024 ห้ามรวมปี 2025) → `docs/cv_folds_2023_2024.csv`
  > gap 12 แถว (≈1 วัน) MAE 0.49 ± 0.08 UVI, UVA 3.05 ± 0.33 W/m², UVB 0.090 ± 0.011 W/m²; fold 2 (ก.ย.–ธ.ค. 2023) แย่ที่สุด (bias −0.44) เพราะฝึกด้วยข้อมูลไม่ครบฤดู → ต้องใช้ข้อมูลอย่างน้อย 1 ปีเต็ม
- [x] ตรวจ data leakage → `leakage_checks()` ใน `src/train_multi.py`, `docs/leakage_checks.csv`
  > ผ่านทั้ง 5 ข้อ: ไม่มีแถวปี 2025, ไม่มี feature ต้องห้าม, fold เรียงตามเวลาและมี gap, |Spearman| สูงสุด 0.66, โมเดลที่ฝึกกับ target สุ่มสลับได้ R² −0.10
→ `source_code/src/train_multi.py`, `source_code/notebooks/07_multioutput_cv.ipynb`

### วัน 8 — Optuna tuning
> ⚠️ **หลังวัน 8 ตัวเลข dev 2024 มี optimistic bias** เพราะ fold 3–5 ที่ใช้เป็น objective ของการ tune อยู่ในปี 2024 ตัวเลขที่ไม่ลำเอียงคือ **test 2025 ในวัน 10**
- [x] กำหนด search space (ประกาศก่อนรัน) → `search_space()` ใน `src/tune.py`
  > `n_estimators` 200–1500, `learning_rate` 0.01–0.2, `max_depth` 3–10, `min_child_weight` 1–30, `subsample` 0.5–1, `colsample_bytree` 0.4–1, `reg_lambda` 1e-3–10, `reg_alpha` 1e-4–1, `gamma` 1e-6–0.05 objective = UVI MAE ของ XGBoost CMF_UVI (weight `uvi_clear²`) เฉลี่ยบน fold 3–5 ของ TimeSeriesSplit(5, gap 12) ใน 2023–2024 (ฝึกด้วยข้อมูลอย่างน้อย 12 เดือน) กฎรับ params: MAE ดีกว่าเดิม > 0.01 **และ** recall เฉลี่ยระดับสูงมาก+รุนแรงมากลดลง ≤ 0.03
- [x] รัน 100 trials (TPE seed 42 + MedianPruner, study ใน `source_code/models/optuna_cmf_xgb_v1.db`, ทุก trial log recall) → `docs/optuna_trials.csv`
  > complete 42 / pruned 58; best #50 CV MAE **0.4466** เทียบกับ default 0.4579 (−0.0113) recall 0.443 เทียบกับ 0.438 → **ผ่านกฎแบบเฉียดฉิว** trial 10 อันดับแรกห่างกัน < 0.001 (ที่ราบ) `learning_rate` สำคัญที่สุด (fANOVA 44 %) และชนขอบล่าง 0.01 ส่วนที่ได้เพิ่มถ้าขยายช่วงน่าจะเล็กกว่า noise
- [x] บันทึก best params → `source_code/models/cmf_xgb_best_params_v1.json` และ multi-output ที่ใช้ params นี้ → `cmf_multi_xgb_v2.joblib` + metrics
  > dev 2024 (optimistic): UVI MAE 0.461 → **0.450**, UVA 2.93 → 2.87 W/m², UVB 0.086 → 0.084 W/m²; CV 5 folds: UVI 0.493 → 0.470 แต่ recall ระดับรุนแรงมากเฉลี่ย 0.20 → 0.16 → การ tune ไม่ได้แก้ระดับรุนแรงมาก ยังต้องเตือนด้วย q90 ในวัน 9
→ `source_code/src/tune.py`, `source_code/notebooks/08_optuna.ipynb`, `docs/tuning_dev_2024.csv`, `docs/cv_folds_2023_2024_tuned.csv`, `docs/figures/optuna_*.png`

### วัน 9 — Quantile Regression
- [x] quantile 0.1 / 0.5 / 0.9 (+ 0.75 ไว้เทียบการเตือน) → XGBoost `reg:quantileerror` ทำนาย CMF_UVI (params วัน 8, weight `uvi_clear²`, เรียงลำดับ quantile ต่อแถว) → `source_code/models/cmf_uvi_quantile_xgb_v1.json` + metrics
- [x] ตรวจ coverage ของช่วง (~80%) → `docs/quantile_cv_folds.csv`, `docs/quantile_dev_2024.csv`
  > ช่วงดิบ [q10, q90] **แคบเกินไป**: coverage CV fold 3–5 = 0.593, dev 2024 = 0.578 → ใช้ **CQR** ตามกฎที่ประกาศไว้ (split conformal บนสเกล CMF) ตรวจ: Q จาก fold 3–4 ทำให้ coverage ของ fold 5 เป็น 0.863; dev 2024 (Q จากปี 2023 = +0.050) ได้ **0.837** แต่ช่วงกว้างขึ้นจาก 0.81 เป็น 1.50 UVI; Q ของโมเดลสุดท้าย = **+0.038** (fold 3–5) ข้อจำกัด: coverage ไม่สม่ำเสมอ ระดับสูงมาก 0.76, รุนแรงมาก 0.70 (n = 10), เดือน มี.ค./ก.ค. 0.73 เพราะใช้ Q ค่าเดียว
- [x] เทียบการเตือนด้วย q50 / q75 / q90 (recall, precision, false alarm rate) บน dev 2024 และ CV fold 3–5 → `docs/quantile_alerts_*.csv`, `docs/figures/quantile_alerts.png`
  > เกณฑ์ที่ประกาศก่อนดูผล: เลือก quantile ต่ำสุดที่ recall รุนแรงมาก ≥ 0.8 และ precision ≥ สูงมาก ≥ 0.5 (CV fold 3–5) → **ไม่มีตัวไหนผ่าน ใช้ q90 (หลัง CQR) ตาม rules** CV fold 3–5: q50 recall รุนแรงมาก 0.11, q75 0.13, **q90 0.62** (precision 0.33); เตือน ≥ สูงมากด้วย q90 ได้ recall 0.99, precision 0.60, false alarm rate 0.16 บน dev 2024 ชั่วโมงรุนแรงมากทั้ง 53 ชม. ได้รับการเตือนอย่างน้อยระดับสูงมาก → วัน 22 ต้องใช้ cooldown/hysteresis เพราะ false alarm สูง
→ `source_code/src/quantile.py`, `source_code/notebooks/09_quantile.ipynb`, `docs/figures/quantile_*.png` (ตัวเลข dev 2024 ยังมี optimistic bias จากวัน 8)

### วัน 10 — ประเมินผล + Risk Engine
> **ประกาศก่อนเปิดข้อมูล 2025 (pre-registration, commit ก่อนโหลด):** โค้ดประเมินคือ `src/evaluate_test.py` (`CRITERIA`) และรัน `--run` ได้**ครั้งเดียว** ถ้ามีไฟล์ผลอยู่แล้วจะไม่ยอมรันซ้ำ **หลังเห็นผลห้ามแก้โมเดล features params หรือ Q ถ้าผลไม่ดีให้รายงานตามจริง**
> - **โมเดลที่ล็อกไว้ (refit บน 2023–2024):** UVI/UVA/UVB ค่าเดียวจาก MultiOutput XGBoost (params วัน 8, weight `uvi_clear²`); ช่วงและการเตือนจาก quantile XGBoost + CQR **Q = +0.0379** (CMF) คำนวณใหม่ในขั้นนี้ด้วย CV fold 3–5 ของ 2023–2024 → `models/cqr_q_final_v1.json` (รายต่อ fold 0.038 / 0.047 / 0.027 ไม่มีแนวโน้มตามความยาวข้อมูลฝึก); เตือนด้วย **q90 หลัง CQR**
> - **Baseline บน 2025:** Open-Meteo `uv_index` ตรง ๆ, physics-only ฟ้าใส (Madronich, CMF = 1), physics × CMF คงที่ (ค่าเฉลี่ย CMF_UVI 2023–2024)
> - **ค่าเที่ยงสุริยะ:** interpolate ค่ารายชั่วโมงแบบวัน 2 (`solar_noon_values`); ค่า OMI < 0 ถือว่าไม่มีข้อมูล; ทุก estimator เทียบบนวันชุดเดียวกัน; วันฟ้าเปิด = NASA cloud < 10 % ตอนเที่ยง (แบบวัน 2)
>
> | # | ตัวชี้วัด (2025) | เกณฑ์ผ่าน |
> |---|---|---|
> | T1 | MAE รายชั่วโมงของ UVI (โมเดล) เทียบ NASA POWER | **< 1.0** (checkpoint) |
> | T1b | MAE เดียวกัน เทียบ baseline ทั้ง 3 | ต่ำกว่า baseline **ทุกตัว** |
> | T2a | MAE ตอนเที่ยงของ UVI ที่ทำนาย เทียบ **OMI UVindex (ฟ้ามีเมฆ)** | **≤ 1.5** |
> | T2b | MAE เดียวกัน เทียบกับ MAE ของ NASA POWER เทียบ OMI (วันเดียวกัน) | ≤ NASA + 0.3 |
> | T2c | MAE เดียวกัน เทียบ baseline ทั้ง 3 (เทียบ OMI) | ต่ำกว่า baseline **ทุกตัว** |
> | T3a | physics ฟ้าใส `uvi_clear` ตอนเที่ยง เทียบ **TEMIS ฟ้าใส** (ทุกวัน) | MAE **≤ 1.0** |
> | T3b | UVI ที่ทำนาย เทียบ TEMIS **เฉพาะวันฟ้าเปิด** | MAE **≤ 1.5** |
> | T3c | MAE เดียวกัน เทียบ NASA POWER เทียบ TEMIS (วันเดียวกัน) | ≤ NASA + 0.3 |
> | T4 | Pearson r: UVB โมเดล กับ OMI 305/310 nm, UVA โมเดล กับ OMI 324/380 nm (หน่วยต่างกัน จึงใช้ r) | **≥ 0.7 ทั้ง 4 คู่** |
> | T4b | r ของโมเดล เทียบ r ของ physics ฟ้าใส (คู่เดียวกัน) | ≥ physics **ทุกคู่** |
> | T5 | coverage ของช่วง [q10 − Q, q90 + Q] เทียบ NASA รายชั่วโมง | **0.75–0.85** |
> | T6a | เตือน ≥ สูงมาก ด้วย q90: recall | **≥ 0.90** |
> | T6b | เตือน ≥ สูงมาก ด้วย q90: precision | **≥ 0.50** |
> | T6c | เตือน ≥ สูงมาก ด้วย q90: false alarm rate (FP / ชม. ที่จริงต่ำกว่าสูงมาก) | **≤ 0.20** |
> | T6d | เตือนระดับรุนแรงมาก (UVI ≥ 11) ด้วย q90: recall | **≥ 0.80** (เกณฑ์เดียวกับวัน 9 ซึ่งไม่ผ่าน: CV fold 3–5 ได้ 0.62, dev 2024 ได้ 0.70 รายงานไว้เพื่อความโปร่งใส) |
>
> รายงานแยกตามแหล่ง (NASA / OMI / TEMIS) และแยกจากผล dev รวม confusion matrix และ recall ระดับสูงมาก/รุนแรงมาก (exact level) ตาม rules อ้างอิงปี 2023 (notebook 02): NASA POWER เทียบ OMI MAE 1.14 และเทียบ TEMIS วันฟ้าเปิด MAE 2.68 (bias −2.68) ดังนั้น T3b อาจไม่ผ่านเพราะ bias ของ target เอง
- [x] refit โมเดลที่เลือกบนข้อมูล 2023–2024 แล้วประเมินบน **test ปี 2025 ครั้งเดียว** (NASA POWER) รายงานแยกจากผล dev → `docs/test_2025_results.json`, `docs/test_2025_criteria.csv`, `source_code/notebooks/10_test_2025.ipynb`
  > **ผ่าน 14/15 เกณฑ์ ไม่ผ่าน T4** หลังเห็นผลไม่ได้แก้อะไร MAE รายชั่วโมงเทียบ NASA **0.479** (dev 2024 0.450; R² 0.934) ต่ำกว่า baseline ทุกตัว (CMF คงที่ 0.708, Open-Meteo 1.244, physics ฟ้าใส 2.471) UVA 2.91 W/m², UVB 0.088 W/m²; coverage ของช่วง CQR **0.806**
- [x] Confusion matrix + Recall ระดับสูง (q90 หลัง CQR)
  > เตือน ≥ สูงมาก: recall **0.986**, precision 0.564, false alarm rate 0.163; รุนแรงมาก: recall **0.826** (19/23 ชม., 95 % CI 0.63–0.93) แต่ precision 0.17; recall แบบ exact level: สูงมาก 0.848, รุนแรงมาก 0.826
- [x] **ทดสอบอิสระ:** ดึง OMI ปี 2025 (`fetch_validation --split test`, 365 วัน) แล้วเทียบค่าช่วงเที่ยงวันกับ TEMIS (UVI) และ OMI (UVI, 305/310 nm ≈ UVB, 324/380 nm ≈ UVA) **ปี 2025 เท่านั้น** รายงาน MAE แยกตามแหล่ง
  > **OMI ฟ้ามีเมฆ:** MAE **1.32** (bias −0.82, n 269) เทียบกับ NASA POWER 1.33 และ Open-Meteo 2.36 **TEMIS ฟ้าใส:** physics `uvi_clear` MAE **0.76** (ทุกวัน); โมเดลในวันฟ้าเปิด MAE 1.36 (**bias −1.36**, NASA −1.58) → โมเดลรับ bias ต่ำของ NASA มา ค่าที่สูงกว่า ~11 จึงถูกประเมินต่ำ (ข้อจำกัดสำคัญของการเตือน ต้องเขียนในรายงาน) **Irradiance (T4 ไม่ผ่าน):** r 0.65 / 0.63 (UVB–305/310 nm), 0.53 / 0.57 (UVA–324/380 nm) ต่ำกว่า 0.7 แต่สูงกว่า physics ฟ้าใสทุกคู่
- [x] `source_code/src/risk.py`: ระดับ WHO, MED, เวลาผิวไหม้, คำแนะนำ SPF/PA
  > ระดับที่แสดงมาจากค่าเดี่ยว ส่วนระดับเตือน เวลาผิวไหม้ (ปัดลง) และคำแนะนำมาจากขอบบน q90 พร้อม disclaimer ภาษาไทย → `assess()` ใช้ต่อใน `/predict` วัน 16
- [x] บันทึกโมเดลทั้งหมด → `cmf_multi_xgb_final.joblib` (13.9 MB) และ `cmf_uvi_quantile_xgb_final.ubj.gz` (21.2 MB) พร้อม `*_final_metrics.json`, และ `cqr_q_final_v1.json`

**Checkpoint วัน 10: MAE < 1.0 UVI** → ✅ **ผ่าน (test 2025: 0.479)** ตรวจซ้ำด้วย `/checkpoint` โดยโหลดโมเดลที่บันทึกไว้จากดิสก์: MAE 0.479, RMSE 0.752, R² 0.934 ตรงกับผลที่บันทึก; recall (q90) สูงมาก 0.848 / รุนแรงมาก 0.826

---

## Phase 3: ML ขั้นสูง (วัน 11–15)

### วัน 11 — LSTM: เตรียมข้อมูล
- [x] sliding window 48 ชม. → 24 ชม. → `src/sequences.py`, `dataset/processed/seq_v1_{train,dev}.npz`, `source_code/notebooks/11_lstm_data.ipynb`
  > grid รายชั่วโมงครบ (กลางวัน + กลางคืน) สร้างใหม่จากไฟล์ raw และกรองปี 2025 ออกตั้งแต่อ่าน ค่ากลางวันตรงกับ `train.parquet` ทุกค่า (7,438 แถว ต่างกัน 0.0) **Input มีเฉพาะที่หาได้ตอนใช้งานจริง:** features 23 ตัว (Open-Meteo + เวลา/ตำแหน่ง) ย้อนหลัง 48 ชม. + covariate 24 ชม. ข้างหน้าจากพยากรณ์ Open-Meteo **ไม่มี NASA POWER เป็น input** (`check_inputs()`) target = CMF_UVI t+1…t+24 (mask `uvi_clear < 0.5`); origin ทุกชั่วโมง
- [x] scale + แบ่งตามเวลา → `source_code/models/seq_spec_v1.json`
  > train = target ทั้งหมดในปี 2023 (8,540 window), dev = target ทั้งหมดในปี 2024 (8,761 window) ตัด window ที่คร่อมปีทิ้ง z-score ด้วยสถิติปี 2023 เท่านั้น **Baseline dev 2024** (`docs/lstm_baseline_dev_2024.csv`): B1 XGBoost (config วัน 10, fit 2023) + features Open-Meteo MAE **0.450** (recall ≥ สูงมาก 0.83); B2 Open-Meteo `uv_index` 1.162 ⚠️ ข้อจำกัด (แก้คำอธิบายวัน 16 ตามโค้ด `fetch_data.py` ซึ่งใช้ **Open-Meteo Historical Forecast API**): ข้อมูลฝึกเป็นช่วงต้นของแต่ละรอบพยากรณ์มาต่อกัน ไม่ใช่พยากรณ์ล่วงหน้า 24 ชม. จริง ผลจริงตอนพยากรณ์อาจแย่กว่าที่วัดได้ (ถ้าจะวัดตามระยะพยากรณ์จริงต้องใช้ Previous Runs API เป็นงานเสริม)

### วัน 12 — LSTM: ฝึกและเทียบผล
> **ประกาศเกณฑ์ในวัน 11 (ก่อนฝึก LSTM):**
> - **ตัดสินบน dev 2024 เท่านั้น** (LSTM ฝึกบน window ปี 2023 และใช้ `window_metrics()` ตัวเดียวกับ baseline บน window ชุดเดียวกัน) LSTM **ชนะ** baseline B1 (XGBoost + features Open-Meteo, MAE 0.450) ก็ต่อเมื่อ
>   1. MAE ของ UVI (ทุก lead 1–24 ชม. เฉพาะชั่วโมงกลางวัน) **ต่ำกว่า B1 เกิน 0.02 UVI** และ
>   2. recall ของการเตือน ≥ สูงมาก (ค่าเดี่ยว) **ลดลงจาก B1 ไม่เกิน 0.03**
>
>   ถ้าไม่ผ่านทั้งสองข้อ ให้รายงานตามจริงและ **ใช้ XGBoost ในแอป** (รวมพยากรณ์ 6–24 ชม.)
> - **Test 2025 ประเมินครั้งเดียว** หลังตัดสินบน dev แล้ว (LSTM refit บน 2023–2024 เทียบ XGBoost final วัน 10 บน window ปี 2025 และ guard รันครั้งเดียวแบบวัน 10) ใช้รายงานเท่านั้น ไม่เปลี่ยนการตัดสินใจ: **L1** MAE ของ LSTM < 1.0 UVI; **L2** MAE ของ LSTM ต่ำกว่า XGBoost final เกิน 0.02 UVI
- [x] ฝึก LSTM/GRU พยากรณ์ 6–24 ชม. → `src/lstm.py`, `source_code/notebooks/12_lstm.ipynb`, `models/lstm_v1_metrics.json`
  > encoder–decoder (units 64, dropout 0.2, loss = MSE ถ่วง `uvi_clear²`, `enable_op_determinism`) config คงที่ไม่ได้ tune early stopping ใช้ window ที่ target อยู่ใน **พ.ย.–ธ.ค. 2023** (ไม่ใช้ dev 2024) เลือก **LSTM** แทน GRU ด้วย validation loss ช่วงเดียวกัน (0.00426 เทียบกับ 0.00477 เฉลี่ย 3 seeds)
- [x] เทียบกับพยากรณ์ Open-Meteo และ baseline XGBoost → `docs/lstm_dev_2024.csv`, `docs/lstm_test_2025.json`
  > **dev 2024 (3 seeds): LSTM MAE 0.463 ± 0.008** เทียบกับ B1 XGBoost + Open-Meteo 0.450 และ B2 Open-Meteo `uv_index` 1.162; recall ≥ สูงมาก 0.873 (B1 0.831) **→ ไม่ผ่านเกณฑ์ (ต้อง < 0.430) ใช้ XGBoost ในแอปรวมพยากรณ์ 6–24 ชม. และไม่ปรับ LSTM ต่อ** LSTM มี bias +0.17 และแย่กว่า B1 ทุก lead **Test 2025 (ครั้งเดียว, ใช้รายงานเท่านั้น):** LSTM refit 0.497 ± 0.004 เทียบกับ XGBoost final 0.480 และ Open-Meteo 1.164 → L1 ผ่าน, L2 ไม่ผ่าน; recall รุนแรงมาก LSTM 0.06 เทียบกับ XGBoost 0.22; early stopping ตอน refit หยุดที่ epoch 5 / 1 / 1 ข้อจำกัด (แก้คำอธิบายวัน 16, ข้อมูลมาจาก Historical Forecast API): ข้อมูลฝึกเป็นช่วงต้นของแต่ละรอบพยากรณ์มาต่อกัน ไม่ใช่พยากรณ์ล่วงหน้า 24 ชม. จริง ผลจริงตอนพยากรณ์อาจแย่กว่าที่วัดได้

> **ปรับขอบเขต Phase 3 (วัน 13):** CNN เป็น**โมดูลแยก** ไม่นำไป stack กับ XGBoost เพราะไม่มีภาพท้องฟ้าของปทุมธานีที่จับคู่กับ target ของ NASA POWER ได้ CNN ทำ 2 งาน: (1) จำแนกสภาพท้องฟ้า (CCSN + SWIMCAT-ext แต่ละ dataset ใช้ label และ head ของตัวเอง) (2) ประมาณสัดส่วนเมฆ (baseline red/blue ratio ก่อน แล้วเพิ่ม head CNN เมื่อได้ SWIMSEG — ทำแล้วหลังวัน 20) วัดผลบน test split ของแต่ละ dataset แยกกัน **แอปใช้ผลเป็นข้อมูลประกอบเท่านั้น ไม่เปลี่ยนค่า UVI** ตัด stacking และ SKIPP'D/CloudCV ออก วัน 15 เป็นวันสำรอง (แก้ `.agents/rules/00-project-context.md` และ `.agents/workflows/checkpoint.md` ให้ตรงกัน)

### วัน 13 — CNN: เตรียม dataset (ไม่ใช้ภาพถ่ายเอง)
- [x] ดาวน์โหลด CCSN (CC0) และ SWIMCAT-ext (CC BY 4.0, ใช้แทน SWIMCAT) + ตรวจ license/checksum → `src/sky_data.py`, `docs/datasets.md`
  > CCSN 2,543 ภาพ 11 ชนิด (md5 ตรง), SWIMCAT-ext 2,100 ภาพ 6 คลาส × 350 (sha256 ตรง) SWIMCAT-ext ขยายมาจาก SWIMCAT (CC BY-NC) จึงถือว่าใช้เพื่อการศึกษา/ไม่ใช่เชิงพาณิชย์
- SWIMCAT / SWIMSEG (CC BY-NC 4.0) ต้องกรอกฟอร์มก่อน
  > **ย้ายไป future work (ตัดสินวัน 15) ไม่ใช่งานค้าง:** ยกเลิก head CNN สัดส่วนเมฆ และใช้ red/blue proxy แทน ถ้าได้ SWIMSEG ภายหลังค่อยทำ (ดู "ส่วนเสริม" ท้ายไฟล์; `index_swimseg()` มีพร้อมแล้ว) (อัปเดตหลังวัน 20: ทำแล้ว ได้ SWIMSEG และฝึก head สัดส่วนเมฆ ผ่านเกณฑ์ C1/C2 MAE 0.084 เทียบกับ red/blue 0.145 ดู ROADMAP "ส่วนเสริม")
- [x] index + ตรวจภาพซ้ำ + แบ่ง train/val/test ของแต่ละ dataset (70/15/15, stratified, ภาพซ้ำอยู่ split เดียวกัน) → `docs/sky_splits/*.csv`, `source_code/notebooks/13_sky_data.ipynb`
  > CCSN 1,785 / 383 / 375, SWIMCAT-ext 1,472 / 317 / 311, 0 กลุ่มซ้ำที่คร่อม split **เปลี่ยนจาก dHash เป็นเทียบ thumbnail 16×16 ที่หมุน/พลิกได้ 8 แบบ (MAD < 0.03)** เพราะ dHash โยงภาพที่ texture น้อยเป็นกลุ่มผิด ๆ ~50 ภาพ และจับภาพที่หมุนไม่ได้ **พบ CCSN 263 ภาพ (124 กลุ่ม) เป็นรูปเดียวกันแต่อยู่คนละชนิดเมฆ** (label noise ใน dataset) ติด flag `label_conflict` ไว้ → **เสนอให้ตัดทิ้งจากทุก split ก่อนฝึกในวัน 14**; SWIMCAT-ext มี 1,470 ภาพอยู่ในกลุ่มซ้ำ
- [x] preprocessing (crop กลาง + resize 224) + augmentation (flip, หมุน ±15°, perspective, ความสว่าง, contrast, white balance, saturation, blur) ลด domain gap จากภาพกล้องท้องฟ้าสู่ภาพมือถือ → `load_image()`, `augmenter()`, `docs/figures/sky_*.png`
  > test split อ่านได้เฉพาะเมื่อส่ง `load_split(..., confirm_test=True)`; domain gap จดไว้ใน `docs/datasets.md`

### วัน 14 — CNN: Transfer Learning (โมดูลแยก)
> **ประกาศก่อนเปิด test split (commit ก่อนฝึกและก่อนอ่าน test)** โค้ดคือ `src/sky_cnn.py` (`CRITERIA`, `judge()`) และ `--test` รันได้ครั้งเดียว (guard) **หลังเห็นผลห้ามแก้โมเดล ข้อมูล หรือ config ถ้าไม่ผ่านให้รายงานตามจริง**
> - **Input contract:** ภาพ float RGB **[0, 1]** (`load_image` / `augmenter`) ภายในโมเดลมี `Rescaling(255)` ก่อนเข้า MobileNetV3Small (`include_preprocessing=True` ซึ่งรับ 0–255) และมี `check_unit_range()` กันไม่ให้ scale ซ้ำ พร้อม test ตรวจว่า backbone ได้ค่า 0–255 และหลัง preprocessing ได้ [−1, 1]
> - **โมเดล:** MobileNetV3Small (ImageNet) backbone ร่วม + head CCSN 11 คลาส และ SWIMCAT-ext 6 คลาส (loss ของ dataset อื่นมีน้ำหนัก 0) ฝึก 2 ขั้น: freeze backbone lr 1e-3 ≤ 15 epochs แล้ว unfreeze 30 % บน (BatchNorm ยัง freeze) lr 1e-4 ≤ 30 epochs, early stopping บน **val** (patience 5), augmentation วัน 13, **3 seeds** (42/43/44) รายงาน mean ± SD, โมเดลที่ export (TFLite float16) เลือกจาก val loss
> - **ข้อมูล:** ตัดกลุ่ม `label_conflict` ของ CCSN ออกจาก train, val และ test หลัก และรายงาน test แบบรวมกลุ่มนี้ไว้เทียบ (ไม่มีเกณฑ์)
> - **CCSN 4 กลุ่ม UV** (สิ่งที่แอปจะแสดง): เมฆบางระดับสูง Ci/Cs/Cc/Ct, เมฆระดับกลาง Ac/As, เมฆหนาระดับต่ำ St/Sc/Ns/Cb, เมฆก้อน Cu ความน่าจะเป็นของกลุ่ม = ผลรวมของชนิดในกลุ่ม
> - **SWIMCAT-ext:** รายงานจำนวนภาพและจำนวนกลุ่มภาพไม่ซ้ำ + accuracy รายกลุ่ม (เฉลี่ยความน่าจะเป็นในกลุ่ม 1 กลุ่ม = 1 คะแนน)
> - **Baseline อ้างอิง:** logistic regression บนสถิติสี (RGB/HSV/NRBR) **สัดส่วนเมฆ:** red/blue ratio `NRBR = (B−R)/(B+R) < 0.25` (ค่าจากงานวิจัย ไม่ได้ปรับ) ยังไม่มี SWIMSEG จึงตรวจแบบ proxy กับคลาสของ SWIMCAT-ext เท่านั้น (อัปเดตหลังวัน 20: ทำแล้ว ได้ SWIMSEG และฝึก head สัดส่วนเมฆ ผ่านเกณฑ์ C1/C2 MAE 0.084 เทียบกับ red/blue 0.145 ดู ROADMAP "ส่วนเสริม")
>
> | # | ตัวชี้วัด (test, ค่าเฉลี่ย 3 seeds) | เกณฑ์ผ่าน |
> |---|---|---|
> | K1 | CCSN 11 คลาส (ตัด conflict) accuracy | **≥ 0.60** |
> | K2 | CCSN 11 คลาส macro-F1 | **≥ 0.55** |
> | K3 | CCSN 4 กลุ่ม UV accuracy | **≥ 0.75** |
> | K4 | CCSN กลุ่ม UV: recall ของ "เมฆบางระดับสูง" | **≥ 0.70** |
> | K5 | CCSN 11 คลาส accuracy − baseline สี | **≥ 0.10** |
> | S1 | SWIMCAT-ext accuracy รายภาพ | **≥ 0.85** |
> | S2 | SWIMCAT-ext accuracy รายกลุ่มภาพไม่ซ้ำ | **≥ 0.80** |
> | S3 | SWIMCAT-ext accuracy รายกลุ่ม − baseline สี | **≥ 0.05** |
> | R1 | red/blue proxy: median สัดส่วนเมฆของ clear_sky | **< 0.20** |
> | R2 | red/blue proxy: median ของ thick_white, thick_dark, veil | **> 0.60 ทุกคลาส** |
- [x] MobileNetV3 backbone ร่วม + head จำแนกแยกตาม dataset (CCSN 11 คลาส, SWIMCAT-ext 6 คลาส) ใช้ train/val เท่านั้น → `src/sky_cnn.py`, `models/sky_cnn_v1_metrics.json`, `docs/sky_cnn_val.csv`
  > ครบ 3 seeds: val loss 0.763 / 0.751 / 0.759, CCSN acc 0.521 / 0.518 / 0.516, กลุ่ม UV 0.717 / 0.708 / 0.703, SWIMCAT-ext 0.991 / 0.984 / 0.987; baseline สี (val) CCSN 0.31, SWIMCAT-ext รายกลุ่ม 0.80 export seed 43 (val loss ต่ำสุด) → `models/sky_cnn_v1.tflite` (float16, 1.96 MB) + `sky_cnn_v1_labels.json`; seed 44 ฝึกใหม่ใน process แยก (27 ก.ย. 02:19–02:51, stage2 หยุดที่ epoch 11) ส่วน seed 42/43 โหลดจากไฟล์
  > ประวัติ: seed 42 (val loss 0.763, CCSN acc 0.521, UV-group 0.717, SWIMCAT-ext 0.991) และ seed 43 (0.751, 0.518, 0.708, 0.984) บันทึกไว้เท่านั้น **ไม่ได้ปรับโมเดลตามผล val** seed 44 หยุดเพราะ**เครื่อง sleep** (26 ก.ย. 16:08) แล้ว python.exe crash `0xC0000409` (ucrtbase.dll) ประมาณ 1 นาทีหลังตื่น (27 ก.ย. 01:12) ไม่มี Traceback และไม่ใช่ OOM (ภาพเก็บเป็น uint8 ใช้ RAM ราว 3–4 GB จาก 30 GB และไม่มีเหตุการณ์หน่วยความจำต่ำ) แก้เฉพาะการรัน: `resume_or_train()` โหลด seed ที่มีโมเดลแล้วแทนการฝึกใหม่ และ log ทุก epoch ลง `dataset/processed/logs/sky_cnn_seed<N>.log` สถาปัตยกรรม, stage, hyperparameter, split, seed และเกณฑ์ไม่เปลี่ยน history ราย epoch ของ seed 42/43 หายไปกับ process ที่ crash **ห้ามรัน `--test` จนกว่าจะครบ 3 seeds**
- [x] baseline สัดส่วนเมฆด้วย red/blue ratio (+ head CNN จาก SWIMSEG ถ้าได้ข้อมูลแล้ว) → `rb_cloud_fraction()`, `docs/figures/sky_rb_cloud_fraction.png`
  > head CNN สัดส่วนเมฆ**ย้ายไป future work (ตัดสินวัน 15)** (อัปเดตหลังวัน 20: ทำแล้ว ได้ SWIMSEG และฝึก head สัดส่วนเมฆ ผ่านเกณฑ์ C1/C2 MAE 0.084 เทียบกับ red/blue 0.145 ดู ROADMAP "ส่วนเสริม") แอปใช้ red/blue proxy ซึ่งตรวจบน SWIMCAT-ext test ได้: median clear_sky 0.001, thin_white 0.42, patterned 0.69, thick_white 0.66, thick_dark 0.97, veil 1.00
- [x] ประกาศเกณฑ์ก่อน (commit `12c1828`) แล้วประเมินบน test split ของแต่ละ dataset ครั้งเดียว + export ให้ `/sky-image` → `docs/sky_cnn_test.json`, `source_code/notebooks/14_sky_cnn.ipynb`
  > **ผ่าน 7 / 10 ไม่ผ่าน K1, K2, K3** (ค่าเฉลี่ย 3 seeds, หลังเห็นผลไม่ได้แก้อะไร) **CCSN** (ตัด conflict, 326 ภาพ): 11 คลาส accuracy **0.486 ± 0.010 ❌** (≥ 0.60), macro-F1 **0.452 ± 0.023 ❌** (≥ 0.55), 4 กลุ่ม UV **0.685 ± 0.009 ❌** (≥ 0.75), recall เมฆบางระดับสูง 0.707 ✅ (≥ 0.70, เฉียดฉิว), เหนือ baseline สี +0.243 ✅; recall เมฆระดับกลาง 0.37 และเมฆก้อน 0.41 ต่ำ; แบบรวม conflict (375 ภาพ) 0.462 / 0.438 / 0.692 **SWIMCAT-ext** (311 ภาพ = 181 กลุ่มภาพไม่ซ้ำ): รายภาพ 0.975 ± 0.007 ✅, รายกลุ่ม 0.967 ± 0.010 ✅, เหนือ baseline สี +0.149 ✅ **red/blue proxy:** R1 0.001 ✅, R2 ต่ำสุด 0.656 (thick_white) ✅ → จำแนกสภาพท้องฟ้าใช้ได้ แต่จำแนกชนิดเมฆ/กลุ่ม UV ไม่ถึงเกณฑ์ ในแอปต้องแสดงผลกลุ่มเมฆพร้อมความไม่แน่นอน หรือแสดงเฉพาะสภาพท้องฟ้า (ตัดสินวัน 16–20) หมายเหตุ: `tf.lite.Interpreter` ถูกประกาศเลิกใช้ ให้ย้ายไป `ai_edge_litert` ตอนทำ API
  > **TFLite float16 (seed 43) เทียบกับ .keras** ตรวจบน **val** (ไม่อ่าน test ซ้ำ, notebook 14 ข้อ 5): คลาสตรงกัน 99.3 % (CCSN) / 99.4 % (SWIMCAT-ext) / 99.7 % (กลุ่ม UV) ความน่าจะเป็นต่างกันสูงสุด 0.057 ตัวชี้วัด val เท่ากัน (macro-F1 0.4796 → 0.4794)
  > **ข้อจำกัด (ต้องเขียนในรายงาน):** (1) history ราย epoch ของ seed 42/43 หาย มี learning curve แค่ seed 44 (2) CCSN มี label ขัดกัน 263 ภาพ (124 กลุ่ม) ถูกตัดออก ข้อมูลน้อยลงและ label ที่เหลืออาจมี noise อีก (3) domain gap: ตามคำอธิบายบน Mendeley (doi:10.17632/vwdd9grvdp.1) ภาพ SWIMCAT-ext ทั้งหมด "collected from Internet and labelled by technical expert" (ไม่ใช่ภาพ fisheye จากกล้องท้องฟ้าตามที่เขียนไว้ก่อนหน้า แก้วัน 15) ส่วน CCSN เป็นภาพจากกล้องธรรมดา ทั้งสองชุดไม่ใช่ภาพจากมือถือที่ปทุมธานี และยังไม่ได้วัดผลบนภาพมือถือ (4) SWIMCAT-ext ขยายจาก SWIMCAT (CC BY-NC) และภาพมาจากอินเทอร์เน็ตซึ่งไม่ทราบสิทธิ์ของภาพต้นฉบับ จึงใช้เพื่อการศึกษาเท่านั้น ไม่ใช่เชิงพาณิชย์

### วัน 15 — วันสำรอง
> ห้ามฝึกโมเดลใหม่และห้ามรัน `--test` ใหม่ในวันนี้ head CNN สัดส่วนเมฆ (SWIMSEG) ย้ายไป future work และใช้ red/blue proxy แทน (อัปเดตหลังวัน 20: ทำแล้ว ได้ SWIMSEG และฝึก head สัดส่วนเมฆ ผ่านเกณฑ์ C1/C2 MAE 0.084 เทียบกับ red/blue 0.145 ดู ROADMAP "ส่วนเสริม")
- [x] ตรวจ commit `2f260a3` (TFLite float16 บน val) → มาจาก session ก่อนหน้าของ Claude Code (author Folktom04 + `Co-Authored-By: Claude Opus 5.5` เหมือนทุก commit) ตัวเลขตรงกับไฟล์ผล (val macro-F1 ของ seed 43 = 0.4796 ตรงกับ `sky_cnn_v1_metrics.json`) และอ่านเฉพาะ val ไม่ได้อ่าน test ซ้ำ
- [x] แก้แหล่งที่มาของ SWIMCAT-ext ตามคำอธิบายบน Mendeley (doi:10.17632/vwdd9grvdp.1, ยืนยันทั้งจากหน้าเว็บและ public API): "an extension of SWIMCAT dataset … All images were collected from Internet and labelled by technical expert." ในไฟล์ไม่มีเอกสารแนบ และไม่ได้บอกว่ารวมภาพ SWIMCAT ต้นฉบับหรือไม่ → แก้ ROADMAP, `docs/datasets.md`, `src/sky_data.py` และ rules ที่เคยเขียนว่าเป็น fisheye/sky-camera
- [x] ตรวจภาพซ้ำข้าม dataset (CCSN × SWIMCAT-ext ทุก split, วิธีเดียวกับวัน 13) → `cross_duplicates()`, `python -m src.sky_cnn --crosscheck`, `docs/sky_crossdataset_duplicates.csv`, `docs/sky_cnn_crosscheck.json`
  > กฎวัน 13 จับได้ **11 คู่**: CCSN-train/SWIM-test 1, train/train 7, train/val 2, val/val 1 **แต่เมื่อดูภาพจริงไม่มีคู่ไหนเป็นภาพเดียวกัน** (เป็นภาพ texture น้อยที่หน้าตาคล้ายกัน เช่น ฟ้าสีฟ้าที่มีเส้น contrail กับฟ้าเปล่า หรือ Ac/As/Cc กับ veil สีเทา) ข้อจำกัดคือกฎ thumbnail 16×16 มี false positive กับภาพเรียบ ๆ ผลประกอบ (โมเดลเดิม ไม่ได้ฝึกใหม่) เมื่อตัดภาพ test 1 ภาพที่ถูกจับ (SWIMCAT-ext `F_img51.png`, veil) ออก: รายภาพ 0.975 → 0.975, รายกลุ่ม 0.967 → 0.967 (310 ภาพ / 180 กลุ่ม) ส่วน CCSN ไม่มีภาพถูกตัด **ผลหลักใน `sky_cnn_test.json` ไม่เปลี่ยน**
- [x] ใส่ cell id ให้ notebook (nbformat) → มีแค่ notebook 14 ที่ขาด (3 cell ที่เพิ่มใน `2f260a3`) เพิ่ม id อย่างเดียว เนื้อหา/ผลไม่เปลี่ยน และไม่ได้รันใหม่ ส่วน notebook 01–13 มี id อยู่แล้ว
- [x] สรุปผลวัน 1–14 สำหรับรายงาน → `docs/results_summary.md` (ทุกตัวเลขมีไฟล์ต้นทางกำกับ, ตารางเกณฑ์ที่ประกาศก่อนเทียบผ่าน/ไม่ผ่าน, หัวข้อข้อจำกัด)

**Checkpoint วัน 15: ผล LSTM ตัดสินแล้ว (ใช้ XGBoost) + CNN ทำงานบน test split ของแต่ละ dataset** → ✅ ตรวจแล้ว: `lstm_v1_metrics.json` บันทึกว่า `rnn_wins: false`, `app_model: XGBoost` และโหลด sky CNN 3 seeds จากดิสก์มาคำนวณ test ซ้ำได้**ตรงกับ `sky_cnn_test.json` ทุกค่า** (`checkpoint_full_test_reproduced` ใน `docs/sky_cnn_crosscheck.json`) CNN ทำงานและประเมินแล้ว แต่ผลยังเป็นตามที่รายงานไว้ (ผ่าน 7/10, CCSN K1–K3 ไม่ผ่าน)

---

## Phase 4: Backend + แอป (วัน 16–21)

### วัน 16 — FastAPI endpoints
- [x] `/predict`, `/forecast`, `/sky-image`, `/health` → `source_code/api/main.py`, `api/schemas.py`, `src/inference.py`, `src/sky_infer.py`, `docs/api.md`
  > input ใช้ Open-Meteo Forecast + Air Quality เท่านั้น (**ไม่เรียก NASA POWER**) ตัวแปรชุดเดียวกับตอนฝึกและไม่ใส่ `models=` ตรวจแล้วว่า Historical Forecast API (ตอนฝึก) กับ Forecast API (ตอนใช้งาน) ให้ค่าตรงกันทุกค่า (16/16 ตัวแปร, 72/72 ชม.) และ `build_features()` ให้ features ตรงกับ `train.parquet` ทั้ง 23 ตัว (7,394 แถว, ต่างกันสูงสุด 0, tolerance 1e-6) ค่าเดี่ยวไม่ถูก clip ถ้าออกนอก q10–q90 จะขยายช่วงที่แสดงพร้อม `interval_adjusted: true` (บน dev 2024 เกิด 0/3,726 ชม.) ส่วน**การเตือน, เวลาผิวไหม้ และคำแนะนำใช้ q90 หลัง CQR เสมอ** (`risk.assess(alert_uvi=...)`) `/sky-image` ประมวลผลในหน่วยความจำ ไม่บันทึกภาพ ผลเป็นข้อมูลประกอบ ไม่ปรับค่า UVI และบอก reliability ตรง ๆ ทุก response รวมถึง error มี disclaimer TFLite ใช้ `ai-edge-litert==2.2.0` และ fallback เป็น `tf.lite` smoke test จริงที่ปทุมธานี (27 ก.ย. ~13:10): UVI 5.49 [4.94, 6.66] ระดับปานกลาง (เตือนระดับสูงจาก q90) ส่วน Open-Meteo `uv_index` ชั่วโมงเดียวกันได้ 2.95 (ท้องฟ้าเมฆ 100 %)
  > **แก้เพิ่ม (ก่อนเริ่มวัน 17):** (A) การเตือน, เวลาผิวไหม้, คำแนะนำ และ `next_safe_time` ใช้ `alert_uvi = max(q90 หลัง CQR, ค่าเดี่ยว)` เพื่อไม่ให้เตือนต่ำกว่าค่าที่แสดง (`test_point_above_q90_alert_uses_point_not_q90`, `test_alert_uvi_is_max_of_q90_and_point`) (B) ข้อมูลหายตอนใช้งานจริง: เดิม `clean()` ตัดชั่วโมงที่ข้อมูลไม่ครบทิ้งโดยไม่แจ้ง และถ้าชั่วโมงปัจจุบันหายไป `current_index()` จะหยิบชั่วโมงถัดไปมาแทน ตอนนี้ใส่ชั่วโมงที่หายกลับเข้ามา, interpolate ได้ไม่เกิน 3 ชม. (เหมือนตอนฝึก), เติมช่วงหัว/ท้ายจากชั่วโมงใกล้สุดได้ไม่เกิน 3 ชม., ติดธง `data_imputed`, ชั่วโมงที่ยังไม่ครบจะถูกตัดพร้อม log และถ้าชั่วโมงปัจจุบันไม่มีข้อมูลจะตอบ **503** เปลี่ยน air quality เป็น left join (`test_build_features_missing_data_filled_flagged_or_dropped`, `test_current_index_strict_when_current_hour_missing`, `test_missing_live_data_flagged_or_503`, `test_fetch_live_keeps_hours_missing_air_quality`) (10) เพิ่มเทส fallback ไป `tf.lite` (`test_make_interpreter_falls_back_to_tf_lite`) ส่วนข้อ 6–8 มีเทสอยู่แล้ว (`test_sky_image_result_and_nothing_stored`, `test_errors_carry_disclaimer`, `test_sky_image_never_changes_uvi`) ข้อ 9 บันทึกใน `docs/api.md` ทดสอบจริงซ้ำ 27 ก.ย. 16:00: 200, `alert_uvi` 1.01, `data_imputed` false

### วัน 17 — PostgreSQL schema
- [x] users, push_tokens, measurements, notifications_log → `source_code/src/db.py`, `docs/db.md`
  > เวลาทุกคอลัมน์เป็น `DateTime(timezone=True)` (`UTCDateTime`: ไม่รับ naive, อ่านกลับเป็น UTC-aware ทั้ง PostgreSQL และ SQLite) `users.alert_burn_minutes` (ค่าเริ่มต้น 30), `measurements.sky_confidence` / `interval_adjusted` / `data_imputed` ความเป็นส่วนตัว: ไม่มีชื่อ/อีเมล/ภาพ, พิกัดปัดเหลือ 0.01° (~1 กม.), ลบ user แล้ว push_tokens, notifications_log และ **measurements ถูกลบด้วย CASCADE** (ไม่ใช้ SET NULL เพราะชุดเวลา+ตำแหน่งยังระบุตัวคนได้ ดูเหตุผลใน `docs/db.md`) `purge_old_rows(days=90)` ลบ measurements (ยกเว้น `source='field'`) และ notifications_log ที่เก่ากว่า 90 วัน SQLite ใช้เป็น fallback เมื่อไม่ได้ตั้ง `DATABASE_URL` เท่านั้น (log WARNING) และ `/health` บอก `db_backend`, `db_fallback`, `db_ok` ส่วนเรื่อง PDPA (เก็บอะไร/ไม่เก็บอะไร/เก็บนานเท่าไร/ลบยังไง) อยู่ใน `docs/db.md`
- [x] SQLAlchemy models + migration → Alembic `alembic.ini`, `source_code/migrations/versions/0001_initial_schema.py`, `source_code/tests/test_db.py`
  > migration ไม่ import `src.db` เทสตรวจว่า migration ตรงกับ models (`compare_metadata` ไม่มี diff), upgrade/downgrade ได้ และ DDL ของ PostgreSQL แบบ offline มี `TIMESTAMP WITH TIME ZONE` 7 คอลัมน์, CASCADE 3, SET NULL 1 ผล pytest ทั้งหมด 199 passed, 22 skipped (ทั้ง 22 ข้อคือ PostgreSQL) บน SQLite ผ่านครบ
  > ~~ค้าง: ยังไม่ได้รันกับ PostgreSQL จริง~~ แก้แล้ว
- [x] ทดสอบบน PostgreSQL 18 จริงแล้ว (18.6, 27 ก.ย. 2026)
  > `alembic upgrade head` กับ `DATABASE_URL` → `0001 (head)` ตาราง users, push_tokens, measurements, notifications_log, alembic_version ครบ คอลัมน์เวลา 7 คอลัมน์เป็น `timestamptz` ทั้งหมด `pytest -q` ทั้งชุด **221 passed, 0 skipped** (เทส `[postgresql]` 23 ข้อผ่านหมด ไม่มีข้อที่ skip) ผลบน PostgreSQL ไม่ต่างจาก SQLite จึงไม่ต้องแก้โค้ด tests อ่าน `TEST_DATABASE_URL` จาก `.env` ผ่าน `load_dotenv` และไม่ log ค่า URL

### วัน 18 — Expo: หน้าหลัก
> **แก้ก่อนเริ่มวัน 18 (ตรวจทั้งโปรเจกต์):** (1) `/sky-image` ตอบ **SWIMCAT-ext 6 คลาสเป็นผลหลัก** (`sky_class`, `sky_class_th`, `sky_confidence`, `sky_class_probs`) + `cloud_fraction_rb` และเลิกส่ง `genus` / `cloud_group` ของ CCSN (ไม่ผ่านเกณฑ์ K1–K3) ใช้ TFLite ตัวเดิม ไม่ได้ฝึกใหม่ ผลดิบของทั้งสอง head ยังเรียกได้ด้วย `predict_heads()` (2) เอกสาร: README (สถาปัตยกรรมไม่มี stacking, ground truth คือ NASA POWER RE, disclaimer ครอบคลุมทุกค่า, วิธีติดตั้ง/รัน), rules (Python 3.12, Historical Forecast API, `/sky-image`), `checkpoint.md` (ห้ามรัน `--test` ซ้ำ), `START_HERE.md` (prompt วัน 13), `docs/api.md` (3) docstring ครบทุกฟังก์ชันใน `src/` และเพิ่มเทสตรง 8 ข้อ (`request_params`, `hour_start_local`, `mask_implausible`, `assert_no_test_rows`, `load_ozone_climatology`, `add_clear_sky`, `fetch_temis`, `nrbr_map`) ผล pytest **229 passed, 0 skipped** ไม่มีตัวเลขผลใดเปลี่ยน
- [x] สร้างโปรเจกต์ Expo + Expo Router → `source_code/app/` (Expo SDK 57, React Native 0.86, TypeScript, `src/app/_layout.tsx`, `src/app/index.tsx`, `src/api/`, `src/config.ts`, `README.md`)
  > template `default` ตัดหน้าตัวอย่างออก และลบ `CLAUDE.md` / `AGENTS.md` / `.claude` / `.vscode` ที่ template สร้างมา (กันกฎชนกับ `.agents/rules/`) หน้าหลักเรียก `POST /predict` ที่ปทุมธานี ผิวประเภท III (ค่าเริ่มต้นชั่วคราว: แบบสอบถามผิววัน 19, GPS/จังหวัดวัน 21) มีสถานะโหลด / error ภาษาไทย (502, 503, 422, เครือข่าย, timeout) / ลากลงเพื่อโหลดใหม่ และ disclaimer ท้ายหน้าเสมอ API เพิ่ม CORS (`CORS_ORIGINS`, ค่าเริ่มต้น Expo web `localhost:8081`) + เทส 2 ข้อ ตรวจกับ API จริง: preflight ได้ header, origin อื่นไม่ได้, key ของ response จริงตรงกับ `types.ts` ครบ (ไม่ขาดไม่เกิน)
- [x] การ์ด UV + ระดับสี → `src/components/UVCard.tsx`, `src/lib/uv.ts`
  > UVI ตัวใหญ่, ช่วง q10–q90, ป้ายระดับไทยสี WHO (ตัวอักษรเข้มบนสีเหลือง), แถบ "เตือนตามค่าบน (q90)" เมื่อ `alert_level` สูงกว่า `level`, เวลาที่ UV กลับสู่ระดับต่ำ, ป้าย `data_imputed` / `interval_adjusted` / `note` การ map ระดับใช้กฎเดียวกับ `who_level()` (ปัด x.5 ขึ้น)
- [x] การ์ด UVA / UVB + เวลาผิวไหม้ → `src/components/UvaUvbCard.tsx`
  > UVA/UVB เป็น W/m², เวลาก่อนผิวไหม้จาก `burn_minutes` ของ API (คิดจาก `alert_uvi` = ค่าบน), กลางคืนแสดง "ไม่มีความเสี่ยง (กลางคืน)", คำแนะนำ SPF/PA จาก `advice`
  > ทดสอบ: Jest 40 passed (`__tests__/uv`, `client`, `cards`, `home`), `tsc --noEmit` ผ่าน, `expo lint` ผ่าน, `expo export --platform web` build ผ่าน, pytest **231 passed, 0 skipped** (`test_sky_image_result_and_nothing_stored` เคย fail เป็นบางครั้ง เพราะโปรแกรมอื่นเขียนไฟล์ลงโฟลเดอร์ Temp ระหว่างที่เทสไล่ดูไฟล์ ซึ่งช้าลงหลังมี `app/node_modules` ตอนนี้โฟลเดอร์โปรเจกต์ยังต้องไม่มีไฟล์ใหม่เลย ส่วนใน Temp นับเฉพาะไฟล์ภาพหรือไฟล์ที่มีข้อมูลที่อัปโหลด และข้าม `node_modules` ทดลองให้ endpoint แอบเขียนไฟล์แล้ว เทสยังจับได้)
- [x] ทดสอบบนมือถือจริง (Samsung, Android, Expo Go, 28 ก.ย. 2026)
  > หน้าหลักแสดง UVI, ช่วง q10–q90, UVA/UVB, เวลาผิวไหม้ และ disclaimer ถูกต้อง ครั้งแรกขึ้น "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้" ทั้งที่ Chrome บนมือถือเปิด `/health` ได้ สาเหตุคือ Expo Go แคช bundle เก่า แก้ด้วย Force stop + Clear cache ตรวจแล้วว่าโค้ดอ่าน URL ถูก (Metro ใส่ `EXPO_PUBLIC_API_URL` ลงใน dev bundle จริง) ผลจากการดีบัก: หน้าจอ error แสดง "ที่อยู่ที่เรียก" และ "รายละเอียด" (ข้อความ error ดิบ) ขั้นตอนทดสอบบนมือถือและวิธีแก้ bundle เก่าอยู่ใน `source_code/app/README.md` timeout 20 วินาที (วัด `/predict` ครั้งแรกได้ ~2 วินาที ส่วนเรื่อง retry ฝั่ง API ไว้คุยวัน 19) root `.gitignore` เพิ่ม `.env*.local`
  > กลางคืน (`is_daylight` false): API ยังส่งคำแนะนำระดับ "ต่ำ" ซึ่งมี "…ควรใส่แว่นกันแดด" แอปจึงซ่อนคำแนะนำ แล้วแสดง UV สูงสุดของช่วงกลางวันถัดไปจาก `/forecast?hours=36` แทน (`nextDaytimePeak()`, "พรุ่งนี้" หรือ "วันนี้" หลังเที่ยงคืน, พร้อมช่วง q10–q90) ถ้า `/forecast` ล้มเหลว หน้าจอยังใช้ได้และขึ้น "ยังไม่มีข้อมูลพยากรณ์ของวันถัดไป" ตรวจกับ API จริงตอน 03:00: ได้ "วันนี้" สูงสุด 7.35 (สูง) ราว 12:00 ช่วง 6.03–8.71 Jest **51 passed**
  > ~~ค้าง: ตรวจหน้าจอบนเว็บด้วย browser agent ของ Antigravity ตามรายการใน `source_code/app/README.md` (ยังไม่ได้รับผล)~~ **แทนด้วยการทดสอบบนมือถือจริง (Samsung, Expo Go) + Jest** (ตัดสิน 29 ก.ย. 2026)

### วัน 19 — Expo: กราฟ + ตั้งค่า
- [x] กราฟพยากรณ์รายชั่วโมง → `src/components/HourlyChart.tsx`, `src/lib/chart.ts`
  > ชั่วโมงปัจจุบัน + 24 ชม. จาก `/predict` แท่งสีระดับ WHO (กว้าง 14 px ไม่ชนกัน, มุมบนโค้ง 4 px), เส้นช่วง q10–q90 สีเทาเข้ม, เส้นอ้างอิงบาง ๆ ที่ UVI 3/6/8/11, แกนสูงอย่างน้อย 12 (วันที่ UV ต่ำจะได้ไม่ดูน่ากลัวเกินจริง), ตัวเลขเฉพาะชั่วโมงสูงสุด, แตะแท่งเพื่อดูรายละเอียด (มือถือไม่มี hover), ทุกแท่งมี `accessibilityLabel`, มีคำอธิบายสี 5 ระดับ และบรรทัดสรุปค่าสูงสุด ไม่ได้ลงไลบรารีกราฟ
- [x] แบบสอบถามประเภทผิว 5 ข้อ → `src/app/quiz.tsx`, `src/lib/skinQuiz.ts`, `docs/skin_quiz.md`
  > **แบบย่อดัดแปลงจาก Fitzpatrick ยังไม่ผ่านการตรวจสอบทางวิชาการ** (เขียนไว้ทั้งในหน้าผลและ docs) ตัดข้อสีตาและสีผมออก เพราะคนไทยเกือบทั้งหมดตอบเหมือนกัน เหลือ 5 ข้อ ข้อละ 0–4 คะแนน รวม 0–20 จุดตัดคือจุดตัดของแบบเต็ม 40 คะแนนหารสอง ได้ I 0–3 · II 4–7 · III 8–10 · IV 11–14 · V 15–17 · VI 18–20 **คะแนนที่ตกขอบพอดี (7, 14) ปัดไปประเภทที่อ่อนกว่า** ซึ่งเตือนเร็วกว่า จึงปลอดภัยกว่า เทสตรวจทุกขอบช่วง และตรวจว่าไม่มีคะแนนไหนได้ประเภทเข้มกว่าแบบเต็มที่คะแนน ×2 เลือกประเภทเองได้ ระหว่างที่ยังไม่ระบุ หน้าหลักใช้ III และมีปุ่มชวนทำแบบสอบถาม
- [x] หน้าตั้งค่าการแจ้งเตือน → `src/app/settings.tsx`, `src/lib/settings.ts`, `src/lib/SettingsContext.tsx`; API `POST /users`, `PUT /users/{id}/settings`, `DELETE /users/{id}` (`src/users.py`, `api/main.py`)
  > ระดับเตือน 6 / 8 / 11 โดย **safe_threshold = alert − 2** (6→4, 8→6, 11→9, เซิร์ฟเวอร์เป็นคนคำนวณ ถ้า client ส่ง `safe_threshold` มาได้ 422), เตือนก่อนผิวไหม้ 15/30/60 นาที, สรุป 07:00 และเตือนทาครีมซ้ำ (บันทึกไว้ให้วัน 22) เก็บการตั้งค่าใน AsyncStorage **จะส่งไปเซิร์ฟเวอร์ต่อเมื่อผู้ใช้เปิดสวิตช์ยินยอมเอง (ปิดเป็นค่าเริ่มต้น เพราะประเภทผิวเป็นข้อมูลสุขภาพตาม PDPA ม.26)** ปิดสวิตช์ = ถอนความยินยอม ซึ่งจะลบข้อมูลบนเซิร์ฟเวอร์ด้วย ปุ่ม "ลบข้อมูลของฉัน" มีหน้ายืนยัน ลบบนเซิร์ฟเวอร์ก่อนแล้วค่อยล้างในเครื่อง (ถ้าติดต่อเซิร์ฟเวอร์ไม่ได้ ข้อมูลในเครื่องยังอยู่เพื่อให้กดลองใหม่ได้)
  > API: user คือ device id แบบสุ่ม (UUID ที่แอปสร้าง) ส่งใน `X-Device-Id` ถ้าไม่ตรงได้ 403, ไม่มี user ได้ 404, header ผิดรูปแบบได้ 400, `POST` ซ้ำด้วย device เดิมได้ 200 (idempotent) และ `DELETE` ลบทุกอย่างที่ผูกกับ user ด้วย CASCADE **ไม่ log และไม่ส่ง device id กลับ:** engine ตั้ง `hide_parameters=True` แต่เทสบน PostgreSQL เจอว่าข้อความ error ของ PG เองยังมีค่าอยู่ (`DETAIL: Key (device_id)=(…)`) จึงให้ `IntegrityError` ตอบ **409** และ DB error อื่นตอบ **503** โดยไม่ส่งข้อความของ DB กลับ และ log แค่ชื่อคลาส วิธีลด DETAIL ใน log ของ PostgreSQL server (`log_error_verbosity = terse`) อยู่ใน `docs/db.md`
  > **retry ที่ค้างจากวัน 18:** ตอนดึงข้อมูลสดใช้ `get_live()` แทน session ของตอนฝึก retry 2 ครั้ง (0.5 วินาที แล้ว 1 วินาที) timeout 5 วินาทีต่อครั้ง และสองคำขอใช้งบรวมกัน 15 วินาที จึงตอบหรือได้ 502 ก่อนแอปตัดที่ 20 วินาที (ของเดิมคือ 5 retry, backoff 2 วินาที, timeout 30 วินาที อาจนานเกิน 1 นาที) สคริปต์ดึงข้อมูลตอนฝึกยังใช้ค่าเดิม
  > ทดสอบ: Jest **109 passed** (9 suites), `tsc` / `expo lint` / `expo export --platform web` ผ่าน pytest **281 passed, 0 skipped** (PostgreSQL 18.6 จริง 41 ข้อ = db 23 + users 18) ผลโมเดลไม่เปลี่ยน
  > 28 ก.ย. Windows Smart App Control บล็อก DLL ของ pandas / sklearn / psycopg-binary แก้โดยติดตั้งเวอร์ชันเดิมใหม่ด้วย `--force-reinstall --no-cache-dir --no-deps` **โดยไม่ปิด SAC** (วิธีอยู่ใน README)
- [x] ทดสอบบนมือถือจริง (Android, Expo Go, 28 ก.ย. 2026)
  > ผ่าน: กราฟรายชั่วโมงเป็นรูประฆัง สูงสุด 8.3 ตอน 12:00 สีถูก, หน้าตั้งค่า (safe = เตือน − 2 ถูก), สวิตช์ความยินยอม, หน้ายืนยันการลบ, แบบสอบถาม
  > แก้ UI หลังทดสอบ: (1) ชั่วโมงที่เลือกเคยเป็นพื้นหลังเทาสูงเต็มกราฟ ดูเหมือนค่า UV สูง ตอนนี้เป็น**จุดใต้แกน** และตัวเลขชั่วโมงเป็นตัวหนา (2) เปิดกราฟครั้งแรก ถ้าเป็นกลางวันจะเริ่มที่ชั่วโมงปัจจุบัน ถ้าเป็นกลางคืนจะ**เลือกและเลื่อนไปที่ชั่วโมงสูงสุดของช่วงกลางวันถัดไป** ("พรุ่งนี้ …", `initialFocusIndex`, `scrollOffsetFor`) (3) สวิตช์ "เปิดการแจ้งเตือน" (ส่งจากเซิร์ฟเวอร์) **ปิดการใช้งานและแสดงเป็นปิด** จนกว่าจะยินยอม พร้อมป้าย "ยังไม่ทำงาน ต้องยินยอมให้ส่งข้อมูลก่อน" และย้ายการ์ดความยินยอมขึ้นไปไว้เหนือการ์ดแจ้งเตือน
  > **ใช้กติกาปัดค่าเดียวกันทุกที่:** `round_uvi()` (ปัดเป็นจำนวนเต็ม x.5 ปัดขึ้น) ใน `src/metrics.py` เป็นฐานของ `who_level` (ระดับของชั่วโมงในกราฟ), `risk.assess` (การ์ดหลัก) และฟังก์ชันใหม่ `risk.reaches_alert` / `risk.is_safe_again` ที่งานแจ้งเตือนวัน 23 ต้องใช้ ถ้าเทียบค่าดิบ `7.8 >= 8` จะไม่เตือน ทั้งที่การ์ดแสดง "สูงมาก" ฝั่งแอปมี `roundUvi` / `reachesAlert` / `isSafeAgain` ที่ทำแบบเดียวกัน เทสทั้ง pytest และ Jest อ่านกรณีจากไฟล์เดียวกัน `source_code/tests/who_rounding_cases.json` (2.49/2.5, 5.49/5.5, 7.49/7.5, 7.8, 10.49/10.5 ฯลฯ) และมีเทสว่าแท่ง 7.8 ในกราฟเป็นสีแดง (สูงมาก)
  > ทดสอบ: Jest **127 passed**, `tsc` / `expo lint` / `expo export --platform web` ผ่าน pytest **294 passed, 0 skipped** (PostgreSQL 41 ข้อ)
  > **กติกาเตือนเทียบกับผล test วัน 10:** ตอนใช้งานจริง ปัด UVI ก่อนแล้วค่อยเทียบกับเกณฑ์ (7.5 → 8 จึงเตือนที่เกณฑ์ 8, 7.49 ไม่เตือน) ตรวจโค้ดแล้วพบว่า T6a–T6d ของวัน 10 วัดด้วยกติกาเดียวกัน คือ `evaluate_test.py` เรียก `quantile.alert_report()` ซึ่งแปลงทั้ง NASA POWER และ q90 เป็นระดับด้วย `who_level()` → `round_uvi()` การปัดจึงไม่ต่างกัน ไม่ต้องคำนวณใหม่ และไม่ได้รัน test 2025 ใหม่ มีจุดต่างที่ไม่ใช่เรื่องการปัดอยู่ข้อเดียว: T6 ใช้ q90 (CQR) อย่างเดียว ส่วนตอนใช้งานใช้ `max(q90, ค่าจุด)` บน dev 2024 สองค่านี้เท่ากันทุกชั่วโมง (ค่าจุดไม่เกิน q90 เลยใน 3,726 ชม.) รายละเอียดอยู่ใน `docs/results_summary.md`
  > ~~ค้าง: ตรวจหน้าจอข้อ 7–10 ใน `source_code/app/README.md` ด้วย browser agent ของ Antigravity (ยังไม่ได้รับผล)~~ **แทนด้วยการทดสอบบนมือถือจริง (Samsung, Expo Go) + Jest** (ตัดสิน 29 ก.ย. 2026)

### วัน 20 — กล้อง + เซนเซอร์แสง
- [x] expo-camera ส่งภาพไป `/sky-image` → `src/app/camera.tsx`, `src/lib/sky.ts`, `src/lib/skyPhoto.ts`, `uploadSkyImage()` ใน `src/api/client.ts`
  > **ความเป็นส่วนตัว:** ก่อนถ่ายครั้งแรกแสดงข้อความ "ภาพจะถูกส่งไปวิเคราะห์ที่เซิร์ฟเวอร์แล้วลบทันที ไม่มีการเก็บภาพ" (กดรับทราบแล้วจำไว้ในเครื่องที่ `skyNoticeAck` ซึ่งไม่ส่งไปเซิร์ฟเวอร์) ถ่ายด้วย `exif: false` และ**ส่งภาพที่ re-encode ใหม่ทุกครั้ง** (expo-image-manipulator, ด้านยาวสุด 1024 px, JPEG 0.8) ไฟล์ต้นฉบับและไฟล์ re-encode **ถูกลบใน `finally`** ทั้งตอนที่ส่งสำเร็จ, ส่งไม่สำเร็จ และ re-encode ไม่สำเร็จ (มีเทส Jest ทั้ง 3 กรณี) ขอสิทธิ์กล้องอย่างเดียว ไม่ขอไมโครโฟน
  > **EXIF ฝั่ง API:** `src.sky_infer.has_exif()` + log `sky-image upload has_exif=<bool>` ซึ่งไม่ log ค่าของ EXIF (เทสตรวจว่ารุ่นมือถือและ GPS ไม่อยู่ใน log) ตรวจกับ API จริง (uvicorn): JPEG ที่มี GPS + รุ่นมือถือได้ `has_exif=True` และภาพเดียวกันหลัง re-encode ได้ `has_exif=False` ทั้งคู่ได้ 200 และ key ของ response ตรงกับ `SkyImageResponse` ใน `types.ts` ครบ พบว่า logger `uvguard.api` ไม่เคยพิมพ์ INFO ตอนรันด้วย uvicorn เลย (รวมถึง "models loaded") จึงเพิ่ม `configure_logging()` เปิดเฉพาะ logger นี้ ซึ่ง log แค่ user id, จำนวน, ชื่อ backend และ boolean ตัวนี้
  > **ผลที่แสดง:** สภาพท้องฟ้า (SWIMCAT-ext), ความมั่นใจ %, สัดส่วนเมฆ (red/blue) % และ reliability จาก API ถ้า `sky_confidence < 0.5` จะแสดง **"ไม่แน่ใจ"** พร้อมคลาสที่เป็นไปได้ 2 อันดับแรก ทุกผลมีข้อความ "ข้อมูลประกอบเท่านั้น ไม่เปลี่ยนค่า UVI · ไม่บันทึกภาพ" และหมายเหตุ "โมเดลทดสอบกับภาพจากเว็บ ความแม่นยำกับภาพจากกล้องมือถือยังไม่ได้วัด" ชื่อคลาสภาษาไทยในแอปต้องตรงกับ `SWIM_CLASS_TH` (`test_app_sky_class_names_match_api`) API แจ้ง 413/415 เป็นภาษาไทย ถ้ากล้องเงยไม่ถึง 30° จะขึ้นคำแนะนำให้ยกกล้องขึ้น
- [x] LightSensor (Android) + ตรวจทิศทางมือถือ → `src/app/light.tsx`, `src/lib/lux.ts`, `src/lib/orientation.ts`, `src/lib/useGravity.ts`
  > กั้นด้วย `Platform.OS === 'android'` ปุ่ม "วัดแสง" ในหน้าหลักขึ้นเฉพาะบน Android ส่วน iOS/เว็บขึ้นข้อความ "ใช้ได้เฉพาะ Android" และเครื่องที่ไม่มีเซนเซอร์ (`isAvailableAsync`) ก็แจ้งเช่นกัน ค่า lux เป็น median ของ 2 วินาทีล่าสุด (ค่ากระโดดครั้งเดียวไม่มีผล) และหยุดฟังเซนเซอร์เมื่อออกจากหน้า ทิศทางมือถือหาจาก accelerometer: มุมระหว่างแนวตั้งฉากกับหน้าจอและแนวดิ่ง ถ้าไม่เกิน 15° ถือว่า "ทิศทางถูกต้อง" ถ้ามากกว่านั้นขึ้น "เอียงเกินไป" หรือ "คว่ำ" และบอกว่าค่ายังไม่ควรใช้ Android ส่งค่า z ≈ +1 g เมื่อวางหงาย (อ่านจาก `AccelerometerModule.kt`) ส่วน iOS กลับเครื่องหมาย ค่า lux **ยังไม่ได้ปรับเทียบ** และไม่เปลี่ยนค่า UVI ยังไม่ได้แยก "กลางแดด/ในร่ม" และยังไม่บันทึกค่า (ทั้งสองเรื่องเป็นงานวัน 25)
  > ทดสอบ: Jest **168 passed** (14 suites; เทสใหม่ orientation, lux, sky, camera, light, และลิงก์ในหน้าหลัก), `tsc` / `expo lint` / `expo export --platform web` ผ่าน, pytest **298 passed, 0 skipped**
- [ ] ทดสอบกล้องและเซนเซอร์แสงบนมือถือ Android จริง
  > ค้าง: ต้องทำเองบนมือถือตามขั้นตอนใน `source_code/app/README.md` ("ทดสอบกล้องและเซนเซอร์แสงบนมือถือจริง") โดยเฉพาะ (1) log ของ API ต้องเป็น `has_exif=False` กับภาพจากกล้องจริง ซึ่งในเครื่องนี้ไม่มีภาพจริงที่มี EXIF ให้ทดสอบ (สุ่มดูใน dataset 5,000 ภาพแล้วไม่มีสักภาพ) และ (2) เครื่องหมายแกน z บน Samsung ต้องให้ผลว่าวางหงาย = "ทิศทางถูกต้อง" ส่วนรายการตรวจหน้าจอข้อ 11–12 ให้ browser agent ของ Antigravity ตรวจ

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
### head CNN สัดส่วนเมฆจาก SWIMSEG (ทำหลังวัน 20)
> **ประกาศก่อนฝึกและก่อนเปิด test split (commit นี้)** โค้ดคือ `src/sky_cloud.py` (`CLOUD_CRITERIA`, `judge_cloud()`, `ships()`) และ `--test` รันได้ครั้งเดียว (มี guard คือไฟล์ `docs/sky_cloud_test.json`) **หลังเห็นผลห้ามแก้โมเดล ข้อมูล split หรือ config ถ้าไม่ผ่านให้รายงานตามจริง** ห้ามแตะ XGBoost, CNN วัน 14 (`sky_cnn_v1*`) และ test ของโมเดลอื่น
> - **ข้อมูล:** SWIMSEG (Dev, Lee & Winkler 2017, CC BY-NC 4.0) อยู่ที่ `dataset/sky/raw/swimseg` มีภาพ 1,013 ภาพ, mask 1,013 ไฟล์ (0/255, 600×600) และ `metadata.csv` 1,013 แถว ตรวจ license จาก `license.html` / `readme.pdf` แล้ว ภาพเป็น patch ที่แปลงจากกล้องถ่ายทั้งท้องฟ้า (WAHRSIS, NTU สิงคโปร์) ให้เป็นมุมมองเลนส์ธรรมดาประมาณ 62° **ไม่ใช่ภาพ fisheye**
> - **target** = สัดส่วนพิกเซลเมฆใน mask **(สีขาว = เมฆ)** ตรวจบน train เท่านั้น: Spearman กับ red/blue = +0.73 และดูภาพแล้ว (ฟ้าใส → mask ดำ) ส่วน `class_dict.csv` ของไฟล์ที่นำมาอัปโหลดซ้ำเขียนว่าสีดำ = เมฆ ซึ่ง**ผิด**
> - **split (ห้ามรั่ว):** ไม่ใช้ train/val/test ที่มากับไฟล์ ภาพ 1,013 ภาพมาจากการถ่ายแค่ **33 ครั้ง ใน 17 วัน** และบางครั้งถ่ายห่างกันไม่กี่นาที (16:52 กับ 16:54) จึง**จัดกลุ่มตามวันถ่าย** รวมกับกลุ่มภาพซ้ำตามกฎวัน 13 (thumbnail 16×16, 8 แบบ, MAD < 0.03) แล้วแบ่ง 70/15/15 ตามกลุ่ม ใช้ seed แรกตั้งแต่ 42 ที่สัดส่วนภาพห่างเป้าไม่เกิน ±5 pp และทุก split มีทั้ง mask ที่เมฆ < 20 % และ > 80 % (กฎนี้ไม่ใช้ผลโมเดล) → **seed 43: train 735 ภาพ / 9 วัน, val 137 / 3 วัน, test 141 / 5 วัน** และไม่มีกลุ่มไหนคร่อม split → `docs/sky_splits/swimseg_split.csv` (`python -m src.sky_data --index-swimseg` ไม่เขียน split ของ CCSN / SWIMCAT-ext ทับ)
> - **ภาพซ้ำข้าม dataset** (กฎเดียวกัน) → `docs/sky_swimseg_crossdataset_duplicates.csv`: 11 คู่ ภาพ SWIMSEG 6 ภาพใน train/val กับ SWIMCAT-ext veil_clouds (train 10, test 1) ส่วน **test ของ SWIMSEG มี 0 คู่** เมื่อดูภาพแล้วไม่มีคู่ไหนเป็นภาพเดียวกัน (ฟ้าเทาหรือฟ้าเรียบ ซึ่งเป็น false positive แบบวัน 15)
> - **โมเดล:** backbone MobileNetV3Small จาก `sky_cnn_v1_seed43.keras` **แช่ทั้งหมด** (feature 576 มิติหลัง GAP, BatchNorm อยู่ในโหมด inference) + head Dropout 0.2 → Dense(1, sigmoid), loss MAE, Adam 1e-3, batch 32, ไม่เกิน 50 epochs, early stopping บน val (patience 5, คืน weights ที่ดีที่สุด), augmentation วัน 13 **เฉพาะ flip และปรับสี/ความสว่าง/blur (ไม่หมุน ไม่ perspective เพราะ mask ไม่ได้แปลงตาม)**, **3 seeds (42/43/44)** รายงาน mean ± SD, seed ที่ export (TFLite float16 แยกไฟล์ `sky_cloud_v1.tflite`) เลือกจาก val loss ส่วน `sky_cnn_v1.tflite` ไม่แตะ
> - **baseline:** red/blue `NRBR < 0.25` (ค่าเดิมจากงานวิจัย ไม่ได้ปรับ) บนภาพชุดเดียวกัน
>
> | # | ตัวชี้วัด (SWIMSEG test, 141 ภาพ / 5 วัน) | เกณฑ์ผ่าน |
> |---|---|---|
> | C1 | MAE ของสัดส่วนเมฆ (ค่าเฉลี่ย 3 seeds) | **≤ 0.10** |
> | C2 | MAE ของ red/blue − MAE ของ CNN | **≥ 0.03** |
>
> รายงานเพิ่มแบบไม่มีเกณฑ์: RMSE, bias, MAE แยกตามช่วงสัดส่วนเมฆ และ**MAE รายวันของ test** (test มีแค่ 5 วัน ผลจึงแกว่งได้มาก)
> **ถ้าผ่านทั้ง C1 และ C2:** `/sky-image` ส่ง `cloud_fraction_cnn` และแอปแสดงเป็นข้อมูลประกอบ ("สัดส่วนเมฆในภาพ ไม่ใช่ทั้งท้องฟ้า") **ถ้าไม่ผ่านข้อใดข้อหนึ่ง:** API ไม่ส่งค่านี้และแอปไม่แสดง แต่บันทึกผลตามจริงใน ROADMAP และ `docs/results_summary.md` ในทุกกรณีค่านี้ไม่เปลี่ยน UVI
> **ข้อจำกัด:** SWIMSEG ถ่ายจากกล้องถ่ายทั้งท้องฟ้าที่สิงคโปร์ (NTU, 1.34N) แล้วแปลงเป็นมุมมองเลนส์ธรรมดาประมาณ 62° และ mask ติดป้ายโดยผู้เชี่ยวชาญ ภาพจากมือถือเห็นท้องฟ้าแค่บางส่วน และสี, white balance, การรับแสง รวมถึงวัตถุในภาพ (ตึก, ต้นไม้) ต่างจากชุดข้อมูล ค่าที่ได้คือ**สัดส่วนเมฆในภาพ ไม่ใช่ทั้งท้องฟ้า** และยังไม่ได้วัดผลบนภาพจากมือถือ ข้อมูลมีแค่ 17 วัน
- [x] ตรวจไฟล์ SWIMSEG + ประกาศเกณฑ์ + split ตามวัน → `src/sky_data.py` (`index_swimseg_folders`, `union_groups`, `split_ok`, `build_swimseg_split`), `src/sky_cloud.py`, `tests/test_sky_cloud.py`
- [x] ฝึก 3 seeds (ผู้ใช้รันเองใน PowerShell, 28 ก.ย. 23:08–23:33) → `models/sky_cloud_v1_seed{42,43,44}.keras`, `models/sky_cloud_v1_metrics.json`, `models/sky_cloud_v1.tflite`
  > ฝึกใหม่ครบทั้ง 3 seeds (`resumed: false`) early stopping หยุดที่ 32 / 44 / 45 epochs (ไม่มี seed ไหนวิ่งจนครบ 50) **val MAE 0.0795 / 0.0783 / 0.0776** เทียบกับ red/blue บน val 0.150 export **seed 44** (val loss ต่ำสุด) TFLite float16 ต่างจาก Keras บน val สูงสุด 0.0077 (MAE ของ TFLite บน val 0.0774) ไฟล์ `sky_cnn_v1*` ของวัน 14 ไม่ถูกแก้ (เวลาไฟล์ยังเป็น 26–27 ก.ย.)
- [x] ประเมิน test ครั้งเดียว → `docs/sky_cloud_test.json`, `docs/figures/sky_cloud_test_scatter.png`
  > **ผ่านทั้ง 2 เกณฑ์** (141 ภาพ / 5 วัน, หลังเห็นผลไม่ได้แก้อะไร) **C1** MAE ของ CNN **0.084 ± 0.0015** (seed 42/43/44: 0.085 / 0.082 / 0.084) ✅ (≤ 0.10) **C2** red/blue MAE 0.145 → ดีกว่า **+0.061** ✅ (≥ 0.03) RMSE 0.103 เทียบกับ 0.188, bias ของ CNN −0.012 (ค่าเฉลี่ยของ 3 seeds ได้ MAE 0.0825) **CNN ดีกว่า red/blue ทุกวันทั้ง 5 วันของ test:** MAE รายวัน 0.041–0.097 เทียบกับ 0.117–0.209 แต่ CNN **ดึงค่าเข้าหาค่ากลาง** (ช่วงเมฆน้อยทายสูงไป ช่วงเมฆมากทายต่ำไป ในกราฟแทบไม่ทายต่ำกว่า 15 %) และ test มีภาพเมฆ < 20 % แค่ 7 ภาพ และ > 80 % แค่ 9 ภาพ ผลที่ปลายสองด้านจึงยังไม่แน่นอน ส่วน MAE ของ seed 42 ในช่วงเมฆ < 20 % เท่ากับ 0.127
- [x] ผ่านเกณฑ์ → API ส่ง `cloud_fraction_cnn` + แอปแสดงเป็นข้อมูลประกอบ → `src/sky_infer.py` (`cloud_head_result`, `predict_cloud_fraction`), `src/inference.py`, `api/main.py`, `api/schemas.py`, แอป `camera.tsx`, `lib/sky.ts`, `types.ts`
  > กติกาอยู่ในโค้ดด้วย: `ModelBundle.load()` โหลด `sky_cloud_v1.tflite` **ก็ต่อเมื่อ** `docs/sky_cloud_test.json` มี `ships: true` ถ้าไม่มี API จะไม่ส่ง field นี้เลย (`response_model_exclude_none`) และแอปจะไม่แสดง (มีเทสทั้งสองกรณี) แอปแสดงบรรทัด "สัดส่วนเมฆในภาพ (โมเดล)" พร้อมข้อความ "สัดส่วนเมฆในภาพ ไม่ใช่ทั้งท้องฟ้า" คงบรรทัด red/blue ไว้ และค่านี้**ไม่เปลี่ยน UVI** ตรวจกับ API จริง: `/health` แสดง `sky_cloud_v1.tflite` และ `/sky-image` ได้ `cloud_fraction_cnn` พร้อม reliability ส่วน key ตรงกับ `types.ts` ภาพสีฟ้าล้วนได้ CNN 0.16 เทียบกับ red/blue 0.00 ซึ่งตรงกับเรื่องดึงค่าเข้าหาค่ากลาง
  > ทดสอบ: pytest **314 passed, 0 skipped**, Jest **170 passed**, `tsc` / `expo lint` / `expo export --platform web` ผ่าน
  > ค้าง: ยังไม่ได้ลองกับภาพจากมือถือจริง (ใช้ขั้นตอนเดิมใน `source_code/app/README.md`)
- [x] ตรวจหลังรัน `--train` ซ้ำโดยไม่ตั้งใจ (29 ก.ย. 00:03, กด Ctrl+C) และเทียบกับไฟล์ทางการ
  > **ไฟล์ `.keras` ไม่ถูกเขียนทับ:** ทั้ง 3 seed ถูกโหลดจากไฟล์เดิม (log: "reloaded … (not retrained)", val loss 0.0795 / 0.0783 / 0.0776 เท่าเดิม) เวลาไฟล์ยังเป็น 23:14 / 23:23 / 23:33 ซึ่งก่อนรัน test (23:38) จึงเป็นชุดเดียวกับที่ใช้ตอน test การรันครั้งนี้ export `sky_cloud_v1.tflite` ซ้ำ แต่ได้ไฟล์ที่ **hash ตรงกับ commit `d1bf56a` ทุก byte** (`8cd8010…`) ส่วน `sky_cloud_v1_metrics.json` ถูกเขียนใหม่ (`created`, `resumed`) จึงกู้คืนด้วย `git checkout --` แล้ว hash ตรงกับ `d1bf56a` ส่วน `docs/sky_cloud_test.json` และกราฟไม่ถูกแตะ (hash ตรงกับ `d1bf56a`) ไม่ได้รัน `--test` ซ้ำ
  > **ไฟล์ทางการ:** `swimseg.zip` จากลิงก์ของผู้สร้าง (Dev, Lee & Winkler, CC BY-NC 4.0, ใส่รหัสผ่านไว้ รหัสผ่านอยู่ใน `.env`) **ภาพ 1,013 ภาพ + mask 1,013 ไฟล์ ตรงกับ `archive (19).zip` และโฟลเดอร์ที่ใช้เทรนทุก byte (SHA-256)** รวมถึง `metadata.csv` และ `license.html` ส่วนที่ต่างกันเป็นไฟล์ที่ไม่ได้ใช้เทรน: `readme.pdf` คนละ build (2016 เทียบกับ 2018), `class_dict.csv` (เขียนสีกลับ) และ `_DS_Store` ที่มีแค่ในชุดที่นำมาอัปโหลดซ้ำ **จึงไม่ต้องเทรนใหม่ ใช้ผลเดิม (MAE 0.084)** manifest อยู่ที่ `docs/sky_splits/swimseg_official_sha256.csv` zip ทั้งหมด (`archive (19).zip`, `swimseg`, `swimcat`, `shwimseg`, `swinseg`, `swinyseg`) อยู่ใน `dataset/sky/raw/` และ git ignore แล้ว
  > **แอปแสดงเป็นระดับแทน %:** `cloud_fraction_cnn` < 30 % = น้อย, 30–70 % = ปานกลาง, > 70 % = มาก (`cloudLevelTh`) พร้อมหมายเหตุ "ภาพท้องฟ้าใสอาจแสดงเป็นเมฆน้อย" เพราะโมเดลดึงค่าเข้าหาค่ากลาง API ยังส่งเป็นตัวเลข 0–1 เหมือนเดิม และแก้เอกสารที่ยังเขียนว่า SWIMSEG เป็น future work (rules, `START_HERE.md`, `docs/datasets.md`, docstring ของ `sky_data.py`) ส่วนบันทึกวัน 13–15 ใน ROADMAP และ notebook 13/14 คงข้อความเดิมไว้แล้วเติมหมายเหตุ "อัปเดตหลังวัน 20" (notebook แก้เฉพาะเซลล์ markdown ไม่ได้รันใหม่)
- [ ] Himawari cloud products (JAXA P-Tree) เป็น features ความหนาเมฆ
- [ ] ติดต่อขอข้อมูลวัด UV ภาคพื้นดินที่นครปฐม (ม.ศิลปากร) ใช้เป็น ground truth

## ถ้าช้ากว่าแผน ตัดตามลำดับนี้
1. CNN ภาพท้องฟ้า (วัน 13–14; วัน 15 สำรอง)
2. เซนเซอร์แสงมือถือ + calibrate
3. การเก็บข้อมูลภาคสนาม (วัน 25) เหลือแค่ทดสอบในที่เดียว
