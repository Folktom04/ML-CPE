import argparse
import csv
import hashlib
import random
import shutil
from pathlib import Path

from PIL import Image
from ultralytics import YOLO

CLASSES = ["cat", "dog"]
COCO_IDS = {15: "cat", 16: "dog"}


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def dedupe(files):
    seen, keep, removed = {}, [], []
    # ให้ไฟล์ชื่อปกติมาก่อนไฟล์ที่มี "(1)"
    for f in sorted(files, key=lambda x: ("(" in x.name, x.name)):
        h = md5(f)
        if h in seen:
            removed.append((f.name, seen[h]))
        else:
            seen[h] = f.name
            keep.append(f)
    return keep, removed


def class_of(name: str) -> int:
    return CLASSES.index(name.split(".")[0].lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="Data")
    ap.add_argument("--out", default="dataset")
    ap.add_argument("--teacher", default="yolo11l.pt")
    ap.add_argument("--val-ratio", type=float, default=0.15)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--csv", default="dataset.csv")
    args = ap.parse_args()

    src, out = Path(args.src), Path(args.out)
    random.seed(args.seed)

    train_all, removed = dedupe(list((src / "training").glob("*.jpg")))
    test_all, removed_t = dedupe(list((src / "testing").glob("*.jpg")))
    removed += removed_t
    print(f"removed duplicates: {len(removed)}")

    # stratified split
    splits = {"test": test_all, "train": [], "val": []}
    for c in CLASSES:
        group = sorted([f for f in train_all if f.name.startswith(c + ".")])
        random.shuffle(group)
        n_val = round(len(group) * args.val_ratio)
        splits["val"] += group[:n_val]
        splits["train"] += group[n_val:]

    teacher = YOLO(args.teacher)
    rows = []
    for split, files in splits.items():
        (out / split / "images").mkdir(parents=True, exist_ok=True)
        (out / split / "labels").mkdir(parents=True, exist_ok=True)
        for f in sorted(files):
            cls = class_of(f.name)
            # ทำชื่อไฟล์ให้สะอาด (ไม่มีวงเล็บ/ช่องว่าง)
            stem = f.stem.replace("(", "_").replace(")", "").replace(" ", "_")
            dst = out / split / "images" / f"{stem}.jpg"
            shutil.copy2(f, dst)
            w, h = Image.open(f).size

            res = teacher.predict(str(f), conf=args.conf, classes=list(COCO_IDS), verbose=False)[0]
            boxes = []
            for b in res.boxes:
                x, y, bw, bh = b.xywhn[0].tolist()
                boxes.append((float(b.conf), int(b.cls), x, y, bw, bh))
            # เลือกเฉพาะกล่องที่ตรง class จากชื่อไฟล์; ถ้าไม่มี ใช้กล่อง cat/dog ใดๆ
            same = [b for b in boxes if COCO_IDS[b[1]] == CLASSES[cls]]
            chosen = same if same else boxes
            if chosen:
                source = "auto_yolo" if same else "auto_yolo_classfix"
            else:
                chosen = [(0.0, -1, 0.5, 0.5, 1.0, 1.0)]
                source = "full_image_fallback"

            with open(out / split / "labels" / f"{stem}.txt", "w") as fh:
                for _, _, x, y, bw, bh in chosen:
                    fh.write(f"{cls} {x:.6f} {y:.6f} {bw:.6f} {bh:.6f}\n")

            for conf, _, x, y, bw, bh in chosen:
                rows.append({
                    "split": split, "image": f"{stem}.jpg", "original_file": f.name,
                    "class_id": cls, "class_name": CLASSES[cls],
                    "img_width": w, "img_height": h,
                    "x_center": round(x, 6), "y_center": round(y, 6),
                    "width": round(bw, 6), "height": round(bh, 6),
                    "label_source": source, "teacher_conf": round(conf, 4),
                })

    with open(args.csv, "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)

    (out / "data.yaml").write_text(
        "# Cat vs Dog Object Detection (YOLO format)\n"
        "# ไม่ระบุ path -> Ultralytics ใช้โฟลเดอร์ที่ไฟล์ data.yaml นี้อยู่เป็น root\n"
        "train: train/images\n"
        "val: val/images\n"
        "test: test/images\n\n"
        f"nc: {len(CLASSES)}\n"
        "names:\n" + "".join(f"  {i}: {n}\n" for i, n in enumerate(CLASSES)),
        encoding="utf-8",
    )
    for s, fl in splits.items():
        print(s, len(fl))
    print("removed:", removed)


if __name__ == "__main__":
    main()
