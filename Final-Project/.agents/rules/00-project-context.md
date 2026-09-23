---
trigger: always_on
---

# UV Guard — Project Context

## What we are building
A 30-day student ML project (Computer Engineering, RMUTT, Thailand). The system estimates UV Index (UVI), UVA and UVB at the user's location, turns them into a personal skin-damage risk (Fitzpatrick skin type I–VI), and warns the user through a mobile app with notifications.

Pipeline:
input (GPS, time, weather/air-quality API, phone lux sensor, sky photo)
→ feature engineering
→ physics clear-sky model (UVI, UVA, UVB)
→ ML predicts Cloud Modification Factor (CMF, 0–1): XGBoost multi-output + CNN sky features → stacking ensemble
→ UV = clear_sky × CMF, with a quantile range (q10–q90)
→ Risk Engine (WHO level, minutes to sunburn, SPF/PA advice)
→ FastAPI → Expo app + notifications. LSTM gives a 6–24 h forecast.

The source of truth for scope and schedule is `ROADMAP.md`. Read it before starting any task and tick `[x]` items you finish.

## Tech stack (do not swap without asking)
- ML: Python 3.11, pandas, numpy, pvlib, xgboost, lightgbm, scikit-learn, optuna, tensorflow/keras
- Backend: FastAPI, SQLAlchemy, PostgreSQL (SQLite allowed only as a fallback), APScheduler
- Mobile: React Native with Expo (TypeScript), expo-notifications, expo-camera, expo-sensors, expo-location
- Data: Open-Meteo APIs (no API key). Default location: Pathum Thani, lat 14.02, lon 100.52, timezone Asia/Bangkok
- Smartphone only: NO external sensors or hardware modules. The only inputs are what a phone provides (GPS, clock, camera, ambient light sensor on Android, accelerometer/gyroscope) plus free web APIs. Do not suggest ESP32, VEML6075 or any add-on device.
- Sky-image CNN is trained ONLY on public datasets — no photos taken by the user: CCSN (normal-camera cloud photos, 11 classes), SWIMCAT (5 sky classes), SWIMSEG (cloud masks), SKIPP'D or NREL CloudCV (sky images paired with PV power / irradiance). Most are fisheye whole-sky images, so reduce the domain gap with centre-crop + perspective transform + colour/brightness augmentation, and report the domain gap as a limitation. SKIPP'D/CloudCV targets are broadband, not UV — treat them as an approximate cloud-attenuation proxy. Check and cite each dataset's license. Photos taken in the app are used for inference/demo only, never for training.
- Training data sources:
  - Open-Meteo Weather/Historical (features only — its uv_index / uv_index_clear_sky may be used as input features but NOT as a target; see "Ground truth")
  - Open-Meteo Air Quality / CAMS (aerosol_optical_depth, dust, pm2_5, ozone)
  - NASA POWER hourly API, community RE — not AG, which rounds to 0.01 MJ/hr (2.78 W/m² steps) and erases UVB; RE hourly Wh/m² = mean W/m² (ALLSKY_SFC_UVA, ALLSKY_SFC_UVB, ALLSKY_SFC_UV_INDEX, ALLSKY/CLRSKY_SFC_SW_DWN, CLOUD_AMT) → CMF_UVI / CMF_A / CMF_B targets (ground truth). Coarse satellite grid — combine with physics, never replace it. Check units (W/m²) against the physics module.
- Independent validation sources (NEVER use for training, feature selection or tuning — test only): TEMIS/KNMI daily noon UVI (clear-sky and cloudy), NASA OMI OMUVB daily overpass (UVI + irradiance at 305/310/324/380 nm; fetch with `earthaccess`, needs an Earthdata login in `.env`). Report error separately per source.
  - Validation split: TEMIS/OMI data from **2023 only** may be used, and only in `source_code/notebooks/02_source_selection.ipynb`, to choose the training target source (Open-Meteo vs NASA POWER uv_index) — done, see "Ground truth". TEMIS/OMI **2024–2025 is the held-out test set**: do not download OMI for it, and do not load, plot, print statistics of or otherwise inspect it before day 10 (printing a row count is allowed). Code must read validation data through `src.fetch_validation.load_validation()`, which returns 2023 unless `split="test"` is passed.
  - TEMIS Bangkok (13.667N, 100.612E) only has clear-sky UVI (cloud-modified columns are -1 outside the MSG area); cloudy validation UVI comes from OMI only.
- Store validation files in `dataset/validation/`.
- Ground truth: **NASA POWER** hourly `ALLSKY_SFC_UV_INDEX`, `ALLSKY_SFC_UVA`, `ALLSKY_SFC_UVB` (satellite/model-based). Decided on day 2 in `02_source_selection.ipynb` with a rule declared before looking at results (primary metric: MAE vs OMI all-sky noon UVI, 2023; pick NASA POWER only if its MAE is lower by more than 0.3 UVI, otherwise Open-Meteo). Result: NASA POWER 1.143 vs Open-Meteo 2.428 (n=275); Open-Meteo saturates near UVI 9.3 and its clear-sky UVI is ~3.5 below TEMIS. State clearly in docs/report that no physical UV instrument was used.
  - NASA POWER is not real-time (months of latency), so it is used for training targets only. At inference the model runs on Open-Meteo / phone inputs. Field validation compares phone-based estimates with the Open-Meteo API at the same time and place; report Open-Meteo's known low bias alongside.

