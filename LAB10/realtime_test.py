import argparse
import time
from pathlib import Path

import cv2
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent
COLORS = {"cat": (255, 140, 0), "dog": (0, 200, 0)}  # BGR


def parse_args():
    ap = argparse.ArgumentParser(description="Real-time cat/dog detection")
    ap.add_argument("--weights", default=str(ROOT / "outputs" / "best.pt"))
    ap.add_argument("--source", default="0", help="เลข index ของกล้อง หรือ path วิดีโอ")
    ap.add_argument("--conf", type=float, default=0.4)
    ap.add_argument("--imgsz", type=int, default=416)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--save", action="store_true", help="บันทึกวิดีโอผลลัพธ์")
    ap.add_argument("--no-show", action="store_true", help="ไม่เปิดหน้าต่าง (ใช้บน server/Colab)")
    return ap.parse_args()


def main():
    args = parse_args()
    model = YOLO(args.weights)
    source = int(args.source) if args.source.isdigit() else args.source
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise SystemExit(f"[ERROR] เปิด source ไม่ได้: {args.source}")

    out_dir = ROOT / "outputs" / "realtime"
    out_dir.mkdir(parents=True, exist_ok=True)
    writer = None
    if args.save:
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps_in = cap.get(cv2.CAP_PROP_FPS) or 20
        writer = cv2.VideoWriter(str(out_dir / "realtime_result.mp4"),
                                 cv2.VideoWriter_fourcc(*"mp4v"), fps_in, (w, h))

    fps, prev = 0.0, time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        r = model.predict(frame, conf=args.conf, imgsz=args.imgsz, device=args.device, verbose=False)[0]
        counts = {"cat": 0, "dog": 0}
        for b in r.boxes:
            x1, y1, x2, y2 = map(int, b.xyxy[0].tolist())
            name = model.names[int(b.cls)]
            counts[name] = counts.get(name, 0) + 1
            color = COLORS.get(name, (0, 0, 255))
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{name} {float(b.conf):.2f}", (x1, max(20, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        now = time.time()
        fps = 0.9 * fps + 0.1 * (1.0 / max(now - prev, 1e-6))
        prev = now
        info = f"FPS: {fps:.1f} | cat: {counts['cat']} | dog: {counts['dog']}"
        cv2.rectangle(frame, (0, 0), (360, 30), (0, 0, 0), -1)
        cv2.putText(frame, info, (8, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        if writer:
            writer.write(frame)
        if args.no_show:
            continue
        cv2.imshow("Real-time Cat/Dog Detection (q = quit, s = snapshot)", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("s"):
            p = out_dir / f"snapshot_{int(now)}.jpg"
            cv2.imwrite(str(p), frame)
            print(f"[saved] {p}")

    cap.release()
    if writer:
        writer.release()
        print(f"[OK] saved video -> {out_dir / 'realtime_result.mp4'}")
    if not args.no_show:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
