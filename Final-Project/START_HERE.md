# เริ่มโปรเจกต์ UV Guard (Antigravity + Claude Code)

โปรเจกต์นี้ใช้เครื่องมือสองตัวในโฟลเดอร์เดียวกัน

| งาน | ใช้ตัวไหน |
|---|---|
| Phase 1–3: ข้อมูล, ฟิสิกส์, ML | **Claude Code** |
| Phase 4: FastAPI, ฐานข้อมูล | **Claude Code** |
| Phase 4: หน้าจอแอป Expo | **Antigravity** (browser agent ดูหน้าจอ + ถ่ายภาพ) |
| Phase 5: แจ้งเตือน | Claude Code เขียนโค้ด, ทดสอบบนมือถือจริงด้วยตัวเอง |
| quota ฝั่งไหนหมด | สลับไปใช้อีกฝั่ง ทั้งคู่อ่าน ROADMAP.md เดียวกัน |

กติกาเขียนไว้ที่เดียวคือ `.agents/rules/` แล้ว `CLAUDE.md` ดึงไปใช้ ถ้าจะแก้กติกา ให้แก้ใน `.agents/rules/` เท่านั้น

## 1. เปิดโปรเจกต์
โปรเจกต์อยู่ที่ `C:\Users\folkt\ML-CPE\Final-Project` ซึ่งอยู่ใน repo `ML-CPE` เดิม **ไม่ต้อง `git init` ใหม่**

1. ใน Antigravity เลือก **Open Folder** → เลือก `ML-CPE\Final-Project` (ต้องเปิดโฟลเดอร์นี้ ไม่ใช่ `ML-CPE` เพราะ rules อยู่ที่ระดับนี้)
2. เปิด Terminal แล้ว commit โครงโปรเจกต์:
   ```powershell
   git add .
   git commit -m "day 0: UV Guard project scaffold"
   git push
   ```

## 2. ตรวจว่า Antigravity อ่าน Rules และ Workflows แล้ว
เปิดเมนู **Customizations** (ปุ่ม `...` บนแผง Agent) จะเห็นรายการดังนี้

| ไฟล์ | ประเภท | ทำงานเมื่อ |
|---|---|---|
| `.agents/rules/00-project-context.md` | Rule | ทุกครั้ง (Always on) |
| `.agents/rules/10-python-ml.md` | Rule | แก้ไฟล์ `.py` / `.ipynb` |
| `.agents/rules/20-api-and-app.md` | Rule | แก้ไฟล์ใน `source_code/api/` หรือ `source_code/app/` |
| `.agents/workflows/day.md` | Workflow | พิมพ์ `/day` |
| `.agents/workflows/checkpoint.md` | Workflow | พิมพ์ `/checkpoint` |
| `.agents/workflows/status.md` | Workflow | พิมพ์ `/status` |

ถ้า rule ไหนไม่ขึ้นโหมดตามตาราง ให้ตั้งค่าโหมดเองในหน้า Customizations
(Antigravity เวอร์ชันเก่าใช้โฟลเดอร์ `.agent/` ไม่มี s ถ้าไม่เห็นไฟล์ ให้เปลี่ยนชื่อโฟลเดอร์)

