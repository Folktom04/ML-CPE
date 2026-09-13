# -*- coding: utf-8 -*-
 
import json
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE_DIR, "classification", "outputs")
FONT_PATH = os.path.join(BASE_DIR, "..", "fonts", "NotoSansThai-Regular.ttf")

pdfmetrics.registerFont(TTFont("Thai", FONT_PATH))

# ---------------------------------------------------------------- styles ---
styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "ThaiTitle", parent=styles["Title"], fontName="Thai",
    fontSize=22, leading=28, spaceAfter=6, textColor=colors.HexColor("#2E3A59"),
)
subtitle_style = ParagraphStyle(
    "ThaiSubtitle", parent=styles["Normal"], fontName="Thai",
    fontSize=13, leading=18, textColor=colors.HexColor("#555555"),
    spaceAfter=20,
)
h1_style = ParagraphStyle(
    "ThaiH1", parent=styles["Heading1"], fontName="Thai",
    fontSize=16, leading=20, spaceBefore=16, spaceAfter=8,
    textColor=colors.HexColor("#1F3B73"),
)
h2_style = ParagraphStyle(
    "ThaiH2", parent=styles["Heading2"], fontName="Thai",
    fontSize=13, leading=17, spaceBefore=10, spaceAfter=6,
    textColor=colors.HexColor("#2E3A59"),
)
body_style = ParagraphStyle(
    "ThaiBody", parent=styles["Normal"], fontName="Thai",
    fontSize=11, leading=17, spaceAfter=8, alignment=0,  # left (justify looks uneven with mixed Thai/English tokens)
)
bullet_style = ParagraphStyle(
    "ThaiBullet", parent=body_style, leftIndent=14, spaceAfter=4,
)
caption_style = ParagraphStyle(
    "ThaiCaption", parent=styles["Normal"], fontName="Thai",
    fontSize=9.5, leading=13, textColor=colors.HexColor("#666666"),
    alignment=1, spaceAfter=14, spaceBefore=4,
)
code_style = ParagraphStyle(
    "ThaiCode", parent=styles["Normal"], fontName="Courier",
    fontSize=8.5, leading=11, backColor=colors.HexColor("#F4F4F4"),
    borderPadding=6, spaceAfter=10,
)

# ------------------------------------------------------------- load data ---
with open(os.path.join(OUT_DIR, "classes.json"), encoding="utf-8") as f:
    class_names = json.load(f)

with open(os.path.join(OUT_DIR, "classification_report.txt"), encoding="utf-8") as f:
    report_text = f.read()

acc_line = report_text.splitlines()[0]  # "Test accuracy: 0.5963"
test_acc = acc_line.split(":")[1].strip()

# Parse the per-class table out of report_text for a nicer PDF table
lines = [l for l in report_text.splitlines() if l.strip()]
table_rows = [["Class", "Precision", "Recall", "F1-score", "Support"]]
for line in lines:
    parts = line.split()
    if len(parts) == 5 and parts[0] in class_names:
        table_rows.append(parts)

# overall accuracy row
for line in lines:
    if line.strip().startswith("accuracy"):
        parts = line.split()
        # format: accuracy  0.60  218
        table_rows.append(["accuracy", "", "", parts[-2], parts[-1]])

story = []

# ------------------------------------------------------------- title page --
story.append(Spacer(1, 2 * cm))
story.append(Paragraph("รายงานโครงงาน ML-07-CNN", title_style))
story.append(Paragraph(
    "การจำแนกตำแหน่งโปรตีนในเซลล์ยีสต์ด้วยโครงข่ายประสาทเทียมแบบคอนโวลูชัน 1 มิติ "
    "(1D Convolutional Neural Network)",
    subtitle_style,
))
story.append(Spacer(1, 0.5 * cm))

