# UV Guard ☀️

ระบบ Machine Learning ประเมินรังสี UV (UVI, UVA, UVB) ณ ตำแหน่งผู้ใช้ แปลงเป็นความเสี่ยงต่อผิวตามประเภทผิว (Fitzpatrick I–VI) และเตือนผ่านแอปมือถือ

> **ข้อจำกัดความรับผิดชอบ:** ค่า UV, ระดับความเสี่ยง, เวลาผิวไหม้ และคำแนะนำทั้งหมดเป็นค่าประมาณเพื่อการศึกษาและการเตือนภัยทั่วไปเท่านั้น ไม่ใช่การวินิจฉัยหรือคำแนะนำทางการแพทย์ หากมีปัญหาผิวหนังควรปรึกษาแพทย์

> **พื้นที่ใช้งาน:** โมเดลฝึกและทดสอบด้วยข้อมูลของ**ปทุมธานีเท่านั้น** (NASA POWER จุดเดียว, ozone climatology ของจุดนั้น) แอปใช้ GPS หรือเลือกจังหวัดได้ทั่วประเทศ แต่ถ้าตำแหน่งห่างจากปทุมธานีเกิน ~50 กม. ความแม่นยำยังไม่ได้ประเมิน และหน้าหลักจะขึ้นหมายเหตุ "ความแม่นยำนอกพื้นที่ปทุมธานียังไม่ได้ประเมิน" API รองรับเฉพาะพื้นที่ประเทศไทย (นอกกรอบประเทศไทยตอบ 422) รายละเอียดอยู่ใน `docs/results_summary.md` ข้อจำกัดข้อ 9

> **การแจ้งเตือน (วัน 22):** เป็น local notification ที่ตั้งเวลาล่วงหน้าจากพยากรณ์ในเครื่อง (ไม่ต้องยินยอม ไม่ส่งข้อมูลออก) ข้อจำกัด: (1) ต้องเปิดแอปอย่างน้อยวันละครั้ง เพราะพยากรณ์ในเครื่องมีประมาณ 36 ชม. และ Expo Go รันงานเบื้องหลังเองไม่ได้ วันที่ไม่มีพยากรณ์จะได้แจ้งเตือน "เปิดแอปเพื่อดู UV วันนี้" ตอน 07:00 แทน (0) **บน Android ต้องใช้ development build:** `expo-notifications` 57 throw ตั้งแต่ตอน import ใน Expo Go Android แอปจึงปิดการแจ้งเตือนเองใน Expo Go Android และบอกเหตุผลในหน้าตั้งค่า ส่วนอื่นของแอปยังใช้ได้ (1b) **การแจ้งเตือนจากเซิร์ฟเวอร์ (วัน 23)** "UV สูง" / "ปลอดภัยแล้ว" ทุก 30 นาทีตามจังหวัด ต้องยินยอมและใช้ development build แอปตรวจว่าใช้ได้ตอนเปิดแอป ถ้าเซิร์ฟเวอร์ปิดหลังจากนั้น push จะไม่มาจนกว่าจะเปิดแอปครั้งถัดไป (2) **Android อาจส่งแจ้งเตือนช้ากว่าเวลาที่ตั้ง** เพราะ Doze / โหมดประหยัดแบตเตอรี่ (แอปขอใช้ exact alarm ไม่ได้ใน Expo Go) (3) เตือนก่อนผิวไหม้จากปุ่ม "ออกแดด" คิดจากกรณีอยู่กลางแดดเต็มที่และใช้ค่าบนของ UV ถ้าอยู่ในร่มบ้าง เวลาจริงจะนานกว่านี้ และยังไม่ได้คิดผลของครีมกันแดดหรือเสื้อผ้า ทุกข้อความแจ้งเตือนมีคำว่า "ประมาณ"

## Architecture
GPS / เวลา / Open-Meteo (weather + air quality) → Feature Engineering → Clear-sky physics (UVI: Madronich, UVA/UVB: pvlib SPECTRL2) × CMF จาก **XGBoost multi-output** → ช่วง q10–q90 (quantile XGBoost + CQR) → Risk Engine (ระดับ WHO, เวลาผิวไหม้ใช้ค่าบน) → FastAPI → Expo App + Notifications

