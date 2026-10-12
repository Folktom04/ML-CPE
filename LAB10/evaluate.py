import argparse
import json
from pathlib import Path

from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent


def parse_args():
    ap = argparse.ArgumentParser(description="Evaluate YOLOv8 Cat/Dog detector")
    ap.add_argument("--weights", default=str(ROOT / "outputs" / "best.pt"))
    ap.add_argument("--data", default=str(ROOT / "dataset" / "data.yaml"))
    ap.add_argument("--split", default="test", choices=["train", "val", "test"])
    ap.add_argument("--imgsz", type=int, default=416)
    ap.add_argument("--conf", type=float, default=0.001)
    ap.add_argument("--iou", type=float, default=0.6)
    ap.add_argument("--device", default="cpu")
    return ap.parse_args()


def main():
    args = parse_args()
    model = YOLO(args.weights)
    m = model.val(
        data=args.data,
        split=args.split,
        imgsz=args.imgsz,
        conf=args.conf,
        iou=args.iou,
        device=args.device,
        project=str(ROOT / "outputs"),
        name=f"eval_{args.split}",
        exist_ok=True,
        plots=True,
    )

    names = model.names
    result = {
        "split": args.split,
        "weights": str(Path(args.weights).name),
        "precision": round(float(m.box.mp), 4),
        "recall": round(float(m.box.mr), 4),
        "mAP50": round(float(m.box.map50), 4),
        "mAP50_95": round(float(m.box.map), 4),
        "per_class": {},
        "speed_ms_per_image": {k: round(v, 2) for k, v in m.speed.items()},
    }
    for i, c in enumerate(m.box.ap_class_index):
        p, r, ap50, ap = m.box.class_result(i)
        result["per_class"][names[int(c)]] = {
            "precision": round(float(p), 4), "recall": round(float(r), 4),
            "mAP50": round(float(ap50), 4), "mAP50_95": round(float(ap), 4),
        }

    print("\n========== Evaluation ==========")
    print(f"{'class':<8}{'P':>8}{'R':>8}{'mAP50':>9}{'mAP50-95':>10}")
    print(f"{'all':<8}{result['precision']:>8.3f}{result['recall']:>8.3f}"
          f"{result['mAP50']:>9.3f}{result['mAP50_95']:>10.3f}")
    for c, v in result["per_class"].items():
        print(f"{c:<8}{v['precision']:>8.3f}{v['recall']:>8.3f}"
              f"{v['mAP50']:>9.3f}{v['mAP50_95']:>10.3f}")

    out = ROOT / "outputs" / f"metrics_{args.split}.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[OK] saved -> {out}")


if __name__ == "__main__":
    main()
