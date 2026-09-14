# ML-06-NN: การจำแนกประเภทสัตว์ด้วย Nearest Neighbor (NN)

โปรเจกต์นี้สาธิตอัลกอริทึม **Nearest Neighbor (NN)** แบบพื้นฐานที่สุด (1-NN คือพิจารณาเพื่อนบ้านที่ใกล้ที่สุดเพียงตัวเดียว ไม่ใช่ k-Nearest Neighbors ที่พิจารณาหลายตัว) โดยใช้ `KNeighborsClassifier(n_neighbors=1)` จากไลบรารี scikit-learn เพื่อจำแนกประเภทของสัตว์ (Mammal, Bird, Reptile, Fish, Amphibian, Bug, Invertebrate) จากลักษณะทางกายภาพ/พฤติกรรม 16 อย่าง โดยใช้ **Zoo Dataset** จาก UCI Machine Learning Repository

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
    ├── split_data.py               # แบ่งข้อมูลเป็น train / validation / test (พร้อมชื่อสัตว์)
    ├── nn_model.py                 # สร้าง เทรน บันทึก และทำนายด้วย Nearest Neighbor (1-NN)
    ├── evaluate.py                 # accuracy, classification report, confusion matrix, กราฟระยะห่าง
    ├── test_nn.py                  # ทดสอบโมเดลกับตัวอย่างสุ่ม 4 ตัว พร้อมย้อนดูเพื่อนบ้านที่ใกล้ที่สุด
    └── outputs/                    # ผลลัพธ์ทั้งหมดจากการรัน pipeline
        ├── features.npy
        ├── labels.npy
        ├── classes.json
        ├── X_train.npy / X_val.npy / X_test.npy
        ├── y_train.npy / y_val.npy / y_test.npy
        ├── names_train.json / names_val.json / names_test.json
        ├── scaler.joblib
        ├── nn_model.joblib
        ├── classification_report.json / .txt
        ├── test_predictions.json
        ├── confusion_matrix.png
        ├── neighbor_distance.png
        └── prediction_sample.png