info_table = Table([
    ["ชุดข้อมูล (Dataset)", "Yeast Dataset (UCI Machine Learning Repository)"],
    ["จำนวนตัวอย่าง", "1,484 แถว (8 คุณลักษณะเชิงตัวเลข)"],
    ["จำนวนคลาส", f"{len(class_names)} คลาส ({', '.join(class_names)})"],
    ["โมเดลที่ใช้", "1D Convolutional Neural Network (TensorFlow / Keras)"],
    ["ความแม่นยำบนชุดทดสอบ", f"{float(test_acc)*100:.2f}%"],
], colWidths=[5.5 * cm, 10.5 * cm])
info_table.setStyle(TableStyle([
    ("FONTNAME", (0, 0), (-1, -1), "Thai"),
    ("FONTSIZE", (0, 0), (-1, -1), 10.5),
    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAF0FB")),
    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1F3B73")),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 7),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ("LEFTPADDING", (0, 0), (-1, -1), 8),
]))
story.append(info_table)
story.append(PageBreak())

# ------------------------------------------------------------- 1. intro ----
story.append(Paragraph("1. บทนำ", h1_style))
story.append(Paragraph(
    "โครงงานนี้มีวัตถุประสงค์เพื่อสร้างโครงข่ายประสาทเทียมแบบคอนโวลูชัน (Convolutional "
    "Neural Network: CNN) สำหรับจำแนกตำแหน่งการอยู่อาศัยของโปรตีนภายในเซลล์ยีสต์ "
    "(protein subcellular localization) จากค่าคุณลักษณะทางชีวเคมี 8 ค่าที่คำนวณได้จากลำดับ "
    "กรดอะมิโนของโปรตีนแต่ละชนิด", body_style,
))
story.append(Paragraph(
    "โครงร่างของงานที่ได้รับมอบหมาย (ML-07-CNN template) ถูกออกแบบมาสำหรับข้อมูลรูปภาพ "
    "(เช่น การจำแนกภาพแมวและสุนัขในโฟลเดอร์ PetImages) อย่างไรก็ตาม ชุดข้อมูลที่ใช้จริงในโครงงานนี้ "
    "คือ yeast.csv ซึ่งเป็น <b>ข้อมูลตาราง (tabular data)</b> ไม่ใช่รูปภาพ ผู้จัดทำจึงปรับสถาปัตยกรรม "
    "จาก 2D-CNN (ที่ออกแบบมาสำหรับข้อมูลภาพ) เป็น <b>1D-CNN</b> ซึ่งเหมาะสมกับข้อมูลที่อยู่ในรูปแบบ "
    "เวกเตอร์ตัวเลขต่อเนื่อง โดยยังคงขั้นตอนการทำงานแบบเดียวกับ CNN สำหรับภาพ ได้แก่ การโหลดข้อมูล "
    "การเตรียมข้อมูล การแบ่งชุดข้อมูล การฝึกโมเดล และการประเมินผล", body_style,
))

# ------------------------------------------------------------- 2. dataset --
story.append(Paragraph("2. ชุดข้อมูล (Dataset)", h1_style))
story.append(Paragraph(
    "ชุดข้อมูล Yeast มาจาก UCI Machine Learning Repository ประกอบด้วยข้อมูลโปรตีน 1,484 ตัวอย่าง "
    "แต่ละตัวอย่างมีคุณลักษณะเชิงตัวเลข 8 ค่า (ค่าทั้งหมดอยู่ในช่วง 0-1) และป้ายกำกับ (label) ระบุ "
    "ตำแหน่งที่โปรตีนนั้นอยู่ในเซลล์ ดังตารางต่อไปนี้:", body_style,
))

