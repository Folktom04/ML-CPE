"""UV Guard FastAPI service (day 16).

Run from the project root::

    $env:PYTHONPATH = "source_code"
    .venv\\Scripts\\python.exe -m uvicorn api.main:app --app-dir source_code --port 8000

Data sources at run time: Open-Meteo Forecast + Air Quality only (``src.inference``); NASA
POWER is never called. Uploaded sky photos are processed in memory and never stored. The sky
CNN result is supporting information only and is never used to change the UVI.
"""

from __future__ import annotations

import io
import json
import logging
from contextlib import asynccontextmanager
from typing import Any

import numpy as np
import requests
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

from api.schemas import (
    ErrorResponse,
    ForecastResponse,
    HealthResponse,
    HourUV,
    PredictRequest,
    PredictResponse,
    SkyImageResponse,
)
from src import inference as inf
from src.metrics import WHO_LEVELS, who_level
from src.risk import DISCLAIMER, assess
from src.sky_data import load_image
from src.sky_infer import predict_sky
from src.train_cmf import DOCS_DIR

MAX_IMAGE_BYTES = 10 * 1024 * 1024
OUTSIDE_NOTE = "ตำแหน่งอยู่นอกประเทศไทย โมเดลฝึกด้วยข้อมูลของปทุมธานีเท่านั้น ค่าอาจคลาดเคลื่อนมาก"
log = logging.getLogger("uvguard.api")


