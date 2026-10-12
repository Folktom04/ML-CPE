import argparse
import shutil
from pathlib import Path

from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent


def parse_args():
    ap = argparse.ArgumentParser(description="Train YOLOv8 on Cat/Dog dataset")
    ap.add_argument("--data", default=str(ROOT / "dataset" / "data.yaml"))
    ap.add_argument("--model", default="yolov8n.pt", help="pretrained weights (COCO)")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--imgsz", type=int, default=416)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--device", default="cpu", help="'cpu' หรือ '0' สำหรับ GPU")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--patience", type=int, default=10, help="early stopping")
    ap.add_argument("--seed", type=int, default=42)
    return ap.parse_args()


def main():
    args = parse_args()
    model = YOLO(args.model)  # Transfer learning จาก COCO pre-trained

    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        patience=args.patience,
        seed=args.seed,
        optimizer="AdamW",
        lr0=0.001,
        cos_lr=True,
        project=str(ROOT / "outputs"),
        name="train",
        exist_ok=True,
        plots=True,
        verbose=True,
    )

    best = ROOT / "outputs" / "train" / "weights" / "best.pt"
    if best.exists():
        shutil.copy2(best, ROOT / "outputs" / "best.pt")
        print(f"\n[OK] best model -> {ROOT / 'outputs' / 'best.pt'}")


if __name__ == "__main__":
    main()