- **Ground truth:** NASA POWER hourly (community RE) `ALLSKY_SFC_UV_INDEX`, `ALLSKY_SFC_UVA`, `ALLSKY_SFC_UVB` ซึ่งเป็นข้อมูลดาวเทียม/แบบจำลอง **ไม่ได้ใช้เครื่องวัด UV จริง** NASA POWER ใช้เป็น target ตอนฝึกเท่านั้น ไม่ใช่ feature
- **Features:** Open-Meteo Historical Forecast API + Air Quality API (ตอนฝึก) และ Forecast API ตัวแปรชุดเดียวกัน (ตอนใช้งาน) รวมกับเรขาคณิตดวงอาทิตย์และเวลา
- **พยากรณ์ 6–24 ชม.:** ใช้ XGBoost ตัวเดียวกัน LSTM ทดลองแล้วไม่ผ่านเกณฑ์ (วัน 12)
- **CNN ภาพท้องฟ้า:** โมดูลแยก **ไม่ได้ stack กับ XGBoost และไม่ปรับค่า UVI** แอปแสดงเฉพาะชนิดท้องฟ้าจาก SWIMCAT-ext (6 คลาส + ความมั่นใจ) สัดส่วนเมฆจากอัตราส่วนสีแดง/น้ำเงิน และสัดส่วนเมฆในภาพจาก head ที่ฝึกบน SWIMSEG (ผ่านเกณฑ์: MAE 0.084 เทียบกับวิธีสี 0.145 บนชุดทดสอบ) เป็นข้อมูลประกอบเท่านั้น ฝึกจาก dataset สาธารณะ CCSN, SWIMCAT-ext (ภาพที่เก็บจากอินเทอร์เน็ต) และ SWIMSEG (Dev, Lee & Winkler 2017, CC BY-NC 4.0, ภาพจากกล้องถ่ายท้องฟ้าที่สิงคโปร์) ค่าสัดส่วนเมฆเป็นของ**ภาพที่ถ่าย ไม่ใช่ทั้งท้องฟ้า**
- ระบบใช้ **สมาร์ทโฟนเครื่องเดียว** ไม่มีเซนเซอร์หรือโมดูลเสริม

ผลลัพธ์ทุกตัวเลขพร้อมไฟล์ต้นทางอยู่ใน [docs/results_summary.md](docs/results_summary.md)

## Structure
| Folder | Content |
|---|---|
| `source_code/src/` | ดึงข้อมูล, ฟิสิกส์, features, การฝึก, risk engine, ฐานข้อมูล |
| `source_code/tests/` | pytest |
| `source_code/notebooks/` | EDA และการทดลอง (01–14) |
| `source_code/models/` | โมเดลที่บันทึกไว้ + `*_metrics.json` |
| `source_code/api/` | FastAPI service (`docs/api.md`) |
| `source_code/migrations/` | Alembic migrations (`docs/db.md`) |
| `source_code/app/` | แอป Expo (React Native, TypeScript) |
| `dataset/` | `raw/`, `processed/`, `validation/`, `sky/` (ไม่อยู่ใน git) และ `field/` ข้อมูลภาคสนามจากมือถือ |
| `docs/` | เอกสาร, รูป, ผลลัพธ์ |

## ติดตั้ง
ต้องใช้ **Python 3.12**, PostgreSQL (ทดสอบบน 18.6) และ Node.js (สำหรับแอป)

```powershell
# Windows PowerShell (จากโฟลเดอร์ Final-Project)
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # แล้วแก้ค่าใน .env (ห้าม commit .env)
```
macOS / Linux: `python3.12 -m venv .venv && source .venv/bin/activate`

ค่าใน `.env`:
- `DATABASE_URL`: PostgreSQL หลัก ถ้าไม่ตั้งจะใช้ SQLite fallback พร้อม WARNING
- `TEST_DATABASE_URL`: ฐานข้อมูลทดสอบ ชื่อต้องมีคำว่า `test` เพราะเทสจะลบตารางทั้งหมด
- `EARTHDATA_USERNAME` / `EARTHDATA_PASSWORD`: ใช้ดาวน์โหลด OMI เท่านั้น

วิธีติดตั้ง PostgreSQL และสร้างฐานข้อมูลอยู่ใน [docs/db.md](docs/db.md)