def sky_reliability() -> dict[str, str]:
    """Plain statement of how reliable each sky-CNN output was on its test split (day 14).

    Returns:
        ``{"cloud_group": ..., "sky_class": ...}`` (Thai text with the test numbers).
    """
    try:
        t = json.loads((DOCS_DIR / "sky_cnn_test.json").read_text(encoding="utf-8"))
        g = t["ccsn"]["mean"]["group_accuracy"]
        s = t["swim"]["mean"]["group_accuracy"]
        return {
            "cloud_group": f"ไม่ผ่านเกณฑ์ที่ตั้งไว้ (ความแม่นบนชุดทดสอบ {g:.0%} เกณฑ์ 75%) ใช้ประกอบเท่านั้น",
            "sky_class": f"ผ่านเกณฑ์ (ความแม่นบนชุดทดสอบ {s:.0%}) แต่ยังไม่ได้ทดสอบกับภาพจากมือถือ",
        }
    except (OSError, KeyError, ValueError):
        return {"cloud_group": "ไม่มีข้อมูลผลทดสอบ", "sky_class": "ไม่มีข้อมูลผลทดสอบ"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models once at start-up (tests may pre-set ``app.state.bundle``)."""
    if getattr(app.state, "bundle", None) is None:
        app.state.bundle = inf.ModelBundle.load()
    app.state.sky_reliability = sky_reliability()
    log.info("models loaded (sky backend: %s)", app.state.bundle.sky_backend)
    yield


app = FastAPI(title="UV Guard API", version="0.16.0", lifespan=lifespan)


def _error(status: int, detail: Any) -> JSONResponse:
    """JSON error that still carries the disclaimer."""
    return JSONResponse(status_code=status, content=ErrorResponse(detail=detail).model_dump())


@app.exception_handler(RequestValidationError)
async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """422 with the disclaimer."""
    return _error(422, json.loads(json.dumps(exc.errors(), default=str)))


@app.exception_handler(HTTPException)
async def _http_error(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP errors with the disclaimer."""
    return _error(exc.status_code, exc.detail)


@app.exception_handler(Exception)
async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
    """500 with the disclaimer (details only in the server log)."""
    log.exception("unhandled error")
    return _error(500, "internal error")


def _live_predictions(lat: float, lon: float):
    """Fetch Open-Meteo, build features and predict every hour."""
    try:
        raw = inf.fetch_live(lat, lon)
    except requests.RequestException as exc:
        raise HTTPException(502, f"Open-Meteo unavailable: {exc.__class__.__name__}") from exc
    feat = inf.build_features(raw, lat, lon)
    if feat.empty:
        raise HTTPException(502, "Open-Meteo returned no usable hours")
    return inf.predict_hours(feat, app.state.bundle)


def _hour(row: Any) -> HourUV:
    """One prediction row as a ``HourUV``."""
    return HourUV(
        time=inf.hour_start_local(row.time_utc),
        uvi=round(float(row.uvi), 2),
        uvi_range=[round(float(row.uvi_lo), 2), round(float(row.uvi_hi), 2)],
        uva_wm2=round(float(row.uva_wm2), 3),
        uvb_wm2=round(float(row.uvb_wm2), 4),
        level=WHO_LEVELS[int(who_level(row.uvi))],
        interval_adjusted=bool(row.interval_adjusted),
        data_imputed=bool(row.data_imputed),
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Service status and the loaded model files."""
    b = app.state.bundle
    return HealthResponse(status="ok", models=b.files, sky_backend=b.sky_backend, cqr_q=b.cqr_q)


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    """UV now + risk for the user's skin type + hourly forecast.

    The displayed level follows the point UVI; alert level, burn time and advice follow
    ``alert_uvi = max(q90 after CQR, point UVI)``, so a warning is never below the value shown.
    If the current hour is missing from the live data the answer is 503 (never another hour).
    """
    pred = _live_predictions(req.lat, req.lon)
    now = inf.utc_now()
    try:
        i = inf.current_index(pred, now)
    except inf.NoCurrentHourError as exc:
        raise HTTPException(503, "Open-Meteo data for the current hour is missing") from exc
    row = pred.iloc[i]
    r = assess(
        float(row.uvi),
        (float(row.uvi_lo), float(row.uvi_hi)),
        req.skin_type,
        alert_uvi=float(row.alert_uvi),
    )
    upcoming = [_hour(x) for x in pred.iloc[i + 1 : i + 25].itertuples()]
    return PredictResponse(
        uvi=round(float(row.uvi), 2),
        uvi_range=[round(float(row.uvi_lo), 2), round(float(row.uvi_hi), 2)],
        uva_wm2=round(float(row.uva_wm2), 3),
        uvb_wm2=round(float(row.uvb_wm2), 4),
        level=r["level"],
        skin_type=r["skin_type"],
        burn_minutes=r["burn_minutes"],
        cmf=None if np.isnan(row.cmf) else round(float(row.cmf), 3),
        advice=r["advice"],
        forecast=upcoming,
        next_safe_time=inf.next_safe_time(pred, now),
        time=inf.hour_start_local(row.time_utc),
        is_daylight=bool(row.is_day),
        level_en=r["level_en"],
        level_color=r["color"],
        uvi_q90_cqr=round(float(row.q90), 2),
        alert_uvi=round(float(row.alert_uvi), 2),
        alert_level=r["alert_level"],
        interval_adjusted=bool(row.interval_adjusted),
        data_imputed=bool(row.data_imputed),
        note=None if inf.in_thailand(req.lat, req.lon) else OUTSIDE_NOTE,
        disclaimer=DISCLAIMER,
    )


@app.get("/forecast", response_model=ForecastResponse)
def forecast(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    hours: int = Query(24, ge=1, le=36),
) -> ForecastResponse:
    """Hourly UVI/UVA/UVB forecast (same XGBoost on Open-Meteo forecast features)."""
    pred = _live_predictions(lat, lon)
    i = inf.current_index(pred, inf.utc_now(), strict=False)
    return ForecastResponse(
        lat=lat,
        lon=lon,
        hours=[_hour(x) for x in pred.iloc[i : i + hours].itertuples()],
        note=None if inf.in_thailand(lat, lon) else OUTSIDE_NOTE,
    )


@app.post("/sky-image", response_model=SkyImageResponse)
async def sky_image(file: UploadFile = File(...)) -> SkyImageResponse:
    """Sky photo -> cloud group / sky class / red-blue cloud fraction (in memory only).

    The bytes are never written to disk or a database; the result never changes the UVI.
    """
    data = await file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "image larger than 10 MB")
    try:
        Image.open(io.BytesIO(data)).verify()
        img = load_image(io.BytesIO(data))
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(415, "not a readable image") from exc
    res = predict_sky(img, interpreter=app.state.bundle.sky)
    return SkyImageResponse(**res, reliability=app.state.sky_reliability, stored=False)