feature_table = Table([
    ["คุณลักษณะ", "ความหมายโดยสังเขป"],
    ["mcg", "คะแนนจากวิธี McGeoch สำหรับสัญญาณการส่งออกโปรตีน (signal sequence)"],
    ["gvh", "คะแนนจากวิธี von Heijne สำหรับสัญญาณเดียวกัน"],
    ["alm", "คะแนนจากโปรแกรม ALOM ที่ทำนายบริเวณเยื่อหุ้มเซลล์ (membrane spanning region)"],
    ["mit", "คะแนนจากการวิเคราะห์ลำดับสัญญาณไมโทคอนเดรีย (mitochondrial signal)"],
    ["erl", "ค่าบ่งชี้การมีลำดับสัญญาณ HDEL (endoplasmic reticulum)"],
    ["pox", "คะแนนบ่งชี้โมทีฟ peroxisomal targeting signal"],
    ["vac", "คะแนนจากการวิเคราะห์โปรตีนในแวคิวโอล (vacuolar)"],
    ["nuc", "คะแนนบ่งชี้สัญญาณนำเข้านิวเคลียส (nuclear localization signal)"],
], colWidths=[2.7 * cm, 13.3 * cm])
feature_table.setStyle(TableStyle([
    ("FONTNAME", (0, 0), (-1, -1), "Thai"),
    ("FONTSIZE", (0, 0), (-1, -1), 9.5),
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3B73")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
]))
story.append(feature_table)
story.append(Spacer(1, 10))

story.append(Paragraph(
    f"ป้ายกำกับ (class) มีทั้งหมด {len(class_names)} คลาส ได้แก่ CYT (cytosolic/cytoskeletal), "
    "NUC (nuclear), MIT (mitochondrial), ME1/ME2/ME3 (membrane protein แบบต่าง ๆ), EXC "
    "(extracellular), VAC (vacuolar), POX (peroxisomal) และ ERL (endoplasmic reticulum lumen) "
    "ทั้งนี้ การกระจายตัวของแต่ละคลาส<b>ไม่สมดุลกันอย่างมาก</b> โดยคลาส CYT มีจำนวนมากที่สุด (463 ตัวอย่าง) "
    "ในขณะที่คลาส ERL มีเพียง 5 ตัวอย่างเท่านั้น ซึ่งเป็นปัจจัยสำคัญที่ทำให้การจำแนกคลาสส่วนน้อยทำได้ยาก",
    body_style,
))

# ------------------------------------------------------------- 3. method ---
story.append(Paragraph("3. ระเบียบวิธี (Methodology)", h1_style))

story.append(Paragraph("3.1 การเตรียมข้อมูล (Data Loading &amp; Preprocessing)", h2_style))
story.append(Paragraph(
    "1) <b>data_loader.py</b> — โหลดข้อมูลจาก dataset.csv ตรวจสอบและตัดแถวที่มีค่าว่างหรือค่าที่ "
    "ไม่ใช่ตัวเลข (คล้ายกับการข้ามไฟล์ภาพที่เสียหายในปัญหาแบบภาพ) รวมถึงลบแถวที่ซ้ำกัน", bullet_style,
))
story.append(Paragraph(
    "2) <b>preprocessing.py</b> — ปรับสเกลคุณลักษณะทั้ง 8 ค่าด้วย StandardScaler (ให้ค่าเฉลี่ย = 0 "
    "ส่วนเบี่ยงเบนมาตรฐาน = 1) จากนั้นเข้ารหัสป้ายกำกับข้อความเป็นตัวเลขด้วย LabelEncoder และปรับรูปร่าง "
    "เวกเตอร์คุณลักษณะจาก (8,) เป็น (8, 1) เพื่อให้สอดคล้องกับอินพุตที่ Conv1D ต้องการ (แกน channel)", bullet_style,
))
story.append(Paragraph(
    "3) <b>split_data.py</b> — แบ่งข้อมูลแบบ stratified (คงสัดส่วนคลาสในทุกชุด) เป็นชุดฝึก 70% "
    "ชุด validation 15% และชุดทดสอบ 15%", bullet_style,
))

