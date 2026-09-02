# ML-3-regression-and-classification

โปรเจกต์นี้ใช้ dataset ภาพใบหน้าคน (ตั้งชื่อไฟล์แบบ UTKFace: `age_gender_race_timestamp.jpg`)
มาสร้างโมเดล Machine Learning ครอบคลุม 3 แล็บ ได้แก่ **Regression**, **Classification**
และ **Model Comparison**

---

## 1. Dataset

| ไฟล์ | รายละเอียด |
|---|---|
| `age_gender.csv` | ตารางข้อมูลหลัก อ่านง่าย มีคอลัมน์ `filename, age, gender, gender_label, race, race_label` รวม 9,778 แถว (1 แถว = 1 ภาพใบหน้า) |
| `others_dir/pixels.npy` | ภาพทุกใบถูกแปลงเป็นภาพขาวดำ (grayscale) ขนาด 32x32 แล้ว flatten เป็นเวกเตอร์ 1,024 มิติ เก็บเป็น numpy array รูปร่าง `(9778, 1024)` ใช้เป็น **features** สำหรับเทรนโมเดล |
| `others_dir/meta.csv` | label ของแต่ละแถวใน `pixels.npy` (filename, age, gender, race) เรียงลำดับตรงกับ `pixels.npy` ทุกแถว |

**gender**: 0 = Male, 1 = Female
**race**: 0 = White, 1 = Black, 2 = Asian, 3 = Indian, 4 = Other

> เหตุผลที่แปลงภาพเป็น pixel array ล่วงหน้า: การอ่านไฟล์ .jpg ทีละภาพระหว่างเทรนโมเดลจะช้ามาก
> จึงประมวลผลครั้งเดียวแล้วเก็บเป็น `.npy` เพื่อให้ `data_loader.py` โหลดได้เร็วทุกครั้งที่รันโปรเจกต์

---

## 2. โครงสร้างไฟล์

```
ML-3-regression-and-classification/
│
├── age_gender.csv              # dataset หลัก (ตารางอ่านง่าย)
├── data_loader.py               # โหลดข้อมูลทั้งแบบตาราง (CSV) และแบบ feature matrix (pixels)
├── main.py                      # รันทั้ง LAB 1 + LAB 2 + สรุปเปรียบเทียบ LAB 3
├── requirements.txt
├── README.md
├── report.pdf                   # รายงานสรุปผลการทดลองทั้ง 3 แล็บ
│
├── others_dir/
│   ├── pixels.npy                # feature matrix: (9778, 1024) grayscale pixels
│   └── meta.csv                  # label คู่กับ pixels.npy
│
├── regression/                   # LAB 1: Regression
│   ├── main.py                   # รันทั้ง 3 โมเดลของ LAB 1 พร้อมสรุปผล
│   ├── model.py                  # Simple LR / Multiple LR / Scaler→PCA→Ridge
│   ├── evaluate.py               # คำนวณ MAE, RMSE, R² และวาดกราฟ
│   └── outputs/
│       ├── regression_results.png    # scatter predicted vs actual + residuals
│       └── age_samples.png           # ตัวอย่างภาพพร้อมอายุจริง/อายุที่ทำนาย
│
├── classification/                # LAB 2: Classification
│   ├── main.py                    # รันทั้งหมดของ LAB 2 พร้อมสรุปผล
│   ├── model.py                   # Scaler→PCA→LogisticRegression (+เวอร์ชัน 2 มิติสำหรับ plot)
│   ├── evaluate.py                # accuracy, classification report, confusion matrix, decision boundary
│   └── outputs/
│       ├── confusion_matrix.png
│       ├── decision_boundary.png     # (เพิ่มเติม) decision boundary บน PCA 2 มิติ
│       └── gender_samples.png
│
└── (สร้างขึ้นเมื่อรันสคริปต์) regression/outputs, classification/outputs
```

---

## 3. รายละเอียดแต่ละแล็บ

### LAB 1: Regression (โฟลเดอร์ `regression/`)

| หัวข้อ | ไฟล์/ฟังก์ชันที่เกี่ยวข้อง |
|---|---|
| Simple Linear Regression | `model.py::build_simple_linear_regression` — ใช้ 1 feature (ค่าความสว่างเฉลี่ยของภาพ) ทำนายอายุ |
| Multiple Linear Regression | `model.py::build_multiple_linear_regression` — ใช้ pixel ดิบทั้ง 1,024 ค่าทำนายอายุ |
| Age Prediction | `model.py::build_age_prediction_pipeline` — pipeline `StandardScaler → PCA(100) → Ridge` ซึ่งเป็นโมเดลหลักของแล็บนี้ |

**Metric ที่ใช้ประเมิน**: MAE, RMSE, R² (ฟังก์ชันอยู่ใน `evaluate.py::regression_metrics`)

**ผลลัพธ์ (ตัวอย่างจากการรันจริง บน test set 800 ภาพ)**