### เมื่อ Windows Smart App Control บล็อก DLL ใน `.venv`
อาการ: `ImportError: DLL load failed ... An Application Control policy has blocked this file.` (เช่น `pandas/_libs/join`, `sklearn`, `psycopg_binary.libs/libpq`) ทำให้ `pytest` หรือการต่อ PostgreSQL ใช้ไม่ได้

**อย่าปิด Smart App Control** (ปิดแล้วเปิดกลับไม่ได้ถ้าไม่ reset Windows) ให้ติดตั้งแพ็กเกจที่โดนบล็อกใหม่ **ด้วยเวอร์ชันเดิม** ก่อน:
```powershell
.venvScriptspython.exe -m pip list                 # ดูเวอร์ชันที่ใช้อยู่
.venvScriptspython.exe -m pip install --force-reinstall --no-cache-dir --no-deps <package>==<เวอร์ชันเดิม>
.venvScriptspython.exe -c "import pandas, sklearn, psycopg; print('ok')"
```
- ต้องใส่ `--no-deps` ไม่อย่างนั้น pip จะลง numpy / scipy รุ่นล่าสุดตามมาด้วย (ข้าม `scipy<1.18`) ซึ่งอาจทำให้ผลโมเดลเปลี่ยน
- 28 ก.ย. 2026: pandas 3.0.6, scikit-learn 1.9.1 และ psycopg-binary 3.3.6 โดนบล็อก พอติดตั้งเวอร์ชันเดิมใหม่ก็ใช้ได้ (numpy/scipy ไม่เปลี่ยน) ทั้งที่ isort ซึ่งไม่ได้ติดตั้งใหม่ก็กลับมาโหลดได้เอง จึงน่าจะเกิดจากการตรวจชื่อเสียงไฟล์ของ SAC ล้มเหลวชั่วคราว
- ถ้ายังโดนบล็อก ให้ลองเวอร์ชันใกล้เคียง 1 รุ่น (แบบ `scipy<1.18` ใน `requirements.txt`) ถ้าเปลี่ยนเวอร์ชัน ต้องรัน `pytest` เพื่อยืนยันว่าผลโมเดลไม่เปลี่ยน

## รัน
ทุกคำสั่งรันจาก `Final-Project/`

**เทส**
```powershell
pytest -q
```

**ฐานข้อมูล**
```powershell
alembic upgrade head
```

**API** (http://127.0.0.1:8000/docs)
```powershell
$env:PYTHONPATH = "source_code"
.venv\Scripts\python.exe -m uvicorn api.main:app --app-dir source_code --port 8000
```
Endpoint ทั้งหมดอธิบายไว้ใน [docs/api.md](docs/api.md)

**สร้างข้อมูลและโมเดลใหม่ (ไม่จำเป็นถ้าจะแค่รัน API)** ให้ตั้ง `$env:PYTHONPATH = "source_code"` ก่อน แล้วรันตามลำดับ:
1. `python -m src.fetch_data` ดาวน์โหลด Open-Meteo และ NASA POWER แล้ว cache ไว้ที่ `dataset/raw/`
2. `python -m src.preprocess` แล้ว `python -m src.features` สร้าง `dataset/processed/train.parquet`
3. `python -m src.train_cmf`, `python -m src.train_multi`, `python -m src.tune` และ `python -m src.quantile` ฝึกและเลือกโมเดลด้วย train 2023 / dev 2024
4. `python -m src.sky_data --download --index` แล้ว `python -m src.sky_cnn --train` สำหรับ CNN ภาพท้องฟ้า

> **ห้ามรันซ้ำ:** `src.evaluate_test --run`, `src.lstm --test` และ `src.sky_cnn --test` เปิด test split (ปี 2025 / test ของภาพ) ได้ **ครั้งเดียว** และรันไปแล้ว ผลอยู่ใน `docs/` ส่วน `src.fetch_validation` ใช้ข้อมูล TEMIS/OMI เพื่อ validation เท่านั้น

**แอป** (ตั้งแต่วัน 18) รันจาก `source_code/app/`
```powershell
npm install
npx expo start --web
```
ถ้าจะเปิดบนมือถือด้วย Expo Go ให้ตั้ง `EXPO_PUBLIC_API_URL` เป็น IP ของคอมในวง LAN

ดูแผนงานทั้งหมดใน [ROADMAP.md](ROADMAP.md)
