# UV Guard: สถาปัตยกรรมระบบ (วัน 28)

ไดอะแกรมเขียนด้วย Mermaid (GitHub แสดงผลเอง) ชื่อไฟล์และโมดูลตรงกับโค้ดใน repo ส่วนรายละเอียดของแต่ละขั้นอยู่ใน `ROADMAP.md`, `docs/api.md`, `docs/db.md` และ `source_code/app/README.md`

## 1. ภาพรวม: ข้อมูล → โมเดล → API/DB → แอป → การแจ้งเตือน

```mermaid
flowchart LR
  subgraph DATA["1. ข้อมูล"]
    OMH["Open-Meteo Historical Forecast<br/>+ Air Quality (ตอนฝึก)"]
    NASA["NASA POWER hourly RE<br/>UVI / UVA / UVB (target)"]
    VAL["TEMIS + OMI OMUVBd<br/>(ทดสอบเท่านั้น)"]
    SKY["CCSN / SWIMCAT-ext / SWIMSEG<br/>(dataset ภาพสาธารณะ)"]
  end

  subgraph TRAIN["2. ฝึกโมเดล (offline, source_code/src)"]
    PRE["preprocess + features<br/>23 features"]
    PHY["physics: Madronich UVI<br/>SPECTRL2 UVA/UVB<br/>ozone_climatology_v2"]
    CMF["target CMF = NASA / ฟ้าใส"]
    XGB["XGBoost multi-output<br/>cmf_multi_xgb_final"]
    QR["quantile XGBoost + CQR<br/>cmf_uvi_quantile_xgb_final<br/>cqr_q_final_v1"]
    CNN["MobileNetV3Small<br/>sky_cnn_v1.tflite<br/>sky_cloud_v1.tflite"]
    EVAL["evaluate_test (ครั้งเดียว)<br/>test 2025"]
  end

  subgraph SERVER["3. API + DB (source_code/api)"]
    API["FastAPI<br/>/predict /forecast /sky-image<br/>/users /push-token /health"]
    INF["inference: features สด<br/>× CMF → UVI + q10–q90"]
    RISK["risk: ระดับ WHO, MED,<br/>เวลาผิวไหม้ (alert_uvi)"]
    SCHED["APScheduler ทุก 30 นาที<br/>src/push.py"]
    DB[("PostgreSQL<br/>users, push_tokens,<br/>measurements, notifications_log")]
  end

  OMF["Open-Meteo Forecast<br/>+ Air Quality (ตอนใช้งาน)"]

  subgraph APP["4. แอป Expo (source_code/app)"]
    UI["หน้าหลัก / กราฟ / ตั้งค่า<br/>onboarding / แบบสอบถามผิว"]
    CAM["กล้องถ่ายท้องฟ้า<br/>(re-encode, ไม่มี EXIF)"]
    LUX["วัดแสง + ทิศทาง<br/>(Android)"]
    STORE["AsyncStorage<br/>การตั้งค่าในเครื่อง"]
  end

  subgraph NOTI["5. การแจ้งเตือน"]
    LOCAL["local notification<br/>expo-notifications (DATE trigger)"]
    PUSH["Expo Push Service<br/>→ FCM → มือถือ"]
  end

  OMH --> PRE --> XGB
  NASA --> CMF
  PHY --> CMF --> XGB
  CMF --> QR
  PRE --> QR
  SKY --> CNN
  XGB --> EVAL
  QR --> EVAL
  VAL -. "ทดสอบเท่านั้น" .-> EVAL

  XGB -- "โหลดครั้งเดียวตอนเริ่ม" --> INF
  QR --> INF
  CNN --> API
  OMF --> INF --> RISK --> API
  API <--> DB
  SCHED --> INF
  SCHED <--> DB
  SCHED --> PUSH

  UI -- "POST /predict, GET /forecast" --> API
  CAM -- "POST /sky-image (ไม่เก็บภาพ)" --> API
  UI -- "users / settings / push-token<br/>(เฉพาะเมื่อยินยอม)" --> API
  LUX --> UI
  STORE <--> UI
  UI -- "useLocalNotifications" --> LOCAL
  PUSH --> UI
```

