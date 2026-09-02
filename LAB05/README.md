# ML-05-SVM: Cat vs Dog Classification ด้วย Support Vector Machine

โปรเจกต์นี้สร้างโมเดล **Support Vector Machine (SVM)** เพื่อจำแนกภาพ
แมว (Cat) และสุนัข (Dog) โดยใช้เทคนิคการสกัดคุณลักษณะแบบดั้งเดิม
(HOG Feature Extraction) ร่วมกับ `scikit-learn`

## 1. ภาพรวมของ Dataset

- แหล่งที่มา: [Cat and Dog (Kaggle, tongpython)](https://www.kaggle.com/datasets/tongpython/cat-and-dog)
  (รายละเอียดเพิ่มเติมดูที่ [link-data.txt](link-data.txt))
- จำนวนภาพทั้งหมด: **10,000 รูป** แบ่งเป็น
  - `PetImages/Cat/` : 5,000 รูป
  - `PetImages/Dog/` : 5,000 รูป
- มีไฟล์ `dataset.csv` เป็น manifest แสดง path และ label ของภาพทุกไฟล์

## 2. โครงสร้างโปรเจกต์

```
ML-05-SVM/
│
├── PetImages/                 # ข้อมูลภาพต้นฉบับ (Cat / Dog)
│   ├── Cat/
│   └── Dog/
│
├── classification/             # โค้ด pipeline ทั้งหมด
│   ├── main.py                 # รันทุกขั้นตอนตั้งแต่ต้นจนจบ
│   ├── data_loader.py          # โหลดรายชื่อไฟล์ภาพจาก PetImages/
│   ├── preprocessing.py        # resize + สกัด HOG feature
│   ├── split_data.py           # แบ่ง Train/Test + StandardScaler
│   ├── svm_model.py            # สร้าง/เทรนโมเดล SVM (kernel=RBF)
│   ├── evaluate.py             # ประเมินผล + วาด Confusion Matrix
│   ├── test_svm.py             # pytest tests + ทำนายภาพเดี่ยว
│   └── outputs/                # ผลลัพธ์ที่ได้จากการรัน pipeline
│       ├── features.npy
│       ├── labels.npy
│       ├── classes.json
│       ├── X_train.npy / X_test.npy
│       ├── y_train.npy / y_test.npy
│       ├── scaler.pkl
│       ├── svm_model.pkl
│       ├── metrics.json
│       └── confusion_matrix.png
│
├── dataset.csv                 # manifest: filepath,label ของภาพทั้งหมด
├── report.pdf                  # รายงานสรุปผลโปรเจกต์ (ภาษาไทย)
├── requirements.txt
└── link-data.txt               # แหล่งที่มาของ dataset
```

## 3. ขั้นตอนการทำงานของ Pipeline

| ขั้นตอน | ไฟล์ | รายละเอียด |
|---|---|---|
| 1. โหลดข้อมูล | `data_loader.py` | สแกนโฟลเดอร์ `PetImages/Cat`, `PetImages/Dog` และคืนค่า path + label |
| 2. เตรียมข้อมูล | `preprocessing.py` | resize ภาพเป็น 64×64 → แปลงขาวดำ → สกัด HOG feature (1,764 มิติ) |
| 3. แบ่งข้อมูล | `split_data.py` | แบ่ง Train/Test แบบ 80/20 (stratified) + StandardScaler |
| 4. เทรนโมเดล | `svm_model.py` | เทรน `SVC(kernel="rbf", C=10, gamma="scale")` |
| 5. ประเมินผล | `evaluate.py` | คำนวณ Accuracy/Precision/Recall/F1 + Confusion Matrix |
| 6. ทดสอบ | `test_svm.py` | pytest unit tests + ฟังก์ชันทำนายภาพเดี่ยว |

## 4. วิธีการติดตั้งและรัน

```bash
# 1) ติดตั้งไลบรารีที่จำเป็น
pip install -r requirements.txt

# 2) รัน pipeline ทั้งหมด (ตั้งแต่โหลดข้อมูลจนถึงประเมินผล)
cd classification
python main.py

# 3) รันเทสต์เพื่อตรวจสอบความถูกต้อง
pytest test_svm.py -v

# 4) ทำนายภาพเดี่ยว
python test_svm.py path/to/your_image.jpg
```

> หมายเหตุ: `main.py` จะรัน ครบทุกขั้นตอน (2-6) ในคำสั่งเดียว
> หากต้องการรันทีละขั้นตอน สามารถรัน `preprocessing.py` → `split_data.py`
> → `svm_model.py` → `evaluate.py` ตามลำดับได้เช่นกัน

## 5. ผลลัพธ์ที่ได้ (จากการรันจริงบน dataset ทั้งหมด)

- **Accuracy บนชุด Test (2,000 รูป): 75.20%**
- Precision / Recall / F1-score ของทั้งสองคลาสอยู่ในช่วง 0.74–0.76
  (ดูรายละเอียดฉบับเต็มใน `classification/outputs/metrics.json`
  และ `report.pdf`)

ผลลัพธ์นี้แสดงให้เห็นข้อจำกัดของ SVM ร่วมกับ HOG feature เมื่อเทียบกับ
โมเดล Deep Learning (CNN) ซึ่งมักทำ accuracy ได้สูงกว่า 90% บน dataset
เดียวกัน เนื่องจาก HOG เป็น hand-crafted feature ที่จับได้เฉพาะขอบ
(edge) และทิศทางของ gradient เท่านั้น ไม่สามารถเรียนรู้ลักษณะเชิงลึก
(texture, ท่าทาง, พื้นหลัง) ได้เท่า CNN

## 6. เทคโนโลยีที่ใช้

- Python 3
- scikit-learn (SVM, StandardScaler, train_test_split, metrics)
- scikit-image (HOG feature extraction)
- Pillow (การจัดการรูปภาพ)
- matplotlib (การวาด Confusion Matrix)
- pytest (การทดสอบ)
