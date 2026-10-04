# UV Guard ☀️

ระบบ Machine Learning ประเมินรังสี UV (UVI, UVA, UVB) ณ ตำแหน่งผู้ใช้ แปลงเป็นความเสี่ยงต่อผิวตามประเภทผิว (Fitzpatrick I–VI) และเตือนผ่านแอปมือถือ ใช้แค่สมาร์ตโฟนเครื่องเดียวกับ API ฟรี ไม่มีเซนเซอร์หรือโมดูลเสริม

> **ข้อจำกัดความรับผิดชอบ:** ค่า UV, ระดับความเสี่ยง, เวลาผิวไหม้ และคำแนะนำทั้งหมดเป็นค่าประมาณเพื่อการศึกษาและการเตือนภัยทั่วไปเท่านั้น ไม่ใช่การวินิจฉัยหรือคำแนะนำทางการแพทย์ หากมีปัญหาผิวหนังควรปรึกษาแพทย์

> **พื้นที่ใช้งาน:** โมเดลฝึกและทดสอบด้วยข้อมูลของ**ปทุมธานีเท่านั้น** (NASA POWER จุดเดียว 14.02N 100.52E และ ozone climatology ของจุดนั้น) แอปใช้ GPS หรือเลือกจังหวัดได้ทั่วประเทศ แต่ถ้าตำแหน่งห่างจากปทุมธานีเกิน 50 กม. ความแม่นยำยังไม่ได้ประเมิน และหน้าหลักจะขึ้น "ความแม่นยำนอกพื้นที่ปทุมธานียังไม่ได้ประเมิน" นอกกรอบประเทศไทย API ตอบ 422