## Repository layout
The project lives in `ML-CPE/Final-Project/`, a folder of the course repo `ML-CPE` (git root is the parent folder — do NOT run `git init` here). The course template requires `dataset/`, `source_code/`, `README.md` and `report.pdf` at this level; keep them.
```
Final-Project/                 # project root (open this folder in Antigravity / Claude Code)
├── dataset/
│   ├── raw/                   # API downloads (git-ignored)
│   ├── processed/             # train.parquet etc. (git-ignored)
│   ├── validation/            # TEMIS / OMI — test only (git-ignored)
│   ├── field/                 # data collected with the phone app
│   └── sky/                   # public sky-image datasets (git-ignored)
├── source_code/
│   ├── src/                   # importable Python package code (import as `from src.physics import ...`)
│   ├── tests/                 # pytest
│   ├── notebooks/             # numbered: 01_eda.ipynb, 02_baseline.ipynb ...
│   ├── models/                # saved models
│   ├── api/                   # FastAPI service
│   └── app/                   # Expo app
├── docs/                      # diagrams, figures, report assets
├── README.md
├── report.pdf                 # final report (course deliverable)
└── ROADMAP.md
```
Run all commands from `Final-Project/`. `pytest.ini` sets `pythonpath = source_code`, so `pytest -q` works from here.

## Domain constants (use exactly these)
- 1 UVI = 0.025 W/m² erythemal irradiance
- Clear-sky UVI (Madronich approx.): UVI = 12.5 · μ^2.42 · (O3/300)^-1.23, μ = cos(solar zenith), clipped at 0
- Ozone input O3 (total column, DU): the monthly climatology `source_code/models/ozone_climatology_v1.json` (built from NASA POWER TO3 2023–2025, Asia/Bangkok months), read with `src.physics.ozone_climatology()`. Use it by default for BOTH training targets and the app/API (train–serve consistency), and to fill TO3 gaps. Do not use a constant 300 DU (−15 % UVI bias in the tropics). Surface ozone from Open-Meteo (µg/m³) is NOT column ozone.
- MED (J/m²) by skin type: I 200, II 250, III 350, IV 450, V 600, VI 1000
- Minutes to burn = MED / (UVI × 0.025 × 60); always use the UPPER quantile of UVI for warnings
- WHO levels: 0–2 ต่ำ, 3–5 ปานกลาง, 6–7 สูง, 8–10 สูงมาก, 11+ รุนแรงมาก
- UVB band 280–315 nm, UVA band 315–400 nm (pvlib spectrl2 starts at 300 nm — note this in docs)
- CMF targets (all from NASA POWER, skip rows where the clear-sky denominator is small — UVI < 0.5 — to avoid noise at dawn/dusk):
  - CMF_UVI = nasa ALLSKY_SFC_UV_INDEX / `uvi_clear_interval(end_times, substeps=CMF_SUBSTEPS)` (Madronich averaged over the hour, climatology ozone; `src/physics.py`)
  - CMF_A = nasa ALLSKY_SFC_UVA / clear-sky UVA; CMF_B = nasa ALLSKY_SFC_UVB / clear-sky UVB, from `uva_uvb_clear_interval(end_times, substeps=CMF_SUBSTEPS)` (pvlib SPECTRL2, climatology ozone, **aod500 = 0**, PW 4 cm, albedo 0.2). The denominator is aerosol-free on purpose (decided day 4), so all three CMFs mean "cloud + aerosol" modification, like the Madronich-based CMF_UVI. Do not pass real AOD to the denominator; AOD / PM2.5 go in as model features.
  - UVB from SPECTRL2 covers 300–315 nm only (grid starts at 300 nm, 4 points: 300/305/310/315) while NASA POWER UVB is 280–315 nm; report this as a limitation.
  - Clear-sky denominators are the MEAN over the hourly interval (`CMF_SUBSTEPS = 12` instants), not the midpoint value, because NASA POWER values are hourly means. The midpoint differs by 6–13 % in the first/last daylight hour (notebook 03). Apply the same averaging to spectrl2 UVA/UVB.
  - The CMF also absorbs aerosol attenuation (Madronich has no aerosol term): on clear hours it is ~0.7–0.8 and falls with AOD, so AOD / PM2.5 must be model features.

## Working rules
- Always make an implementation plan first and wait for approval on any task that touches more than 3 files.
- Validation must be time-based (TimeSeriesSplit / chronological split). Never random-split time-series data.
- Every function in `source_code/src/` gets a docstring and a pytest test. Run `pytest -q` before saying a task is done.
- Never hard-code secrets; use `.env` + python-dotenv. Commit `.env.example`, never `.env`.
- Keep notebooks for exploration only; reusable logic goes into `source_code/src/`.
- Health wording: results are estimates for education and warning, not medical diagnosis. Keep that disclaimer in the app and README.
- Explain plans, walkthroughs and summaries to the user in Thai. Code, identifiers and commit messages stay in English.
