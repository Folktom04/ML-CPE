import argparse
import csv
from pathlib import Path

import cv2
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
COLORS = {"cat": (255, 140, 0), "dog": (0, 200, 0)}  # BGR


def parse_args():
    ap = argparse.ArgumentParser(description="Detect cats/dogs in images")
    ap.add_argument("--weights", default=str(ROOT / "outputs" / "best.pt"))
    ap.add_argument("--source", default=str(ROOT / "dataset" / "test" / "images"))
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--imgsz", type=int, default=416)
    ap.add_argument("--limit", type=int, default=0, help="จำนวนรูปสูงสุด (0 = ทั้งหมด)")
    ap.add_argument("--out", default=str(ROOT / "outputs" / "image_test"))
    ap.add_argument("--show", action="store_true", help="แสดงหน้าต่างผลลัพธ์")
    return ap.parse_args()


def draw(img, boxes, names):
    for b in boxes:
        x1, y1, x2, y2 = map(int, b.xyxy[0].tolist())
        name, conf = names[int(b.cls)], float(b.conf)
        color = COLORS.get(name, (0, 0, 255))
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        label = f"{name} {conf:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(img, (x1, max(0, y1 - th - 8)), (x1 + tw + 6, y1), color, -1)
        cv2.putText(img, label, (x1 + 3, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    return img


def main():
    args = parse_args()
    src = Path(args.source)
    files = sorted(p for p in src.iterdir() if p.suffix.lower() in IMG_EXT) if src.is_dir() else [src]
    if args.limit:
        files = files[: args.limit]

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    model = YOLO(args.weights)

    rows = []
    for f in files:
        r = model.predict(str(f), conf=args.conf, imgsz=args.imgsz, verbose=False)[0]
        img = draw(cv2.imread(str(f)), r.boxes, model.names)
        cv2.imwrite(str(out / f.name), img)

        if len(r.boxes) == 0:
            rows.append({"image": f.name, "pred_class": "none", "conf": 0,
                         "x1": "", "y1": "", "x2": "", "y2": ""})
            print(f"{f.name:<22} -> (no detection)")
        for b in r.boxes:
            x1, y1, x2, y2 = [round(v, 1) for v in b.xyxy[0].tolist()]
            name = model.names[int(b.cls)]
            rows.append({"image": f.name, "pred_class": name, "conf": round(float(b.conf), 4),
                         "x1": x1, "y1": y1, "x2": x2, "y2": y2})
            print(f"{f.name:<22} -> {name:<4} conf={float(b.conf):.2f} box=({x1},{y1},{x2},{y2})")

        if args.show:
            cv2.imshow("Cat/Dog Detection", img)
            if cv2.waitKey(0) & 0xFF == ord("q"):
                break

    with open(out / "predictions.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=["image", "pred_class", "conf", "x1", "y1", "x2", "y2"])
        wr.writeheader()
        wr.writerows(rows)
    cv2.destroyAllWindows()
    print(f"\n[OK] {len(files)} images -> {out}")


if __name__ == "__main__":
    main()
