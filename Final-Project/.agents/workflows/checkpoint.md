---
description: ตรวจว่าผ่าน checkpoint ของ phase ปัจจุบันหรือยัง
---

1. Read `ROADMAP.md` and find the most recent checkpoint that is not yet marked `✅`.
2. Verify it for real, not from memory:
   - Day 5 "Dataset พร้อมฝึก": load `dataset/processed/train.parquet`, print shape, date range, missing-value count, and CMF distribution.
   - Day 10 "MAE < 1.0 UVI": load the saved model and metrics, re-run evaluation on the last time-based fold, print MAE/RMSE on the UVI scale and recall for สูงมาก / รุนแรงมาก.
   - Day 15 "LSTM decided + CNN works": confirm the day-12 LSTM decision is recorded (XGBoost kept) and re-run the sky-CNN evaluation on each dataset's own test split (CCSN, SWIMCAT-ext, SWIMSEG if present) plus the red/blue cloud-fraction baseline; there is no stacking ensemble.
   - Day 21 "แอปครบวงจร": start the API, call `/health` and `/predict`, and confirm the Expo app builds (`npx expo export` or `npx expo start` without errors).
   - Day 24 "แจ้งเตือนบนมือถือจริง": check `notifications_log` has sends; remind the user this must be confirmed on a real phone.
3. Report in Thai as a short table: criterion, measured value, pass/fail.
4. If passed, mark the checkpoint line in `ROADMAP.md` with `✅` and commit. If failed, list the smallest fixes needed and, if the schedule is at risk, point to the cut-order list at the bottom of `ROADMAP.md`.
