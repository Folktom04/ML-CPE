# ML-06-NN: การจำแนกประเภทสัตว์ด้วย Nearest Neighbor (k-NN)

โปรเจกต์นี้สาธิตอัลกอริทึม **Nearest Neighbor (NN)** โดยใช้ **k-Nearest Neighbors (k-NN)** จากไลบรารี scikit-learn เพื่อจำแนกประเภทของสัตว์ (Mammal, Bird, Reptile, Fish, Amphibian, Bug, Invertebrate) จากลักษณะทางกายภาพ/พฤติกรรม 16 อย่าง โดยใช้ **Zoo Dataset** จาก UCI Machine Learning Repository

> **หมายเหตุ:** โครงสร้างไฟล์ต้นฉบับที่ขอมา ออกแบบไว้สำหรับชุดข้อมูลรูปภาพ (โฟลเดอร์ `PetImages/Cat`, `PetImages/Dog`) แต่ชุดข้อมูลที่แนบมาจริงคือ `zoo.csv` ซึ่งเป็นข้อมูลตาราง (tabular data) จึงปรับโครงสร้างให้เหมาะสม โดยตัดโฟลเดอร์ `PetImages/` ออก และปรับสคริปต์ภายใน `classification/` ให้ทำงานกับข้อมูลตารางแทน (คงชื่อไฟล์ script เดิมไว้ตามที่ระบุ)

## 1. ที่มาของข้อมูล (Dataset)

- **ชื่อชุดข้อมูล:** Zoo Data Set
- **แหล่งที่มา:** UCI Machine Learning Repository — https://archive.ics.uci.edu/dataset/111/zoo
- **จำนวนตัวอย่าง:** 101 ตัวอย่าง (สัตว์ 101 ชนิด)
- **จำนวนคุณลักษณะ (features):** 16 คุณลักษณะ ส่วนใหญ่เป็นค่าไบนารี (0/1) เช่น hair, feathers, eggs, milk, airborne, aquatic, predator, toothed, backbone, breathes, venomous, fins, tail, domestic, catsize และ legs (จำนวนขา ค่าจำนวนเต็ม)
- **ป้ายกำกับ (label):** `class_type` (1–7) แมปกับชื่อคลาสจาก `class.csv` ได้แก่ Mammal, Bird, Reptile, Fish, Amphibian, Bug, Invertebrate
- ไฟล์ `dataset.csv` ที่ระดับบนสุดของโปรเจกต์ คือไฟล์ `zoo.csv` ต้นฉบับ (คัดลอกมาเพื่อให้ตรงกับโครงสร้างที่ต้องการอัพโหลด GitHub)

## 2. โครงสร้างโปรเจกต์

```
ML-06-NN/
├── dataset.csv                     # ชุดข้อมูล Zoo (สำเนาของ zoo.csv)
├── report.pdf                      # รายงานฉบับเต็ม (ภาษาไทย)
├── README.md                       # ไฟล์นี้
├── requirements.txt                # รายชื่อไลบรารีที่ต้องติดตั้ง
└── classification/
    ├── zoo.csv                     # ชุดข้อมูลหลัก (ใช้จริงโดยสคริปต์)
    ├── class.csv                   # ตารางแมปหมายเลขคลาส -> ชื่อคลาส
    ├── main.py                     # รันทั้ง pipeline ตั้งแต่ต้นจนจบ
    ├── data_loader.py              # โหลดข้อมูล ตรวจสอบ/ข้ามแถวที่ผิดพลาด
    ├── preprocessing.py            # แปลงเป็น feature/label array และ scale
    ├── split_data.py               # แบ่งข้อมูลเป็น train / validation / test
    ├── nn_model.py                 # สร้าง เทรน บันทึก และทำนายด้วย k-NN
    ├── evaluate.py                 # accuracy, classification report, confusion matrix, กราฟ
    ├── test_nn.py                  # ทดสอบโมเดลกับตัวอย่างสุ่ม 4 ตัว
    └── outputs/                    # ผลลัพธ์ทั้งหมดจากการรัน pipeline
        ├── features.npy
        ├── labels.npy
        ├── classes.json
        ├── X_train.npy / X_val.npy / X_test.npy
        ├── y_train.npy / y_val.npy / y_test.npy
        ├── scaler.joblib
        ├── nn_model.joblib
        ├── history.json
        ├── classification_report.json / .txt
        ├── test_predictions.json
        ├── confusion_matrix.png
        ├── training_history.png
        └── prediction_sample.png
```

