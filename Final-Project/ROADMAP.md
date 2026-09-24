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
  > CMF (p01–p99): UVI 0.25–0.88 (ค่ามัธยฐาน 0.63), A 0.31–0.96 (0.74), B 0.33–1.00 (0.75) มีแค่ `cmf_b` ~1% ที่เกิน 1 ยังไม่ clip เรื่องนี้จะตัดสินในวัน 6; CMF ลดลงตอนดวงอาทิตย์ต่ำ (UVI ~0.4 ที่ 17:30) จึงยังขึ้นกับเรขาคณิตด้วย
- [x] ~~features จากทั้งสองแหล่ง: เมฆ Open-Meteo + CLOUD_AMT และ clear-sky index (ALLSKY / CLRSKY SW) ของ NASA POWER~~ → **features มาจาก Open-Meteo หรือคำนวณจากเวลา/ตำแหน่งเท่านั้น** (ผู้ใช้ตัดสินในวัน 5 และเขียนลง rules แล้ว)
  > ตัด feature ทุกตัวที่มาจาก NASA POWER ออก (CLOUD_AMT, ALLSKY/CLRSKY SW, clear-sky index, TO3) เพราะไม่มีตอนใช้งานจริง และเป็น target leakage (แหล่งเดียวกับ target) แทนด้วย Open-Meteo `cloud_cover_low/mid/high`, `shortwave/direct/diffuse_radiation`, `precipitation` และ `om_kt` = shortwave / GHI ฟ้าใส (Haurwitz) รวม 23 features; `om_kt` สัมพันธ์กับ CMF_UVI +0.65 ซึ่งใกล้กับ clear-sky index ของ NASA ที่ตัดออก (+0.59)
- [x] บันทึก dataset → `dataset/processed/train.parquet` (11,173 ชม.) และสเปก `source_code/models/dataset_spec_v1.json` (รายการ feature/target สำหรับวัน 6 ขึ้นไปและ API)
→ `dataset/processed/train.parquet`, `source_code/src/features.py`, `source_code/notebooks/05_dataset.ipynb`

**Checkpoint วัน 5: Dataset พร้อมฝึก**

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
> | T6d | เตือนรุนแรงมาก ด้วย q90: recall | **≥ 0.80** |
>
> รายงานแยกตามแหล่ง (NASA / OMI / TEMIS) และแยกจากผล dev รวม confusion matrix และ recall ระดับสูงมาก/รุนแรงมาก (exact level) ตาม rules อ้างอิงปี 2023 (notebook 02): NASA POWER เทียบ OMI MAE 1.14 และเทียบ TEMIS วันฟ้าเปิด MAE 2.68 (bias −2.68) ดังนั้น T3b อาจไม่ผ่านเพราะ bias ของ target เอง
- [ ] refit โมเดลที่เลือกบนข้อมูล 2023–2024 แล้วประเมินบน **test ปี 2025 ครั้งเดียว** (NASA POWER) รายงานแยกจากผล dev
- [ ] Confusion matrix + Recall ระดับสูง
- [ ] **ทดสอบอิสระ:** ดึง OMI ปี 2025 (`fetch_validation --split test`) แล้วเทียบค่าช่วงเที่ยงวันกับ TEMIS (UVI) และ OMI (UVI, 305/310 nm ≈ UVB, 324/380 nm ≈ UVA) **ปี 2025 เท่านั้น** รายงาน MAE แยกตามแหล่ง
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