| โมเดล | MAE (ปี) | RMSE (ปี) | R² |
|---|---|---|---|
| Simple Linear Regression | ~19.8 | ~23.8 | ~0.01 |
| Multiple Linear Regression | ~13.8 | ~17.8 | ~0.45 |
| Age Prediction (Scaler→PCA→Ridge) | ~13.4 | ~17.1 | ~0.49 |

### LAB 2: Classification (โฟลเดอร์ `classification/`)

| หัวข้อ | ไฟล์/ฟังก์ชันที่เกี่ยวข้อง |
|---|---|
| Preparing Classification Data | `main.py` ส่วนต้น — โหลด pixel features + label เพศ แล้วแบ่ง train/test |
| Decision Boundary Visualization | `model.py::build_2d_classifier_for_visualization` + `evaluate.py::plot_decision_boundary` — ลด PCA เหลือ 2 มิติ เพื่อวาด decision boundary ได้ |
| Logistic Regression / Gender Prediction | `model.py::build_gender_classifier` — pipeline `StandardScaler → PCA(100) → LogisticRegression` |
| Confusion Matrix | `evaluate.py::plot_confusion_matrix` |

**ผลลัพธ์ (ตัวอย่างจากการรันจริง บน test set 800 ภาพ)**

- โมเดลหลัก (PCA 100 มิติ): **Accuracy ≈ 0.74**
- โมเดลสำหรับ visualize (PCA 2 มิติ): **Accuracy ≈ 0.55** (ต่ำกว่ามาก เพราะมีข้อมูลเหลือแค่ 2 มิติ)

### LAB 3: Model Comparison

เนื้อหานี้ไม่มีโฟลเดอร์แยก แต่รวมอยู่ใน `main.py` (root) ฟังก์ชัน `lab3_model_comparison()`
ซึ่งดึงผลลัพธ์จาก LAB 1 และ LAB 2 มาสรุปเปรียบเทียบ 4 หัวข้อ:

1. **Simple vs Multiple Linear Regression** — เปรียบเทียบ MAE/RMSE/R² ของทั้งสองโมเดล
2. **Training vs Testing Performance** — ดูช่องว่างระหว่าง train MAE กับ test MAE เพื่อสังเกต overfitting
   (Multiple Linear Regression บน pixel ดิบ overfit มากที่สุด ส่วน pipeline PCA→Ridge generalize ได้ดีกว่า)
3. **Regression vs Classification** — เปรียบเทียบว่า target ต่อเนื่อง (อายุ) ใช้ metric MAE/RMSE/R²
   ในขณะที่ target ไม่ต่อเนื่อง (เพศ) ใช้ metric Accuracy/Precision/Recall
4. **Model Performance Metrics** — ตารางสรุปโมเดลที่ดีที่สุดของแต่ละงาน

---

## 4. วิธีติดตั้งและรัน

```bash
# 1. ติดตั้ง dependency
pip install -r requirements.txt

# 2. รันทั้งโปรเจกต์ (LAB 1 + LAB 2 + LAB 3) ในคำสั่งเดียว
python main.py

# หรือรันแยกทีละแล็บ
python regression/main.py
python classification/main.py
```

รันเสร็จแล้วดูผลลัพธ์ภาพได้ที่ `regression/outputs/` และ `classification/outputs/`

---

## 5. สรุปแนวคิดของ Pipeline

ทั้งสองงาน (regression และ classification) ใช้แนวคิดเดียวกัน:

```
raw pixels (1024 มิติ) → StandardScaler → PCA (ลดมิติ) → โมเดล (Ridge / LogisticRegression)
```

- **StandardScaler**: ทำให้ทุก pixel มี scale เท่ากันก่อนเข้าโมเดล เพราะ Ridge/LogisticRegression ไวต่อ scale ของ feature
- **PCA**: ภาพใบหน้ามี pixel ที่สัมพันธ์กันสูงมาก (correlated) การบีบอัดเหลือ ~100 มิติที่มีความแปรปรวนสูงสุด
  ช่วยลด overfitting และลดเวลาเทรนได้มาก โดยแทบไม่เสีย performance
- **Ridge / LogisticRegression**: เป็นโมเดลเชิงเส้นที่มี regularization (L2) ทำให้ทนต่อ feature ที่สัมพันธ์กันสูงได้ดีกว่า
  linear/logistic regression ธรรมดา

---

## 6. หมายเหตุ

- จำนวนภาพที่ใช้เทรนจริงในสคริปต์ (`n_samples=4000`) เป็นการ subsample จาก dataset เต็ม (9,778 ภาพ)
  เพื่อให้รันเร็วบนเครื่องทั่วไป หากต้องการความแม่นยำสูงขึ้นสามารถแก้ค่านี้ใน `regression/main.py`
  และ `classification/main.py` ให้ใช้ข้อมูลทั้งหมดได้
- โมเดลที่ใช้เป็น baseline สำหรับการเรียนรู้แนวคิด regression/classification/model comparison
  ไม่ใช่โมเดล state-of-the-art สำหรับงาน face age/gender prediction จริง (ซึ่งปกติจะใช้ CNN)