story.append(Paragraph("3.2 สถาปัตยกรรมโมเดล (Model Architecture)", h2_style))
story.append(Paragraph(
    "โมเดลถูกสร้างด้วย TensorFlow/Keras ในไฟล์ <b>cnn_model.py</b> ประกอบด้วยชั้น Conv1D สองชั้นเพื่อ "
    "เรียนรู้ความสัมพันธ์ระหว่างคุณลักษณะที่อยู่ใกล้กัน ตามด้วย Global Average Pooling และชั้น Dense "
    "สำหรับจำแนกคลาสสุดท้าย ดังนี้:", body_style,
))
arch_lines = [
    "Input (8, 1)",
    "  -> Conv1D(32, kernel_size=3, activation='relu') + BatchNormalization",
    "  -> Conv1D(64, kernel_size=3, activation='relu') + BatchNormalization",
    "  -> GlobalAveragePooling1D",
    "  -> Dense(64, activation='relu') + Dropout(0.3)",
    "  -> Dense(10, activation='softmax')",
]
story.append(Paragraph("<br/>".join(arch_lines), code_style))
story.append(Paragraph(
    "การฝึกโมเดลใช้ Optimizer แบบ Adam (learning rate = 0.001) และฟังก์ชันสูญเสีย sparse categorical "
    "cross-entropy พร้อมเทคนิค Early Stopping ที่เฝ้าติดตามค่า validation loss (patience = 10 epoch) "
    "เพื่อป้องกันปัญหา overfitting", body_style,
))

story.append(Paragraph("3.3 การประเมินผลและการทดสอบ", h2_style))
story.append(Paragraph(
    "<b>evaluate.py</b> คำนวณความแม่นยำโดยรวม (accuracy), classification report (precision, recall, "
    "F1-score รายคลาส) และ confusion matrix บนชุดทดสอบ ส่วน <b>test_cnn.py</b> สุ่มตัวอย่าง 4 ตัวอย่าง "
    "จากชุดทดสอบมาทำนายและแสดงผลเปรียบเทียบระหว่างค่าจริงกับค่าที่โมเดลทำนาย", body_style,
))

story.append(PageBreak())

# ------------------------------------------------------------- 4. results --
story.append(Paragraph("4. ผลการทดลอง (Results)", h1_style))
story.append(Paragraph(
    f"โมเดล 1D-CNN ทำความแม่นยำบนชุดทดสอบได้ <b>{float(test_acc)*100:.2f}%</b> "
    "ซึ่งใกล้เคียงกับผลลัพธ์ที่มีการรายงานในงานวิจัยที่ใช้ชุดข้อมูล Yeast นี้ (โดยทั่วไปอยู่ในช่วง 55-60%) "
    "เนื่องจากชุดข้อมูลนี้มีลักษณะคลาสไม่สมดุลและขอบเขตของคลาสบางคู่ทับซ้อนกันในเชิงคุณลักษณะ", body_style,
))

story.append(Paragraph("4.1 ตารางผลการจำแนกรายคลาส (Classification Report)", h2_style))
report_table = Table(table_rows, colWidths=[3 * cm, 3 * cm, 3 * cm, 3 * cm, 3 * cm])
report_table.setStyle(TableStyle([
    ("FONTNAME", (0, 0), (-1, -1), "Thai"),
    ("FONTSIZE", (0, 0), (-1, -1), 9.5),
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3B73")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
]))
story.append(report_table)
story.append(Spacer(1, 12))

story.append(Paragraph("4.2 Confusion Matrix", h2_style))
story.append(Image(os.path.join(OUT_DIR, "confusion_matrix.png"), width=13 * cm, height=11.7 * cm))
story.append(Paragraph(
    "รูปที่ 1: Confusion Matrix แสดงจำนวนตัวอย่างที่โมเดลทำนายถูก/ผิดในแต่ละคลาสบนชุดทดสอบ "
    "จะเห็นได้ว่าคลาสที่มีตัวอย่างมาก (CYT, NUC, MIT) มีแนวโน้มถูกทำนายได้ดีกว่าคลาสที่มีตัวอย่างน้อย "
    "(ERL, VAC, POX) อย่างชัดเจน และคลาส CYT/NUC มีความสับสนกันเองค่อนข้างมาก เนื่องจากคุณลักษณะของ "
    "โปรตีนสองกลุ่มนี้มีความใกล้เคียงกัน", caption_style,
))