```

## 3. วิธีการทำงานของ Pipeline

1. **data_loader.py** — โหลด `zoo.csv` และ `class.csv`, ข้ามแถวที่มีค่าว่าง/label ผิดช่วง, บันทึกตารางชื่อคลาสเป็น `classes.json`
2. **preprocessing.py** — แยกฟีเจอร์ 16 คอลัมน์และป้ายกำกับออกจากตาราง แล้ว standardize ฟีเจอร์ด้วย `StandardScaler` (สำคัญมากสำหรับ Nearest Neighbor เพราะอัลกอริทึมนี้วัดระยะห่างแบบ Euclidean หากไม่ scale ฟีเจอร์ที่มีค่าตัวเลขต่างสเกลกันจะมีอิทธิพลไม่เท่ากัน)
3. **split_data.py** — แบ่งข้อมูลแบบ stratified เป็น train 60% / validation 20% / test 20% โดยแบ่งชื่อสัตว์ไปพร้อมกันด้วย (เก็บใน `names_*.json`) เพื่อให้ย้อนดูได้ว่าโมเดลจับคู่กับสัตว์ตัวไหน
4. **nn_model.py** — สร้างโมเดล **Nearest Neighbor แบบพื้นฐาน (`n_neighbors=1`)** ไม่มีการค้นหาค่า k เพราะเป็น NN ไม่ใช่ k-NN แล้วเทรนด้วย train+validation รวมกัน (ไม่มีพารามิเตอร์ให้ปรับ จึงใช้ข้อมูลให้มากที่สุด) และบันทึกโมเดล
5. **evaluate.py** — ประเมินผลบน test set: accuracy, classification report (precision/recall/f1 ต่อคลาส), confusion matrix, และกราฟระยะห่างไปยัง nearest neighbor ของแต่ละตัวอย่างทดสอบ (ใช้แทนกราฟ accuracy-vs-k ของ k-NN เพราะ NN ไม่มีค่า k ให้ปรับ)
6. **test_nn.py** — สุ่มตัวอย่างจาก test set 4 ตัว ทำนาย และ **ย้อนดูว่าจับคู่กับสัตว์ตัวใดในชุดฝึกสอน** พร้อมระยะห่างจริง

รันทั้งหมดด้วยคำสั่งเดียว:

```bash
cd classification
pip install -r ../requirements.txt
python main.py
```

## 4. ผลลัพธ์ที่ได้ (ตัวอย่างจากการรันจริง)

- **Test accuracy:** ดูค่าจริงได้ที่ `outputs/classification_report.txt` (จากการรันตัวอย่าง ได้ 100% บน test set 21 ตัวอย่าง เนื่องจากชุดข้อมูลมีรูปแบบฟีเจอร์ที่แยกแต่ละคลาสได้ชัดเจน)
- **Confusion Matrix:** `outputs/confusion_matrix.png` แสดงจำนวนที่ทำนายถูก/ผิดของแต่ละคลาส
- **Nearest Neighbor Distance:** `outputs/neighbor_distance.png` แสดงระยะห่างของแต่ละตัวอย่างทดสอบไปยังเพื่อนบ้านที่ใกล้ที่สุด — สังเกตได้ว่าสัตว์หลายชนิดมีระยะห่าง ≈ 0 (เช่น lynx กับ polecat, goat กับ reindeer) เพราะมีฟีเจอร์ไบนารีทั้ง 16 ค่าตรงกันทุกตัว ซึ่งเป็นลักษณะที่พบได้บ่อยของชุดข้อมูล Zoo ที่ใช้ฟีเจอร์หยาบ (coarse binary features)

## 5. การประยุกต์ใช้งาน Nearest Neighbor

นอกจากการจำแนกประเภทสัตว์แล้ว โปรเจกต์นี้สาธิตการประยุกต์ใช้งาน NN หลักสองด้าน:

1. **การย้อนรอยคำตอบ (Traceability / Interpretability)** — เพราะ NN ตัดสินใจจากเพื่อนบ้านเพียงตัวเดียว ทุกคำทำนายจึงสามารถอธิบายได้ตรงไปตรงมาว่า "ทำนายแบบนี้เพราะคล้ายกับสัตว์ตัวนี้ในชุดฝึกสอน มากที่สุด" (ดู `test_nn.py` และ `outputs/test_predictions.json`) ซึ่งเป็นจุดเด่นที่โมเดล black-box อื่นให้ไม่ได้ง่าย ๆ
2. **ระยะห่างเป็นตัวชี้วัดความมั่นใจ (Distance as a Confidence Signal)** — ถ้าตัวอย่างใหม่มีระยะห่างไปยัง nearest neighbor มาก แปลว่าไม่คล้ายกับสิ่งที่เคยเห็นมาก่อนเลย ซึ่งใช้เป็นสัญญาณเตือนความไม่มั่นใจ หรือตรวจจับข้อมูลผิดปกติ (novelty/outlier detection) ได้ในงานจริง
3. **Feature scaling ก่อนวัดระยะห่าง** — แสดงให้เห็นว่าทำไมการ standardize ข้อมูลจึงจำเป็นสำหรับอัลกอริทึมที่อาศัยระยะห่างเป็นหลัก (distance-based algorithm) เช่น Nearest Neighbor

## 6. หมายเหตุเรื่อง Reproducibility

- ใช้ `random_state=42` ในการแบ่งข้อมูล เพื่อให้ผลลัพธ์สามารถทำซ้ำได้
- ไฟล์ `.npy`, `.json` และ `.joblib` ทั้งหมดใน `outputs/` เป็นผลลัพธ์จากการรัน pipeline จริง สามารถลบแล้วรัน `python main.py` ใหม่เพื่อสร้างซ้ำได้ทุกครั้ง
