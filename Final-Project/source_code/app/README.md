# UV Guard — แอป Expo

แอป React Native (Expo SDK 57, TypeScript, Expo Router) ของ UV Guard ข้อความที่ผู้ใช้เห็นเป็นภาษาไทยทั้งหมด

> ค่า UV, ระดับความเสี่ยง, เวลาผิวไหม้ และคำแนะนำเป็นค่าประมาณเพื่อการศึกษาและการเตือนเท่านั้น ไม่ใช่การวินิจฉัยทางการแพทย์

## โครงสร้าง
| ไฟล์ | หน้าที่ |
|---|---|
| `src/app/_layout.tsx` | Stack navigator (Expo Router) |
| `src/app/index.tsx` | หน้าหลัก: เรียก `POST /predict`, สถานะโหลด/ผิดพลาด, ลากลงเพื่อโหลดใหม่, disclaimer |
| `src/components/UVCard.tsx` | การ์ด UV: UVI, ช่วง q10–q90, สีระดับ WHO, แถบเตือนตามค่าบน (q90), เวลาที่ UV กลับสู่ระดับต่ำ |
| `src/components/UvaUvbCard.tsx` | การ์ด UVA / UVB (W/m²), เวลาก่อนผิวไหม้ตามประเภทผิว, คำแนะนำ SPF/PA |
| `src/lib/uv.ts` | ระดับ/สี WHO (กฎเดียวกับ `src/metrics.py`) และการจัดรูปแบบข้อความ |
| `src/api/` | type ให้ตรงกับ `source_code/api/schemas.py` และ `fetchPredict()` |
| `src/config.ts` | ที่อยู่ API, ตำแหน่งเริ่มต้น (ปทุมธานี), ประเภทผิวเริ่มต้น (III) |

ตำแหน่งจริงจาก GPS และการเลือกจังหวัดเป็นงานวัน 21 ส่วนแบบสอบถามประเภทผิวเป็นงานวัน 19 ตอนนี้แอปจึงใช้ค่าเริ่มต้นไปก่อน

## รัน
1. รัน API ที่ `Final-Project/` (ดู `docs/api.md`)
2. ในโฟลเดอร์นี้:
   ```powershell
   npm install
   copy .env.example .env   # ถ้าต้องเปลี่ยน EXPO_PUBLIC_API_URL
   npx expo start --web     # เปิด http://localhost:8081
   ```
- **มือถือจริง (Expo Go):** ตั้ง `EXPO_PUBLIC_API_URL=http://<IP ของคอมใน LAN>:8000` และรัน API ด้วย `--host 0.0.0.0` เพราะบนมือถือ `localhost` หมายถึงตัวมือถือเอง
- **CORS:** API อนุญาต `http://localhost:8081` และ `http://127.0.0.1:8081` เป็นค่าเริ่มต้น ถ้าจะใช้ origin อื่นให้ตั้ง `CORS_ORIGINS` ใน `.env` ของ API

## ทดสอบ
```powershell
npm test              # Jest (jest-expo + @testing-library/react-native)
npm run typecheck     # tsc --noEmit
npx expo lint
npx expo export --platform web
```

## รายการตรวจหน้าจอ (สำหรับ browser agent ของ Antigravity)
เปิด `npx expo start --web` โดยให้ API รันอยู่ แล้วตรวจ:
1. หัวข้อ "UV Guard" และบรรทัด "ปทุมธานี (ตำแหน่งเริ่มต้น) · ผิวประเภท III"
2. การ์ด UV: ตัวเลข UVI ใหญ่ ป้ายระดับเป็นภาษาไทย สีป้ายตรง WHO (ต่ำ #3E9B4F, ปานกลาง #D9A400 ตัวอักษรสีเข้ม, สูง #E36B12, สูงมาก #D22F3A, รุนแรงมาก #8A3FC2) และมีบรรทัดช่วง q10–q90
3. ถ้าระดับ q90 สูงกว่าระดับที่แสดง ต้องมีแถบ "เตือนตามค่าบน (q90) …"
4. การ์ด UVA/UVB มีหน่วย W/m² และเวลาก่อนผิวไหม้ ถ้าเป็นกลางคืนต้องขึ้น "ไม่มีความเสี่ยง (กลางคืน)"
5. ปิด API แล้วโหลดหน้าใหม่: ต้องขึ้น "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ …" พร้อมปุ่ม "ลองใหม่" และ disclaimer ยังอยู่ท้ายหน้า
6. ความกว้างแบบมือถือ (375 px) ต้องไม่มี scroll แนวนอน
