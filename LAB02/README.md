# LAB01 — AI Student Impact Dataset: Dataset Exploration

การสำรวจข้อมูลผลกระทบของ Generative AI ต่อผลการเรียนและความเป็นอยู่ที่ดีของนักเรียน (50,000 คน / 16 คุณลักษณะ)

## 📂 โครงสร้างไฟล์

```
LAB01/
├── LAB1_code.ipynb   # โค้ด Python (pandas) สำหรับสำรวจข้อมูล พร้อมผลลัพธ์การรันจริง
├── dataset.csv        # ชุดข้อมูลต้นฉบับ (50,000 แถว x 16 คอลัมน์)
├── report.pdf          # รายงานสรุปผลการสำรวจข้อมูล พร้อมกราฟประกอบ
└── README.md           # เอกสารอธิบายโปรเจกต์ (ไฟล์นี้)
```

## 🎯 เป้าหมายของ LAB นี้

ฝึกทักษะการสำรวจข้อมูลเบื้องต้น (Exploratory Data Analysis) ก่อนนำไปวิเคราะห์เชิงลึกหรือสร้างแบบจำลอง โดยครอบคลุม:

- โหลดและตรวจสอบขนาด/ชนิดข้อมูล (shape, dtypes)
- คำนวณสถิติเชิงสรุป (summary statistics)
- ตรวจสอบค่าที่ขาดหายไปและข้อมูลซ้ำ (missing values, duplicates)
- ตรวจสอบการกระจายตัวของตัวแปรหมวดหมู่ (class distribution)

## 🗂️ เกี่ยวกับชุดข้อมูล (`dataset.csv`)

| กลุ่มคุณลักษณะ | คอลัมน์ตัวอย่าง |
|---|---|
| ตัวระบุ | `Student_ID` |
| ประวัติทางวิชาการ | `Major_Category`, `Year_of_Study`, `Pre_Semester_GPA`, `Post_Semester_GPA` |
| พฤติกรรมการใช้ AI | `Weekly_GenAI_Hours`, `Primary_Use_Case`, `Prompt_Engineering_Skill`, `Tool_Diversity`, `Paid_Subscription` |
| พฤติกรรมการเรียน | `Traditional_Study_Hours`, `Perceived_AI_Dependency` |
| บริบทของสถาบัน | `Institutional_Policy` |
| สุขภาพจิต/ความเป็นอยู่ที่ดี | `Anxiety_Level_During_Exams`, `Skill_Retention_Score`, `Burnout_Risk_Level` |

**ขนาดข้อมูล:** 50,000 แถว × 16 คอลัมน์ — ไม่มีค่าที่ขาดหายไป และไม่มีข้อมูลซ้ำ

## ▶️ วิธีใช้งาน

```bash
git clone <ลิงก์ repository นี้>
cd LAB01
pip install pandas numpy matplotlib seaborn jupyter
jupyter notebook LAB1_code.ipynb
```

## 📄 รายงานผล

ดูสรุปผลการสำรวจข้อมูลแบบละเอียด พร้อมกราฟและตาราง ได้ที่ [`report.pdf`](./report.pdf)

## 🔜 ขั้นตอนถัดไป

- **LAB 2:** Data Visualization (Histogram, Correlation Heatmap)
- **Part 3:** Data Cleaning (Missing Value Handling, Duplicate Removal, Incorrect Data Correction, Data Type Conversion, Mean vs Median)
- **Part 4:** Feature Engineering (Label Encoding, One-Hot Encoding)