## 2.5 ตั้งค่า Claude Code
1. ติดตั้ง Claude Code (ต้องมีแพ็กเกจ Claude Pro ขึ้นไป) ตามคู่มือที่ docs.claude.com
2. สร้าง venv ก่อน เพื่อให้ hook รันเทสด้วย Python ของโปรเจกต์:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   source .venv/bin/activate     # macOS / Linux
   pip install -r requirements.txt
   ```
3. เปิด Terminal ใน Antigravity (ที่โฟลเดอร์ `Final-Project`) แล้วพิมพ์ `claude`
4. พิมพ์ `/memory` เพื่อตรวจว่าโหลด `CLAUDE.md` และไฟล์ rules ทั้ง 3 ไฟล์แล้ว
5. ครั้งแรกจะมีคำถามให้ยืนยันว่าเชื่อถือ hook ของโปรเจกต์ ให้ตอบยอมรับ

สิ่งที่ตั้งไว้ใน `.claude/`
- `commands/day.md`, `status.md`, `checkpoint.md` → คำสั่ง `/day 1`, `/status`, `/checkpoint` เหมือนฝั่ง Antigravity
- `hooks/run_tests.py` → ทุกครั้งที่ Claude แก้ไฟล์ใน `source_code/src/` หรือ `source_code/tests/` จะรัน pytest อัตโนมัติ ถ้าเทสพัง Claude จะต้องแก้ก่อนไปต่อ
- `settings.json` → อนุญาตให้รัน pytest และคำสั่ง git แบบอ่านอย่างเดียวได้เลยโดยไม่ต้องถาม และห้ามอ่านไฟล์ `.env`

แนะนำให้กด **Shift+Tab** เข้า Plan mode ก่อนสั่ง `/day` จะได้เห็นแผนก่อนที่ Claude จะแก้ไฟล์

**กันสองตัวชนกัน:** อย่าสั่งงานทั้งสองตัวพร้อมกันในไฟล์เดียวกัน ทำเสร็จฝั่งหนึ่งแล้ว commit ก่อนสลับ

## 3. ตั้งค่า Agent ของ Antigravity ที่แนะนำ
- **โหมด:** Planning (ให้ agent เขียนแผนก่อนลงมือ) ใช้ Fast เฉพาะงานแก้เล็ก ๆ
- **Terminal execution:** ตั้งให้ agent ขออนุญาตก่อนรันคำสั่ง (อย่างน้อยช่วงแรก) จะได้เห็นว่ามันติดตั้งอะไรลงเครื่อง
- **ตรวจงานทุกครั้ง:** อ่าน Implementation Plan ก่อนกดอนุมัติ และอ่าน Walkthrough ตอนจบ ถ้าไม่เข้าใจโค้ดส่วนไหน ให้ถาม agent ก่อนไปวันถัดไป เพราะต้องอธิบายตอนนำเสนอได้

## 4. ใช้งานประจำวัน
พิมพ์ในแผง Agent:

```
/day 1
```

agent จะอ่าน `ROADMAP.md` → เสนอแผนเป็นภาษาไทย → รอคุณอนุมัติ → เขียนโค้ด → รันเทส → ติ๊ก ROADMAP → commit → สรุปงาน

คำสั่งอื่น:
- `/status` ดูว่าตามแผนหรือช้ากว่ากี่วัน
- `/checkpoint` ตรวจ checkpoint ของ phase (วัน 5, 10, 15, 21, 24)

## 5. Prompt เสริมสำหรับวันที่ยาก
ใช้ต่อท้าย `/day N` หรือพิมพ์แยกเมื่อ agent ติด

**วัน 1 (ข้อมูล)**
> ก่อนเขียนสคริปต์ ให้ทดสอบเรียก Open-Meteo 1 วันก่อน เพื่อยืนยันว่า API ไหนมี uv_index และ uv_index_clear_sky ย้อนหลังได้ (ลอง Air Quality API และ Historical Forecast API) แล้วสรุปให้ดูว่าได้ย้อนหลังถึงวันไหน

**วัน 4 (UVA/UVB)**
> ตรวจผล spectrl2 ด้วยการเทียบ UVA/UVB ตอนเที่ยงวันฟ้าใสที่ปทุมธานีกับค่าในงานวิจัย และบอกว่าค่าอยู่ในช่วงที่สมเหตุสมผลหรือไม่

**วัน 13 (CNN)**
> ใช้เฉพาะ dataset สาธารณะ (CCSN, SWIMCAT, SWIMSEG, SKIPP'D / CloudCV) ไม่มีภาพถ่ายเอง ถ้าดาวน์โหลด dataset ไหนไม่ได้หรือ license ไม่อนุญาต ให้หยุดแล้วเสนอ dataset ทดแทนก่อน อย่าสร้างภาพปลอมหรือ label เอง และสรุปผลแยกตาม dataset ให้เห็นว่าโมเดลทำงานกับภาพกล้องธรรมดา (CCSN) ต่างจากภาพ fisheye แค่ไหน

**วัน 18–21 (แอป)**
> ใช้ browser agent ทดสอบหน้าจอผ่าน `npx expo start --web` ได้ แต่แจ้งเตือนและเซนเซอร์ต้องทดสอบบนมือถือจริง บอกขั้นตอนที่ฉันต้องทำเองบนมือถือ

## 6. ข้อควรระวัง
- **อย่าให้ agent ข้ามวัน:** ถ้างานวันนี้ยังไม่ผ่านเทส อย่าเริ่มวันถัดไป
- **ระวังผลลัพธ์ที่ดีเกินจริง:** ถ้า MAE ต่ำผิดปกติ (เช่น < 0.1) มักเป็น data leakage ให้สั่ง `/checkpoint` ตรวจซ้ำ
- **Quota โมเดล:** งานยาว ๆ อาจใช้ quota หมด แบ่งงานเป็นวันละหลายรอบสั้น ๆ ได้ agent จะอ่านต่อจาก ROADMAP ที่ติ๊กไว้
- **ข้อมูลส่วนตัว:** push token และตำแหน่งผู้ใช้เก็บเฉพาะในฐานข้อมูลของคุณ อย่า commit ไฟล์ `.env`