## สารบัญ
- [สถาปัตยกรรม](#สถาปัตยกรรม)
- [โครงสร้างโฟลเดอร์](#โครงสร้างโฟลเดอร์)
- [ติดตั้ง](#ติดตั้ง)
- [วิธีใช้](#วิธีใช้)
- [ผลลัพธ์](#ผลลัพธ์)
- [ภาพหน้าจอ](#ภาพหน้าจอ)
- [ข้อจำกัด](#ข้อจำกัด)
- [เอกสารเพิ่มเติม](#เอกสารเพิ่มเติม)

## สถาปัตยกรรม
```
GPS / เวลา / Open-Meteo (weather + air quality) → Feature Engineering (23 features)
→ Clear-sky physics (UVI: Madronich, UVA/UVB: pvlib SPECTRL2) × CMF จาก XGBoost multi-output
→ ช่วง q10–q90 (quantile XGBoost + CQR) → Risk Engine (ระดับ WHO, เวลาผิวไหม้จากค่าบน)
→ FastAPI + PostgreSQL → แอป Expo + การแจ้งเตือน (local + push จากเซิร์ฟเวอร์)
```
ไดอะแกรม Mermaid ฉบับเต็ม (ข้อมูล → โมเดล → API/DB → แอป → การแจ้งเตือน) อยู่ใน [docs/architecture.md](docs/architecture.md)

- **Ground truth:** NASA POWER hourly (community RE) `ALLSKY_SFC_UV_INDEX`, `ALLSKY_SFC_UVA`, `ALLSKY_SFC_UVB` เป็นข้อมูลดาวเทียม/แบบจำลอง **ไม่ได้ใช้เครื่องวัด UV จริง** NASA POWER ใช้เป็น target ตอนฝึกเท่านั้น ไม่ใช่ feature
- **Features:** Open-Meteo Historical Forecast API + Air Quality API (ตอนฝึก) และ Forecast API ตัวแปรชุดเดียวกัน (ตอนใช้งาน) รวมกับเรขาคณิตดวงอาทิตย์และเวลา
- **พยากรณ์ 6–24 ชม.:** ใช้ XGBoost ตัวเดียวกัน ส่วน LSTM ทดลองแล้วไม่ผ่านเกณฑ์ (วัน 12)
- **CNN ภาพท้องฟ้า:** เป็นโมดูลแยก **ไม่ stack กับ XGBoost และไม่ปรับค่า UVI**
  - แอปแสดง: สภาพท้องฟ้าจาก SWIMCAT-ext (6 คลาส + ความมั่นใจ), สัดส่วนเมฆจากอัตราส่วนแดง/น้ำเงิน และสัดส่วนเมฆในภาพจาก head ที่ฝึกบน SWIMSEG เป็นข้อมูลประกอบเท่านั้น
  - ฝึกจาก dataset สาธารณะเท่านั้น: CCSN, SWIMCAT-ext และ SWIMSEG ภาพที่ถ่ายในแอปไม่ถูกบันทึกและไม่นำไปฝึก
  - ค่าสัดส่วนเมฆเป็นของ**ภาพที่ถ่าย ไม่ใช่ทั้งท้องฟ้า**

## โครงสร้างโฟลเดอร์
| Folder | Content |
|---|---|
| `source_code/src/` | ดึงข้อมูล, ฟิสิกส์, features, การฝึก, risk engine, ฐานข้อมูล, push scheduler |
| `source_code/tests/` | pytest |
| `source_code/notebooks/` | EDA และการทดลอง (01–14) |
| `source_code/models/` | โมเดลที่บันทึกไว้ + `*_metrics.json` |
| `source_code/api/` | FastAPI service ([docs/api.md](docs/api.md)) |
| `source_code/migrations/` | Alembic migrations ([docs/db.md](docs/db.md)) |
| `source_code/app/` | แอป Expo (React Native, TypeScript) ([source_code/app/README.md](source_code/app/README.md)) |
| `dataset/` | `raw/`, `processed/`, `validation/`, `sky/` (ไม่อยู่ใน git) และ `field/` ข้อมูลภาคสนามจากมือถือ |
| `docs/` | เอกสาร, รูป, ผลลัพธ์, รายงาน ([docs/report.md](docs/report.md)) |

## ติดตั้ง
ต้องใช้ **Python 3.12** (venv ของโปรเจกต์คือ 3.12.10), PostgreSQL (ทดสอบบน 18.6) และ Node.js (สำหรับแอป)

```powershell
# Windows PowerShell (จากโฟลเดอร์ Final-Project)
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # แล้วแก้ค่าใน .env (ห้าม commit .env)
```
macOS / Linux: `python3.12 -m venv .venv && source .venv/bin/activate`

ค่าใน `.env` (ดูตัวอย่างใน `.env.example`):
- `DATABASE_URL`: PostgreSQL หลัก ถ้าไม่ตั้งจะใช้ SQLite fallback พร้อม WARNING
- `TEST_DATABASE_URL`: ฐานข้อมูลทดสอบ ชื่อต้องมีคำว่า `test` เพราะเทสจะลบตารางทั้งหมด
- `EXPO_ACCESS_TOKEN`: ไม่บังคับ ใช้กับ Expo Push Service
- `CORS_ORIGINS`: origin ของเบราว์เซอร์ที่เรียก API ได้ (ค่าเริ่มต้นคือ Expo web `localhost:8081`)
- `EARTHDATA_USERNAME` / `EARTHDATA_PASSWORD`: ใช้ดาวน์โหลด OMI เท่านั้น

วิธีติดตั้ง PostgreSQL และสร้างฐานข้อมูลอยู่ใน [docs/db.md](docs/db.md)

**แอป:** ที่ `source_code/app/` รัน `npm install` และถ้าต้องเปลี่ยนที่อยู่ API ให้ตั้ง `EXPO_PUBLIC_API_URL` ใน `.env.local` (ดู `source_code/app/.env.example`)

### เมื่อ Windows Smart App Control บล็อก DLL ใน `.venv`
อาการ: `ImportError: DLL load failed ... An Application Control policy has blocked this file.` (เช่น `pandas/_libs/join`, `sklearn`, `psycopg_binary.libs/libpq`) ทำให้ `pytest` หรือการต่อ PostgreSQL ใช้ไม่ได้

**อย่าปิด Smart App Control** (ปิดแล้วเปิดกลับไม่ได้ถ้าไม่ reset Windows) ให้ติดตั้งแพ็กเกจที่โดนบล็อกใหม่ **ด้วยเวอร์ชันเดิม** ก่อน:
```powershell
.venv\Scripts\python.exe -m pip list                 # ดูเวอร์ชันที่ใช้อยู่
.venv\Scripts\python.exe -m pip install --force-reinstall --no-cache-dir --no-deps <package>==<เวอร์ชันเดิม>
.venv\Scripts\python.exe -c "import pandas, sklearn, psycopg; print('ok')"
```
- ต้องใส่ `--no-deps` ไม่อย่างนั้น pip จะลง numpy / scipy รุ่นล่าสุดตามมาด้วย (ข้าม `scipy<1.18`) ซึ่งอาจทำให้ผลโมเดลเปลี่ยน
- 28 ก.ย. 2026: pandas 3.0.6, scikit-learn 1.9.1 และ psycopg-binary 3.3.6 โดนบล็อก พอติดตั้งเวอร์ชันเดิมใหม่ก็ใช้ได้ (numpy/scipy ไม่เปลี่ยน) ทั้งที่ isort ซึ่งไม่ได้ติดตั้งใหม่ก็กลับมาโหลดได้เอง จึงน่าจะเกิดจากการตรวจชื่อเสียงไฟล์ของ SAC ล้มเหลวชั่วคราว
- ถ้ายังโดนบล็อก ให้ลองเวอร์ชันใกล้เคียง 1 รุ่น (แบบ `scipy<1.18` ใน `requirements.txt`) ถ้าเปลี่ยนเวอร์ชัน ต้องรัน `pytest` เพื่อยืนยันว่าผลโมเดลไม่เปลี่ยน

## วิธีใช้
ทุกคำสั่ง Python รันจาก `Final-Project/`

**1. เทส**
```powershell
pytest -q                     # Python (src, API, DB)
cd source_code/app; npm test  # แอป (Jest)
```
ผลล่าสุด (4 ต.ค. 2026): pytest **402 passed**, Jest **329 passed** (29 suites) ผลนี้มาจากการรันเทส ไม่ได้มาจากไฟล์ผลลัพธ์ในโปรเจกต์

**2. ฐานข้อมูล**
```powershell
alembic upgrade head
```

**3. API** (http://127.0.0.1:8000/docs)
```powershell
$env:PYTHONPATH = "source_code"
.venv\Scripts\python.exe -m uvicorn api.main:app --app-dir source_code --host 0.0.0.0 --port 8000
```
- `--host 0.0.0.0` จำเป็นเมื่อเปิดแอปจากมือถือจริง ถ้าใช้แค่บนคอมเครื่องเดียวกันตัดออกได้
- push scheduler (ทุก 30 นาที) เริ่มพร้อม API ถ้าจะปิดให้ตั้ง `PUSH_SCHEDULER=off`
- endpoint ทั้งหมดอธิบายไว้ใน [docs/api.md](docs/api.md)

**4. แอป** รันจาก `source_code/app/`
```powershell
npx expo start --web          # เว็บ http://localhost:8081
npx expo start --clear        # มือถือด้วย Expo Go (ไม่มีการแจ้งเตือนบน Android)
npx expo start --dev-client   # มือถือด้วย EAS development build (มีการแจ้งเตือน)
```
- **บนมือถือ:** ตั้ง `EXPO_PUBLIC_API_URL=http://<IP ของคอมใน LAN>:8000` แล้วตรวจจากมือถือว่าเปิด `http://<IP>:8000/health` ได้ก่อน
- **Android:** การแจ้งเตือนต้องใช้ development build (`eas build --profile development --platform android`) เพราะ Expo Go Android ไม่รองรับ `expo-notifications` ขั้นตอนทั้งหมดและเช็กลิสต์ทดสอบบนมือถืออยู่ใน [source_code/app/README.md](source_code/app/README.md) และ [docs/field_test_2026-10-04.md](docs/field_test_2026-10-04.md)

**การใช้งานแอป:** เปิดครั้งแรกจะเข้า onboarding 4 ขั้น (disclaimer → ตำแหน่ง GPS หรือเลือกจังหวัด → แบบสอบถามผิว 5 ข้อ → ความยินยอม ซึ่งปิดเป็นค่าเริ่มต้น) จากนั้นหน้าหลักแสดง:
- UVI พร้อมช่วง q10–q90 และสีระดับ WHO
- UVA/UVB, เวลาก่อนผิวไหม้ และคำแนะนำ SPF/PA
- กราฟรายชั่วโมง
- การ์ด "อยู่กลางแจ้ง" (ปุ่มออกแดด/ทาครีมแล้ว)
- ปุ่มถ่ายท้องฟ้า และวัดแสง (เฉพาะ Android)

หน้าตั้งค่าใช้ปรับเกณฑ์เตือน, สรุป 07:00, เตือนทาครีมซ้ำ, ความยินยอม และ "ลบข้อมูลของฉัน"

**5. สร้างข้อมูลและโมเดลใหม่ (ไม่จำเป็นถ้าจะแค่รัน API)** ให้ตั้ง `$env:PYTHONPATH = "source_code"` ก่อน แล้วรันตามลำดับ:
1. `python -m src.fetch_data` ดาวน์โหลด Open-Meteo และ NASA POWER แล้ว cache ไว้ที่ `dataset/raw/`
2. `python -m src.preprocess` แล้ว `python -m src.features` สร้าง `dataset/processed/train.parquet`
3. `python -m src.train_cmf`, `python -m src.train_multi`, `python -m src.tune` และ `python -m src.quantile` ฝึกและเลือกโมเดลด้วย train 2023 / dev 2024
4. `python -m src.sky_data --download --index` แล้ว `python -m src.sky_cnn --train` สำหรับ CNN ภาพท้องฟ้า และ `python -m src.sky_cloud --train` สำหรับ head สัดส่วนเมฆ

> **ห้ามรันซ้ำ:** `src.evaluate_test --run`, `src.lstm --test`, `src.sky_cnn --test` และ `src.sky_cloud --test` เปิด test split (ปี 2025 / test ของภาพ) ได้ **ครั้งเดียว** และรันไปแล้ว ผลอยู่ใน `docs/` ส่วน `src.fetch_validation` ใช้ข้อมูล TEMIS/OMI เพื่อ validation เท่านั้น

## ผลลัพธ์
ตัวเลขคัดจาก [docs/results_summary.md](docs/results_summary.md) (ไฟล์ต้นทางอยู่ในวงเล็บ) รายละเอียดทั้งหมดอยู่ใน [docs/report.md](docs/report.md)

**การเลือก ground truth (ปี 2023, เทียบ OMI ตอนเที่ยง, n = 275)** `[docs/source_selection_2023.csv]`
NASA POWER MAE **1.143** เทียบ Open-Meteo `uv_index` 2.428 จึงเลือก NASA POWER ตามกฎที่ประกาศไว้ก่อนดูผล (ต้องต่างกันเกิน 0.3)

**Test ปี 2025 ประเมินครั้งเดียว: ผ่าน 14 จาก 15 เกณฑ์ที่ประกาศไว้ก่อน** `[docs/test_2025_criteria.csv]`, `[docs/test_2025_results.json]`

| ตัวชี้วัด (2025) | ค่า | เกณฑ์ |
|---|---|---|
| UVI MAE รายชั่วโมงเทียบ NASA POWER (n = 3,718) | **0.479** | < 1.0 ✅ |
| baseline: CMF คงที่ / Open-Meteo / physics ฟ้าใส | 0.708 / 1.244 / 2.471 | โมเดลต่ำกว่าทุกตัว ✅ |
| R² | 0.934 `[source_code/models/cmf_multi_xgb_final_metrics.json]` | — |
| UVI ตอนเที่ยงเทียบ OMI (ฟ้ามีเมฆ) | 1.320 | ≤ 1.5 ✅ |
| UVI วันฟ้าเปิดเทียบ TEMIS | 1.360 (bias −1.36) | ≤ 1.5 ✅ |
| r ของ UVA/UVB กับ OMI irradiance | ต่ำสุด 0.533 | ≥ 0.7 ทั้ง 4 คู่ **❌ (T4)** |
| coverage ของช่วง q10–q90 (CQR) | 0.806 | 0.75–0.85 ✅ |
| เตือน ≥ สูงมาก (q90): recall / precision / false alarm | 0.986 / 0.564 / 0.163 | ✅ ทั้ง 3 ข้อ |
| เตือนรุนแรงมาก (q90): recall | 0.826 (19/23 ชม.) | ≥ 0.80 ✅ |

UVA MAE 2.910 W/m², UVB MAE 0.088 W/m² `[docs/test_2025_results.json]`

**ผลที่ไม่ผ่านเกณฑ์**
- **LSTM (พยากรณ์):** dev 2024 MAE 0.463 ± 0.007 ไม่ต่ำกว่าเกณฑ์ 0.430 (XGBoost 0.450) จึงใช้ XGBoost ในแอป `[source_code/models/lstm_v1_metrics.json]`
- **Sky CNN ผ่าน 7 จาก 10 ข้อ:** CCSN 11 คลาส accuracy 0.486 (เกณฑ์ ≥ 0.60), macro-F1 0.452 (≥ 0.55) และ 4 กลุ่ม UV 0.685 (≥ 0.75) ไม่ผ่าน จึงไม่แสดงชนิดเมฆในแอป ส่วน SWIMCAT-ext ได้ accuracy 0.975 `[docs/sky_cnn_test.json]`

**ผลที่ผ่านเกณฑ์ของ sky CNN**
- **Head สัดส่วนเมฆ (SWIMSEG) ผ่าน 2 จาก 2 ข้อ:** MAE 0.084 เทียบวิธีแดง/น้ำเงิน 0.145 `[docs/sky_cloud_test.json]`

**ทดสอบบนมือถือจริง:** เจอบั๊ก 2 ตัวบนมือถือ (FormData ตอนส่งรูป และ `expo-notifications` ทำให้ Expo Go Android พัง) และ 1 ตัวตอน EAS build (`package-lock.json`) ทั้ง 3 ตัวแก้แล้วและมีเทสกันไว้ (ตาราง M ใน [docs/report.md](docs/report.md)) 

**ทดสอบภาคสนาม 4 ต.ค. 2026** (Samsung Galaxy S23 Ultra, Android 16, EAS development build, ปทุมธานี วันเดียว ผู้ทดสอบคนเดียว ตาราง N–Q ใน [docs/report.md](docs/report.md) §4.8):
- **แจ้งเตือนในเครื่อง:** 3 รายการที่ยืนยันเวลาได้มาช้า 2–9 นาที (เฉลี่ย 5.7 นาที) แจ้งเตือนผิวไหม้รอบแรกไม่ได้รับ ส่วนสรุป 07:00 ไม่ได้ทดสอบ
- **สูตร:** เวลาเตือน 80 % ของ MED และ % ของ MED ที่แอปแสดงตรงกับสูตร (10:31 เทียบ ≈ 23 นาทีหลังกดออกแดด; 160 % เทียบสูตร 162 %)
- **กล้อง:** `has_exif=False` ทั้ง 2 ภาพที่อัปโหลด แต่ CNN ตอบ "เมฆบางสีขาว 100 %" ทั้ง 4 ภาพจากมือถือ ขณะที่ท้องฟ้าจริงเป็นเมฆบางส่วน
- **ความแม่นยำของ UVI ในวันทดสอบประเมินไม่ได้:** ไม่มีเครื่องวัด UV ภาคพื้นและไม่ได้เทียบกับ Open-Meteo
- **บั๊กที่พบ 4 ตัวแก้แล้ว:** % ของ MED ค้างหลังล็อกจอ, แจ้งเตือนที่เลยเวลาถูกยกเลิก และหน้าหลักแสดงชั่วโมงเก่า (commit `c6b05db`) และเตือนผิวไหม้ข้ามวัน (15:37 ค่าบน 3.0 การ์ดบอก "จะเตือนราว 08:06" ของวันถัดไป, `d2b1762`) ทั้งหมดมีเทส Jest หลังแก้ข้อ 1–3 บนเครื่องจริง 15:37–15:39 % ของ MED เปลี่ยนจาก 0 เป็น 2 % (สูตรได้ 2.6 %) และแจ้งเตือนยังใช้ได้ ส่วนข้อ 4 บนเครื่องจริงไม่ได้จด

## ภาพหน้าจอ
ภาพจากมือถือจริง (Samsung Galaxy S23 Ultra, development build) วันที่ 4 ต.ค. 2026 ตัดแถบสถานะของมือถือออก ปุ่มเฟืองสีเทาที่ลอยอยู่เป็นปุ่มเครื่องมือของ development build ไม่ใช่ส่วนของแอป

| หน้า | ภาพ |
|---|---|
| แบบสอบถามผิว | <img src="docs/screenshots/01_skin_quiz.jpg" width="230"> |
| หน้าหลัก (UVI, ช่วง q10–q90, UVA/UVB, เวลาผิวไหม้) | <img src="docs/screenshots/02_home_uvi_alert.jpg" width="230"> <img src="docs/screenshots/05_uva_uvb_burn_time.jpg" width="230"> |
| กราฟรายชั่วโมง | <img src="docs/screenshots/03_home_hourly_chart.jpg" width="230"> |
| การ์ด "อยู่กลางแจ้ง" (ออกแดด / ทาครีมแล้ว) ภาพ 10:33 ก่อนแก้บั๊ก % ค้าง | <img src="docs/screenshots/04_sun_session.jpg" width="230"> |
| ถ่ายท้องฟ้า | <img src="docs/screenshots/06_sky_camera.jpg" width="230"> |
| วัดแสง (Android) | <img src="docs/screenshots/07_lux.jpg" width="230"> |
| ตั้งค่า + ความยินยอม | <img src="docs/screenshots/08_settings_consent.jpg" width="230"> |
| การแจ้งเตือน | <img src="docs/screenshots/09_notifications_reapply_burn.jpg" width="360"><br><img src="docs/screenshots/10_notification_uv_down.jpg" width="360"> |

## ข้อจำกัด
1. **พื้นที่เดียว:** ฝึกและทดสอบด้วยข้อมูลปทุมธานีที่เดียว และ test มีปีเดียว (2025) ความแม่นยำที่อื่นยังไม่ได้ประเมิน
2. **ไม่มีเครื่องวัดภาคพื้นดิน:** ground truth เป็น NASA POWER (ดาวเทียม/แบบจำลอง) โมเดลรับ bias ต่ำมาด้วย คือวันฟ้าเปิดต่ำกว่า TEMIS 1.36 UVI การเตือนจึงอาจบอกค่าสูงสุดต่ำกว่าจริง `[docs/results_summary.md §6]`
3. **โมเดลท้องฟ้ายังไม่ได้วัดผลกับภาพจากมือถือ** ภาพนอกการกระจายของข้อมูลฝึกยังได้ความมั่นใจ 100 % (ทดสอบ 1 ต.ค.) และภาพจากมือถือทั้ง 4 ภาพได้ "เมฆบางสีขาว 100 %" ขณะที่ท้องฟ้าวันที่ 4 ต.ค. เป็นเมฆบางส่วน (จำนวนภาพน้อยเกินจะสรุป) `[ROADMAP.md วัน 20]`
4. **การแจ้งเตือน:**
   - push จากเซิร์ฟเวอร์ทดสอบด้วยตัวส่งปลอมใน pytest เท่านั้น การรับบนมือถือจริงต้องใช้ Firebase/FCM (build #2)
   - แอปตรวจว่า push ใช้ได้เฉพาะตอนเปิดแอป
   - ไม่ขอสิทธิ์ `SCHEDULE_EXACT_ALARM` แจ้งเตือนที่ตั้งเวลาไว้จึงมาช้า (Doze / ประหยัดแบตเตอรี่) วันที่ 4 ต.ค. วัดได้ 2–9 นาที เฉลี่ย 5.7 นาที (3 รายการ)
   - ต้องเปิดแอปอย่างน้อยวันละครั้ง เพราะพยากรณ์ในเครื่องมีราว 36 ชม.
   - ปุ่ม "ออกแดด" คิดจากกรณีอยู่กลางแดดเต็มที่ ยังไม่คิดผลของครีมกันแดดและเสื้อผ้า และนับเฉพาะช่วงที่มีแดดของวันที่เริ่ม session ไม่สิ้นสุดเองเมื่อข้ามวัน ผู้ใช้ต้องกด "เข้าร่มแล้ว" เอง
5. **การเตือนระดับรุนแรงมาก:** มีน้อย (23 ชม. ในปี 2025) recall จึงไม่แน่นอน และ precision ต่ำ (0.17) `[docs/results_summary.md §6]`
6. **UVA/UVB:** r กับ OMI ต่ำกว่าเป้า (T4) และ UVB ของ SPECTRL2 ครอบคลุมแค่ 300–315 nm
7. **พยากรณ์:** ข้อมูลฝึกมาจาก Historical Forecast API ซึ่งไม่ใช่พยากรณ์ล่วงหน้า 24 ชม. จริง
8. **แอป:**
   - แบบสอบถามผิว 5 ข้อยังไม่ผ่านการตรวจสอบทางวิชาการ
   - ค่า lux ยังไม่ได้ปรับเทียบและไม่เปลี่ยน UVI
   - ยังไม่มี export CSV และตัวแยก "กลางแดด/ในร่ม"
9. **License:** SWIMCAT-ext และ SWIMSEG ใช้เพื่อการศึกษาและไม่ใช่เชิงพาณิชย์เท่านั้น ([docs/datasets.md](docs/datasets.md))
10. **ไม่ใช่เครื่องมือแพทย์**

รายการเต็มอยู่ใน [docs/results_summary.md](docs/results_summary.md) §6 และ [docs/report.md](docs/report.md) บทที่ 5

## เอกสารเพิ่มเติม
| เอกสาร | เนื้อหา |
|---|---|
| [ROADMAP.md](ROADMAP.md) | แผน 30 วันและบันทึกการตัดสินใจ |
| [report.pdf](report.pdf) | รายงาน (PDF, ไฟล์ส่งงาน) |
| [docs/report.md](docs/report.md) | ร่างรายงาน |
| [docs/architecture.md](docs/architecture.md) | ไดอะแกรมสถาปัตยกรรม (Mermaid) |
| [docs/results_summary.md](docs/results_summary.md) | ผลลัพธ์ทุกตัวเลขพร้อมไฟล์ต้นทาง |
| [docs/uv_guard_presentation.pptx](docs/uv_guard_presentation.pptx) | สไลด์นำเสนอ |
| [docs/uv_guard_field_test_2026-10-04.xlsx](docs/uv_guard_field_test_2026-10-04.xlsx) | บันทึกทดสอบภาคสนาม 4 ต.ค. 2026 |
| [docs/api.md](docs/api.md) · [docs/db.md](docs/db.md) | API และฐานข้อมูล (รวม PDPA) |
| [docs/datasets.md](docs/datasets.md) | dataset ภาพท้องฟ้า, license และการอ้างอิง |
| [source_code/app/README.md](source_code/app/README.md) | การรันแอปและขั้นตอนทดสอบบนมือถือ |
