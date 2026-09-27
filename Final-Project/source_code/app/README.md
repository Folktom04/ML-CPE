# UV Guard — แอป Expo

แอป React Native (Expo SDK 57, TypeScript, Expo Router) ของ UV Guard ข้อความที่ผู้ใช้เห็นเป็นภาษาไทยทั้งหมด

> ค่า UV, ระดับความเสี่ยง, เวลาผิวไหม้ และคำแนะนำเป็นค่าประมาณเพื่อการศึกษาและการเตือนเท่านั้น ไม่ใช่การวินิจฉัยทางการแพทย์

## โครงสร้าง
| ไฟล์ | หน้าที่ |
|---|---|
| `src/app/_layout.tsx` | Stack navigator (Expo Router) |
| `src/app/index.tsx` | หน้าหลัก: เรียก `POST /predict`, สถานะโหลด/ผิดพลาด, ลากลงเพื่อโหลดใหม่, disclaimer |
| `src/components/UVCard.tsx` | การ์ด UV: UVI, ช่วง q10–q90, สีระดับ WHO, แถบเตือนตามค่าบน (q90), เวลาที่ UV กลับสู่ระดับต่ำ |
| `src/components/UvaUvbCard.tsx` | การ์ด UVA / UVB (W/m²), เวลาก่อนผิวไหม้ตามประเภทผิว, คำแนะนำ SPF/PA ตอนกลางวัน และตอนกลางคืนแสดง UV สูงสุดของช่วงกลางวันถัดไปจาก `/forecast` แทนคำแนะนำ |
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

## ทดสอบบนมือถือจริง (Expo Go)
ทดสอบแล้ว 28 ก.ย. 2026 บน Samsung (Android) กับ Expo Go หน้าหลักแสดง UVI, ช่วง q10–q90, UVA/UVB, เวลาผิวไหม้ และ disclaimer ถูกต้อง

1. **API ต้องฟังทุก interface:** รันจาก `Final-Project/`
   ```powershell
   $env:PYTHONPATH = "source_code"
   .venv\Scripts\python.exe -m uvicorn api.main:app --app-dir source_code --host 0.0.0.0 --port 8000
   ```
2. **หา IP ของคอมในวง LAN:** ใช้ `ipconfig` ดูที่ IPv4 Address เช่น `192.168.1.48` มือถือกับคอมต้องอยู่ Wi-Fi วงเดียวกัน
3. **ตรวจจากมือถือก่อน:** เปิด `http://<IP>:8000/health` ใน Chrome บนมือถือ ต้องได้ JSON ถ้าไม่ได้ แปลว่าปัญหาอยู่ที่เครือข่ายหรือ Windows Firewall ไม่ใช่ที่แอป
4. **ตั้ง URL ของ API ให้แอป** เลือกวิธีใดวิธีหนึ่ง:
   - ไฟล์ `source_code/app/.env.local` ใส่ `EXPO_PUBLIC_API_URL=http://<IP>:8000` (git ไม่เก็บไฟล์นี้)
   - หรือตั้งใน **หน้าต่าง PowerShell เดียวกัน**กับที่จะรัน Expo: `$env:EXPO_PUBLIC_API_URL="http://<IP>:8000"` ค่า `$env:` มีผลเฉพาะหน้าต่างนั้น และมีสิทธิ์ก่อนค่าในไฟล์ `.env*`
5. **รัน Expo:** `npx expo start --clear` แล้วสแกน QR ด้วย Expo Go
6. **ตรวจ:** ถ้าขึ้น "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้" ให้ดูบรรทัด "ที่อยู่ที่เรียก" บนหน้าจอ ต้องเป็น `http://<IP>:8000/predict` ถ้ายังเป็น `localhost` แปลว่าแอปไม่ได้รับค่าจากข้อ 4

### เมื่อ Expo Go ใช้ bundle เก่า
อาการคือแก้ URL หรือแก้โค้ดแล้ว แต่ "ที่อยู่ที่เรียก" หรือหน้าจอยังเหมือนเดิม
1. ปิด Expo ทุกหน้าต่างบนคอม (Metro เก่าที่ยังค้างอาจทำให้ตัวใหม่ย้ายไปพอร์ต 8082 แต่มือถือยังเชื่อมกับตัวเก่า)
2. บนมือถือ (Android): **Settings → Apps → Expo Go → Force stop** แล้ว **Storage → Clear cache**
3. รัน `npx expo start --clear` ใหม่ แล้วสแกน QR ใหม่ (อย่าเปิดจากรายการ "Recently opened" ใน Expo Go)
4. ถ้ายังไม่หาย ใน Expo Go กด **Clear data** (ต้องสแกน QR ใหม่หลังจากนั้น)

ส่วน iOS: ปัดปิด Expo Go แล้วเปิดใหม่ ถ้ายังไม่หายให้ลบแอปแล้วติดตั้งใหม่

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
4. การ์ด UVA/UVB มีหน่วย W/m² และเวลาก่อนผิวไหม้ ถ้าเป็นกลางคืนต้องขึ้น "ไม่มีความเสี่ยง (กลางคืน)" ต้องไม่มีคำแนะนำ (เช่น "ใส่แว่นกันแดด") และต้องมีกล่อง "พรุ่งนี้ / วันนี้ UV สูงสุดประมาณ …"
5. ปิด API แล้วโหลดหน้าใหม่: ต้องขึ้น "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ …" พร้อมปุ่ม "ลองใหม่" และ disclaimer ยังอยู่ท้ายหน้า
6. ความกว้างแบบมือถือ (375 px) ต้องไม่มี scroll แนวนอน