**หลักที่ไดอะแกรมนี้ยึดไว้** `[.agents/rules/00-project-context.md]`
- **NASA POWER ใช้เป็น target ตอนฝึกเท่านั้น** ไม่ใช่ feature และไม่ถูกเรียกตอนใช้งาน ตอนใช้งานใช้ Open-Meteo Forecast ตัวแปรชุดเดียวกับตอนฝึก
- **TEMIS/OMI ใช้ทดสอบเท่านั้น** (เส้นประ) ปี 2023 ใช้เลือกแหล่ง target และปี 2025 เป็น test
- **CNN เป็นโมดูลแยก:** ไม่ได้ต่อเข้า `INF` และไม่เปลี่ยนค่า UVI
- **ค่า lux ไม่ถูกส่งไปเซิร์ฟเวอร์** และไม่เปลี่ยนค่า UVI

## 2. คำขอ `/predict` (ตอนใช้งาน)

```mermaid
sequenceDiagram
  autonumber
  participant App as แอป Expo
  participant API as FastAPI
  participant OM as Open-Meteo Forecast + Air Quality
  participant M as โมเดล (โหลดตอนเริ่ม)
  App->>API: POST /predict {lat, lon (ปัด 0.01°), skin_type}
  alt นอกกรอบประเทศไทย
    API-->>App: 422 "รองรับเฉพาะพื้นที่ประเทศไทย" (ไม่เรียก Open-Meteo)
  else ในประเทศไทย
    API->>OM: weather + air quality รายชั่วโมง
    OM-->>API: ข้อมูล (หาย ≤ 3 ชม. → interpolate + data_imputed)
    API->>M: build_features (23) → CMF + q10/q90
    M-->>API: UVI = ฟ้าใส × CMF, ช่วง [q10 − Q, q90 + Q]
    API->>API: alert_uvi = max(q90, ค่าเดี่ยว) → risk.assess
    API-->>App: uvi, uvi_range, uva/uvb, level, burn_minutes, advice, forecast, note, disclaimer
  end
```
`[docs/api.md]`, `[ROADMAP.md วัน 16, 21]`

## 3. การแจ้งเตือน: local หรือ push

```mermaid
flowchart TD
  F["ได้พยากรณ์ใหม่ / เปลี่ยนการตั้งค่า"] --> A{"notificationsAvailable()?"}
  A -- "ไม่ (เว็บ / Expo Go Android)" --> S["แสดงเวลาบนจอเท่านั้น<br/>พร้อมบอกเหตุผล"]
  A -- "ใช่ (development build)" --> P{"pushActive?<br/>ยินยอม + จังหวัด + token 200<br/>+ /health push_scheduler"}
  P -- "ใช่" --> SV["เซิร์ฟเวอร์ส่ง 'UV สูง' / 'ปลอดภัยแล้ว'<br/>ทุก 30 นาที ตามจังหวัด"]
  P -- "ไม่" --> L1["local 'UV สูง' / 'ปลอดภัยแล้ว'<br/>q90 ถึงเกณฑ์ · hysteresis เกณฑ์ − 2<br/>cooldown 3 ชม. · ไม่เตือนกลางคืน"]
  A -- "ใช่" --> L2["local เสมอ: สรุป 07:00,<br/>ออกแดด 80 % MED, ทาครีมซ้ำ 2 ชม."]
  SV --> LOG[("notifications_log")]
```
`[ROADMAP.md วัน 22–23]`, `[source_code/app/README.md]`

**ข้อจำกัดของการแจ้งเตือน:**
- ไม่ขอสิทธิ์ `SCHEDULE_EXACT_ALARM` แจ้งเตือนที่ตั้งเวลาไว้จึงอาจมาช้า
- push จากเซิร์ฟเวอร์ทดสอบด้วยตัวส่งปลอมเท่านั้น การรับบนมือถือจริงต้องใช้ build ที่มี FCM
- แอปตรวจ `pushActive` เฉพาะตอนเปิดแอป
