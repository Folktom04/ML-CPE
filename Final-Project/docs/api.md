# UV Guard API (day 16)

FastAPI service in `source_code/api/`. It loads the day-10 final models once at start-up
(multi-output XGBoost, quantile XGBoost + frozen CQR `Q = 0.0379`, sky-CNN TFLite).

**Run** (from `Final-Project/`, Windows PowerShell):

```powershell
$env:PYTHONPATH = "source_code"
.venv\Scripts\python.exe -m uvicorn api.main:app --app-dir source_code --port 8000
```

Interactive docs: http://127.0.0.1:8000/docs

## Data flow
- **Run-time inputs:** Open-Meteo Forecast API (`api.open-meteo.com/v1/forecast`) and Air Quality API. They use the same 12 weather and 4 air-quality variables as training, with no `models=`/`domains=` (Open-Meteo defaults, as in training), `past_days=1` and `forecast_days=2`. Responses are cached in memory for 10 min per location (rounded to 0.01°). **NASA POWER is never called by the API.**
- **Train/serve consistency (day 16):** for the same hours, the Historical Forecast API (used for training) and the Forecast API returned identical values (16/16 variables, 72/72 h). `build_features()` reproduces the 23 training features exactly (7,394 rows compared, max difference 0, tolerance 1e-6).
- **Point vs range:** the point UVI/UVA/UVB comes from the multi-output model; the range is q10–q90 after CQR. The point value is never clipped. If it falls outside [q10, q90], `uvi_range` is widened to include it and `interval_adjusted` is `true` (this happened in 0 of 3,726 dev-2024 hours). **Alert level, burn time, advice and `next_safe_time` use `alert_uvi = max(uvi_q90_cqr, uvi)`** (fixed on day 17), so a warning is never below the value shown.
- **Missing live data (fixed on day 17):** missing hours are re-inserted, implausible values masked, gaps up to 3 h interpolated (as in training) and edge gaps up to 3 h filled from the nearest hour; those hours have `data_imputed: true`. Hours still incomplete are dropped and logged. If the current hour is missing, `/predict` returns **503** and never uses another hour. Air quality is left-joined to weather, so a short air-quality forecast no longer removes hours.
- **Times** are the local start of the hourly interval (Asia/Bangkok), e.g. `13:00` = mean over 13:00–14:00.
- **Every response and error** includes `disclaimer`: "ค่านี้เป็นการประมาณเพื่อการศึกษาและการเตือนเท่านั้น ไม่ใช่การวินิจฉัยทางการแพทย์".
- Model trained on Pathum Thani only; a `note` is added for locations outside Thailand.

## Endpoints

| Method | Path | Input | Output |
|---|---|---|---|
| GET | `/health` | — | `status`, model files, `sky_backend` (`ai_edge_litert` or fallback `tf.lite`), `cqr_q` |
| POST | `/predict` | `{lat, lon, skin_type}` (skin type I–VI or 1–6) | `uvi, uvi_range, uva_wm2, uvb_wm2, level, skin_type, burn_minutes, cmf, advice, forecast[{time, uvi, …}], next_safe_time` + `uvi_q90_cqr, alert_uvi, alert_level, interval_adjusted, data_imputed, level_color, time, is_daylight, note, disclaimer` |
| GET | `/forecast?lat&lon&hours=1..36` | — | hourly `{time, uvi, uvi_range, uva_wm2, uvb_wm2, level, interval_adjusted, data_imputed}` |
| POST | `/sky-image` | multipart `file` (≤ 10 MB) | `cloud_group` (+ Thai, probabilities), `genus`, `sky_class` (+ probabilities), `cloud_fraction_rb`, `reliability`, `stored: false` |

`next_safe_time` is the first hour, starting now, whose `alert_uvi` is at WHO level "ต่ำ", or `null` if there is none in the forecast.

**Sky image:** processed in memory only and never written to disk or a database. The result is **supporting information only and never changes the UVI** (`/predict` takes no image). `reliability` states plainly that the cloud-group output missed its test criterion (UV-group accuracy 0.685 < 0.75) and that the sky-class output passed (0.967). Neither has been tested on phone photos.

Errors: 422 (validation), 413 (image too large), 415 (not an image), 502 (Open-Meteo unavailable), 503 (current hour missing from Open-Meteo), 500 — all carry `disclaimer`.

## Smoke test (27 Sep 2026, ~13:10 Bangkok, Pathum Thani, skin type III)
`/predict`: UVI **5.49**, range **[4.94, 6.66]**, level **ปานกลาง**, alert level (q90) **สูง**, burn time 35 min, CMF 0.497, next safe time 16:00. Open-Meteo `uv_index` for the same hour: **2.95** (clear-sky 7.9, cloud cover 100 %). Open-Meteo's known low bias is documented on day 2 and day 10 (2025 test vs OMI: Open-Meteo MAE 2.36, bias −2.12).
