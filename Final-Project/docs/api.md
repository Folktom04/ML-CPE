# UV Guard API (day 16)

FastAPI service in `source_code/api/`. It loads the day-10 final models once at start-up
(multi-output XGBoost, quantile XGBoost + frozen CQR `Q = 0.0379`, sky-CNN TFLite).

**Run** (from `Final-Project/`, Windows PowerShell):

```powershell
$env:PYTHONPATH = "source_code"
.venv\Scripts\python.exe -m uvicorn api.main:app --app-dir source_code --port 8000
```

Interactive docs: http://127.0.0.1:8000/docs

**CORS (day 18):** browsers may call the API only from the origins in `CORS_ORIGINS` (`.env`, comma-separated); the default is the Expo web dev server `http://localhost:8081` and `http://127.0.0.1:8081`. Methods GET/POST/PUT/DELETE, headers `Content-Type` and `X-Device-Id` (day 19). Native apps send no `Origin` header, so CORS does not affect them.

## Data flow
- **Run-time inputs:** Open-Meteo Forecast API (`api.open-meteo.com/v1/forecast`) and Air Quality API. They use the same 12 weather and 4 air-quality variables as training, with no `models=`/`domains=` (Open-Meteo defaults, as in training), `past_days=1` and `forecast_days=2`. Responses are cached in memory for 10 min per location (rounded to 0.01°). **Live fetch budget (day 19):** each request gets at most 2 retries (on connection errors, timeouts, 429/5xx; pauses 0.5 s then 1 s) with a 5 s timeout per attempt, and the weather + air-quality requests share one **15 s** deadline, so `/predict` answers or returns 502 before the app gives up at 20 s. Before day 19 the live fetch used the training session (5 retries, backoff 2 s, 30 s timeout), which could take over a minute. The training downloads in `src/fetch_data.py` keep those long retries. **NASA POWER is never called by the API.**
- **Train/serve consistency (day 16):** for the same hours, the Historical Forecast API (used for training) and the Forecast API returned identical values (16/16 variables, 72/72 h). `build_features()` reproduces the 23 training features exactly (7,394 rows compared, max difference 0, tolerance 1e-6).
- **Point vs range:** the point UVI/UVA/UVB comes from the multi-output model; the range is q10–q90 after CQR. The point value is never clipped. If it falls outside [q10, q90], `uvi_range` is widened to include it and `interval_adjusted` is `true` (this happened in 0 of 3,726 dev-2024 hours). **Alert level, burn time, advice and `next_safe_time` use `alert_uvi = max(uvi_q90_cqr, uvi)`** (fixed on day 17), so a warning is never below the value shown.
- **Missing live data (fixed on day 17):** missing hours are re-inserted, implausible values masked, gaps up to 3 h interpolated (as in training) and edge gaps up to 3 h filled from the nearest hour; those hours have `data_imputed: true`. Hours still incomplete are dropped and logged. If the current hour is missing, `/predict` returns **503** and never uses another hour. Air quality is left-joined to weather, so a short air-quality forecast no longer removes hours.
- **Times** are the local start of the hourly interval (Asia/Bangkok), e.g. `13:00` = mean over 13:00–14:00.
- **Every response and error** includes `disclaimer`: "ค่านี้เป็นการประมาณเพื่อการศึกษาและการเตือนเท่านั้น ไม่ใช่การวินิจฉัยทางการแพทย์".
- **Area (day 21):** only points inside the Thailand box (5.5–20.5 N, 97.3–105.7 E) are served. Outside it, `/predict` and `/forecast` answer **422** `"รองรับเฉพาะพื้นที่ประเทศไทย"` before any Open-Meteo request. The model was trained and tested at Pathum Thani only, so for a place more than **50 km** away `note` is `"ความแม่นยำนอกพื้นที่ปทุมธานียังไม่ได้ประเมิน"` (`inference.training_area_note`, haversine distance); otherwise `note` is `null`. Before day 21, points outside Thailand got a 200 with a note.

## Endpoints