## 3. วิธีการทำงานของ Pipeline

1. **data_loader.py** — โหลด `zoo.csv` และ `class.csv`, ข้ามแถวที่มีค่าว่าง/label ผิดช่วง, บันทึกตารางชื่อคลาสเป็น `classes.json`
2. **preprocessing.py** — แยกฟีเจอร์ 16 คอลัมน์และป้ายกำกับออกจากตาราง แล้ว standardize ฟีเจอร์ด้วย `StandardScaler` (สำคัญมากสำหรับ k-NN เพราะอัลกอริทึมนี้วัดระยะห่างแบบ Euclidean หากไม่ scale ฟีเจอร์ที่มีค่าตัวเลขต่างสเกลกันจะมีอิทธิพลไม่เท่ากัน)
3. **split_data.py** — แบ่งข้อมูลแบบ stratified เป็น train 60% / validation 20% / test 20%
4. **nn_model.py** — ค้นหาค่า **k** ที่ดีที่สุด (k = 1 ถึง 15) โดยดู accuracy บน validation set (model selection) จากนั้นเทรนโมเดลสุดท้ายด้วย train+validation แล้วบันทึกโมเดล
5. **evaluate.py** — ประเมินผลบน test set: accuracy, classification report (precision/recall/f1 ต่อคลาส), confusion matrix, และกราฟ accuracy เทียบกับค่า k
6. **test_nn.py** — สุ่มตัวอย่างจาก test set 4 ตัว ทำนายและเปรียบเทียบกับค่าจริง

รันทั้งหมดด้วยคำสั่งเดียว:

```bash
cd classification
pip install -r ../requirements.txt
python main.py
```

## 4. ผลลัพธ์ที่ได้ (ตัวอย่างจากการรันจริง)

- **ค่า k ที่ดีที่สุด:** เลือกจาก validation accuracy (ดูกราฟ `training_history.png`) — ที่ k น้อยมาก (k=1) โมเดลจะ overfit (train accuracy = 100% แต่ validation ต่ำกว่า) ส่วนที่ k มากเกินไปโมเดลจะ underfit ค่ากลาง ๆ ให้ validation accuracy สูงสุด
- **Test accuracy:** ดูค่าจริงได้ที่ `outputs/classification_report.txt` (จากการรันตัวอย่าง ได้ 100% บน test set 21 ตัวอย่าง เนื่องจากชุดข้อมูลมีรูปแบบฟีเจอร์ที่แยกแต่ละคลาสได้ชัดเจน)
- **Confusion Matrix:** `outputs/confusion_matrix.png` แสดงจำนวนที่ทำนายถูก/ผิดของแต่ละคลาส

## 5. การประยุกต์ใช้งาน Nearest Neighbor

นอกจากการจำแนกประเภทสัตว์แล้ว แนวคิด k-NN ในโปรเจกต์นี้สาธิตการประยุกต์ใช้งานหลักสองด้าน:

1. **Model selection ด้วยการค้นหาค่า k (Elbow method แบบ validation curve)** — เลือกจำนวนเพื่อนบ้านที่เหมาะสมที่สุดจากข้อมูลจริง แทนการเดาค่า k ตายตัว ซึ่งเป็นขั้นตอนสำคัญของการนำ k-NN ไปใช้งานจริง
2. **Feature scaling ก่อนวัดระยะห่าง** — แสดงให้เห็นว่าทำไมการ standardize ข้อมูลจึงจำเป็นสำหรับอัลกอริทึมที่อาศัยระยะห่างเป็นหลัก (distance-based algorithm) เช่น k-NN

## 6. หมายเหตุเรื่อง Reproducibility

- ใช้ `random_state=42` ในการแบ่งข้อมูล เพื่อให้ผลลัพธ์สามารถทำซ้ำได้
- ไฟล์ `.npy` และ `.joblib` ทั้งหมดใน `outputs/` เป็นผลลัพธ์จากการรัน pipeline จริง สามารถลบแล้วรัน `python main.py` ใหม่เพื่อสร้างซ้ำได้ทุกครั้ง