story.append(Paragraph("4.3 กราฟการฝึกโมเดล (Training History)", h2_style))
story.append(Image(os.path.join(OUT_DIR, "training_history.png"), width=16 * cm, height=6 * cm))
story.append(Paragraph(
    "รูปที่ 2: ค่า Loss และ Accuracy ของชุดฝึก (train) และชุด validation ตลอดการฝึกโมเดล "
    "แสดงให้เห็นว่าโมเดลลู่เข้า (converge) ได้ดีโดยไม่มีสัญญาณของ overfitting ที่รุนแรง เนื่องจากค่า "
    "validation loss ไม่ได้เพิ่มขึ้นสวนทางกับ training loss อย่างชัดเจน",
    caption_style,
))

story.append(PageBreak())

story.append(Paragraph("4.4 ตัวอย่างการทำนาย (Prediction Sample)", h2_style))
story.append(Image(os.path.join(OUT_DIR, "prediction_sample.png"), width=16 * cm, height=6.5 * cm))
story.append(Paragraph(
    "รูปที่ 3: ผลการทดสอบโมเดลกับตัวอย่างที่สุ่มมา 4 ตัวอย่างจากชุดทดสอบ กราฟแท่งสีน้ำเงินหมายถึง "
    "ทำนายถูกต้อง ส่วนสีแดงหมายถึงทำนายผิด พร้อมแสดงค่าความมั่นใจ (confidence) ของโมเดลกำกับไว้ที่หัวข้อ "
    "แต่ละภาพ", caption_style,
))

# ------------------------------------------------------------- 5. discuss --
story.append(Paragraph("5. สรุปและอภิปรายผล (Conclusion &amp; Discussion)", h1_style))
story.append(Paragraph(
    "โครงข่ายประสาทเทียมแบบ 1D-CNN สามารถเรียนรู้และจำแนกตำแหน่งของโปรตีนในเซลล์ยีสต์ได้ในระดับที่ "
    "ใกล้เคียงกับผลงานวิจัยที่เผยแพร่ก่อนหน้านี้ โดยจุดแข็งของโมเดลอยู่ที่คลาสที่มีจำนวนตัวอย่างมากพอ เช่น "
    "ME1, ME3 และ MIT ในขณะที่คลาสที่มีตัวอย่างน้อยมาก เช่น ERL (5 ตัวอย่าง) และ VAC (30 ตัวอย่าง) "
    "โมเดลแทบไม่สามารถเรียนรู้รูปแบบได้ ซึ่งเป็นข้อจำกัดที่เกิดจากปัญหา class imbalance ของชุดข้อมูลเอง "
    "ไม่ใช่ข้อจำกัดของสถาปัตยกรรมโมเดล", body_style,
))
story.append(Paragraph(
    "แนวทางที่อาจช่วยปรับปรุงผลลัพธ์ในอนาคต ได้แก่ การทำ oversampling (เช่น SMOTE) สำหรับคลาสส่วนน้อย "
    "การปรับค่าถ่วงน้ำหนักของแต่ละคลาส (class weighting) ในฟังก์ชันสูญเสีย หรือการเพิ่มข้อมูลจากแหล่งอื่น "
    "เพื่อให้จำนวนตัวอย่างของแต่ละคลาสสมดุลกันมากขึ้น", body_style,
))
story.append(Paragraph(
    "โดยสรุป โครงงานนี้แสดงให้เห็นว่าแนวคิดของ CNN ซึ่งเดิมออกแบบมาสำหรับข้อมูลภาพ สามารถปรับใช้กับ "
    "ข้อมูลตาราง (tabular data) ได้ผ่านการใช้ Conv1D โดยยังคงขั้นตอนหลักของ pipeline แบบเดียวกัน "
    "ได้แก่ การเตรียมข้อมูล การฝึกโมเดล และการประเมินผล", body_style,
))

# ------------------------------------------------------------ build pdf ---
doc = SimpleDocTemplate(
    os.path.join(BASE_DIR, "report.pdf"),
    pagesize=A4,
    leftMargin=2.2 * cm, rightMargin=2.2 * cm,
    topMargin=2 * cm, bottomMargin=2 * cm,
    title="รายงานโครงงาน ML-07-CNN",
)
doc.build(story)
print("report.pdf generated")