| Method | Path | Input | Output |
|---|---|---|---|
| GET | `/health` | — | `status`, model files, `sky_backend` (`ai_edge_litert` or fallback `tf.lite`), `cqr_q`, `db_backend` (`postgresql` or `sqlite`), `db_fallback`, `db_ok` (day 17) |
| POST | `/predict` | `{lat, lon, skin_type}` (skin type I–VI or 1–6) | `uvi, uvi_range, uva_wm2, uvb_wm2, level, skin_type, burn_minutes, cmf, advice, forecast[{time, uvi, …}], next_safe_time` + `uvi_q90_cqr, alert_uvi, alert_level, interval_adjusted, data_imputed, level_color, time, is_daylight, note, disclaimer` |
| GET | `/forecast?lat&lon&hours=1..36` | — | hourly `{time, uvi, uvi_range, uva_wm2, uvb_wm2, level, interval_adjusted, data_imputed, alert_uvi, is_daylight}` (`alert_uvi` = max(q90 after CQR, uvi), `is_daylight` = clear-sky UVI ≥ 0.5; both added on day 22 for the app's local alerts; also in `/predict.forecast`) |
| POST | `/users` | header `X-Device-Id` (16–64 letters/digits/dashes, a random UUID made by the app); body `{skin_type, notify_enabled?, alert_threshold? (3–11), alert_burn_minutes? (5–240), province?}` | 201 new user / 200 same device registered again: `{id, skin_type, province, notify_enabled, alert_threshold, safe_threshold, alert_burn_minutes, updated_at}` (never the device id) |
| PUT | `/users/{id}/settings` | header `X-Device-Id` of that user; any of the fields above (`safe_threshold` is rejected: 422) | the updated user |
| DELETE | `/users/{id}` | header `X-Device-Id` of that user | 204; the user and, through `ON DELETE CASCADE`, their push tokens, measurements and notification log are deleted |
| POST | `/sky-image` | multipart `file` (≤ 10 MB) | `sky_class` (SWIMCAT-ext, 6 classes) + `sky_class_th`, `sky_confidence`, `sky_class_probs`, `cloud_fraction_rb` (red/blue proxy), `cloud_fraction_cnn` (SWIMSEG head, only while its test passed), `reliability`, `stored: false` |

`next_safe_time` is the first hour, starting now, whose `alert_uvi` is at WHO level "ต่ำ", or `null` if there is none in the forecast.

**Sky image:** processed in memory only and never written to disk or a database. The result is **supporting information only and never changes the UVI** (`/predict` takes no image). **The main result is the SWIMCAT-ext head** (6 sky classes, Thai name and `sky_confidence` = softmax probability of the chosen class), which passed its test criteria (0.967). The CCSN head (11 genera and the 4 UV cloud groups) missed its criteria (UV-group accuracy 0.685 < 0.75), so since day 18 `/sky-image` no longer returns `genus` or `cloud_group`; the app does not show them. The raw outputs of both heads are still available in Python through `src.sky_infer.predict_heads()`. `reliability` describes `sky_class`, `cloud_fraction_rb` and (when sent) `cloud_fraction_cnn`. None has been tested on phone photos.

**Cloud-fraction head (after day 20):** `cloud_fraction_cnn` is the cloud fraction **in the photo, not of the whole sky**, from a SWIMSEG-trained head on the frozen day-14 backbone (separate `sky_cloud_v1.tflite`; the day-14 `sky_cnn_v1.tflite` is unchanged). `ModelBundle.load()` loads it only when `docs/sky_cloud_test.json` says `ships: true` (it passed C1 MAE ≤ 0.10 and C2 ≥ 0.03 better than red/blue: 0.084 vs 0.145 on 141 test patches from 5 days). Otherwise the field is left out of the response entirely. It shrinks towards mid values (a clear blue photo gives ~0.15) and was trained on Singapore whole-sky-imager patches, not phone photos.

**EXIF (day 20):** the app takes the photo with `exif: false` and always uploads a copy re-encoded by expo-image-manipulator (longest side 1024 px, JPEG 0.8). Android `Bitmap.compress` and iOS `jpegData` write pixels only, so no GPS, time or phone model is sent. The app deletes both temporary files in `finally`, even when the upload fails. The API logs only `sky-image upload has_exif=<bool>` (`src.sky_infer.has_exif`) and never the EXIF values. This lets a phone test confirm that nothing leaked. The logger `uvguard.api` prints INFO under uvicorn since day 20 (`configure_logging()`); before that its INFO lines, e.g. "models loaded", were not shown at all. It logs only user ids, counts, backend names and this boolean.

**Users (day 19):** a user is one installed app, identified only by a random device id. The device id works as a bearer secret: `PUT`/`DELETE` need the matching `X-Device-Id` (constant-time compare), otherwise **403**; an unknown id is **404**; a missing or malformed header on `POST` is **400**. The device id is never returned and **never logged**: the header is read as a plain string (so no validation error echoes it), logs name only the user id, database errors are logged by class name only, and the engine uses `hide_parameters=True` so SQL errors never contain bound values. **Hysteresis:** `safe_threshold = alert_threshold − 2` is set by the server (6→4, 8→6, 11→9), so `safe_threshold < alert_threshold` always holds. **One rounding rule (day 19):** levels, colours and alert thresholds all use the WHO rounding `round_uvi()` (nearest integer, x.5 up): `who_level` (chart hours), `risk.assess` (main card), and `risk.reaches_alert(uvi, alert_threshold)` / `risk.is_safe_again(uvi, safe_threshold)`, which the day-23 notification job must use. So 7.8 is สูงมาก everywhere and reaches an alert of 8; a raw `7.8 >= 8` would not. The app mirrors it in `roundUvi` / `reachesAlert` / `isSafeAgain`, and both test suites read the same cases from `source_code/tests/who_rounding_cases.json`. The app sends these settings only after the user gives explicit consent in Settings (skin type is health-related data, see `docs/db.md`).

Errors: 400 (`X-Device-Id` missing/malformed), 403 (device id does not match), 404 (unknown user), 409 (database constraint conflict; the database's own error text is never returned or logged), 422 (validation, or outside Thailand: `"รองรับเฉพาะพื้นที่ประเทศไทย"`), 413 (image too large), 415 (not an image), 502 (Open-Meteo unavailable), 503 (current hour missing from Open-Meteo, or database unavailable), 500 — all carry `disclaimer`.

## Smoke test (27 Sep 2026, ~13:10 Bangkok, Pathum Thani, skin type III)
`/predict`: UVI **5.49**, range **[4.94, 6.66]**, level **ปานกลาง**, alert level (q90) **สูง**, burn time 35 min, CMF 0.497, next safe time 16:00. Open-Meteo `uv_index` for the same hour: **2.95** (clear-sky 7.9, cloud cover 100 %). Open-Meteo's known low bias is documented on day 2 and day 10 (2025 test vs OMI: Open-Meteo MAE 2.36, bias −2.12).
