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
import os
from contextlib import asynccontextmanager
from typing import Any

import numpy as np
import requests
from api.schemas import (
    ErrorResponse,
    ForecastResponse,
    HealthResponse,
    HourUV,
    PredictRequest,
    PredictResponse,
    SkyImageResponse,
    UserCreate,
    UserResponse,
    UserSettingsUpdate,
)
from fastapi import (
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from src import db
from src import inference as inf
from src import users
from src.fetch_data import ROOT
from src.metrics import WHO_LEVELS, who_level
from src.risk import DISCLAIMER, assess
from src.sky_data import load_image
from src.sky_infer import has_exif, predict_sky
from src.train_cmf import DOCS_DIR

MAX_IMAGE_BYTES = 10 * 1024 * 1024
DEFAULT_CORS_ORIGINS = ["http://localhost:8081", "http://127.0.0.1:8081"]  # npx expo start --web
OUTSIDE_NOTE = "ตำแหน่งอยู่นอกประเทศไทย โมเดลฝึกด้วยข้อมูลของปทุมธานีเท่านั้น ค่าอาจคลาดเคลื่อนมาก"
log = logging.getLogger("uvguard.api")


def configure_logging(logger: logging.Logger = log) -> None:
    """Print the API's own INFO lines under uvicorn, which only configures its own loggers.

    Only ``uvguard.api`` is enabled; its lines hold user ids, counts and booleans, never a device
    id, coordinates or EXIF values. Idempotent (one handler at most).

    Args:
        logger: Logger to configure (the API logger by default).
    """
    if logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s:     %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def sky_reliability() -> dict[str, str]:
    """Plain statement of how reliable each sky-CNN output was on its test split (day 14).

    Only the outputs the app shows are described: the SWIMCAT-ext sky class and the red/blue
    cloud fraction. The CCSN head missed its criteria and is not returned by ``/sky-image``.

    Returns:
        ``{"sky_class": ..., "cloud_fraction_rb": ...}`` (Thai text with the test numbers).
    """
    rb = "ประมาณจากอัตราส่วนสีแดง/น้ำเงิน (ไม่ใช่โมเดล) ยังไม่ได้ทดสอบกับภาพจากมือถือ"
    try:
        t = json.loads((DOCS_DIR / "sky_cnn_test.json").read_text(encoding="utf-8"))
        s = t["swim"]["mean"]["group_accuracy"]
        return {
            "sky_class": f"ผ่านเกณฑ์ (ความแม่นบนชุดทดสอบ {s:.0%}) แต่ยังไม่ได้ทดสอบกับภาพจากมือถือ",
            "cloud_fraction_rb": rb,
        }
    except (OSError, KeyError, ValueError):
        return {"sky_class": "ไม่มีข้อมูลผลทดสอบ", "cloud_fraction_rb": rb}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models and create the DB engine once at start-up (tests may pre-set both)."""
    configure_logging()
    if getattr(app.state, "bundle", None) is None:
        app.state.bundle = inf.ModelBundle.load()
    if getattr(app.state, "db_engine", None) is None:
        url, app.state.db_fallback = db.database_url()  # logs a WARNING on the SQLite fallback
        app.state.db_engine = db.make_engine(url)
    log.info("database backend: %s", db.backend_name(app.state.db_engine))
    app.state.sky_reliability = sky_reliability()
    log.info("models loaded (sky backend: %s)", app.state.bundle.sky_backend)
    yield


def cors_origins(env: dict[str, str] | None = None) -> list[str]:
    """Browser origins allowed to call the API (the Expo web dev server by default).

    Args:
        env: Mapping to read instead of the process environment (tests). When None,
            ``.env`` at the project root is loaded first (existing variables win).

    Returns:
        Origins from comma-separated ``CORS_ORIGINS``, or ``DEFAULT_CORS_ORIGINS``.
    """
    if env is None:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
        env = dict(os.environ)
    raw = (env.get("CORS_ORIGINS") or "").strip()
    return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()] or DEFAULT_CORS_ORIGINS


app = FastAPI(title="UV Guard API", version="0.19.0", lifespan=lifespan)
# Native apps do not send an Origin header; CORS only matters for the Expo web build.
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-Device-Id"],
)


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


@app.exception_handler(IntegrityError)
async def _db_conflict(request: Request, exc: IntegrityError) -> JSONResponse:
    """409 on a constraint violation; the database's text (it can name values, e.g. PostgreSQL
    ``DETAIL: Key (device_id)=(...)``) is neither returned nor logged, only the error class."""
    log.warning("database conflict on %s: %s", request.url.path, exc.__class__.__name__)
    return _error(409, "conflict with existing data")


@app.exception_handler(SQLAlchemyError)
async def _db_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """503 when the database fails; only the error class is logged (no SQL parameters)."""
    log.error("database error on %s: %s", request.url.path, exc.__class__.__name__)
    return _error(503, "database unavailable")


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
    """Service status, the loaded model files and which database backend is in use."""
    b, engine = app.state.bundle, app.state.db_engine
    return HealthResponse(
        status="ok",
        models=b.files,
        sky_backend=b.sky_backend,
        cqr_q=b.cqr_q,
        db_backend=db.backend_name(engine),
        db_fallback=bool(getattr(app.state, "db_fallback", False)),
        db_ok=db.ping(engine),
    )


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
    """Sky photo -> SWIMCAT-ext sky class + confidence and red-blue cloud fraction (in memory).

    The bytes are never written to disk or a database; the result never changes the UVI.
    """
    data = await file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "image larger than 10 MB")
    # privacy check of the app's re-encoding: log only whether EXIF is present, never its values
    log.info("sky-image upload has_exif=%s", has_exif(data))
    try:
        Image.open(io.BytesIO(data)).verify()
        img = load_image(io.BytesIO(data))
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(415, "not a readable image") from exc
    res = predict_sky(img, interpreter=app.state.bundle.sky)
    return SkyImageResponse(**res, reliability=app.state.sky_reliability, stored=False)


def _session():
    """One database session per request (engine created at start-up)."""
    with db.make_session_factory(app.state.db_engine)() as s:
        yield s


def _user_response(u: db.User) -> UserResponse:
    """A stored user as the API response (never includes the device id)."""
    return UserResponse(
        id=u.id,
        skin_type=u.skin_type,
        province=u.province,
        notify_enabled=u.notify_enabled,
        alert_threshold=u.alert_threshold,
        safe_threshold=u.safe_threshold,
        alert_burn_minutes=u.alert_burn_minutes,
        updated_at=u.updated_at.isoformat(),
    )


def _owned_user(session: Session, user_id: int, device_id: str | None) -> db.User:
    """The user ``user_id`` if ``device_id`` matches it: 404 if unknown, else 403."""
    user = session.get(db.User, user_id)
    if user is None:
        raise HTTPException(404, "user not found")
    if not users.valid_device_id(device_id) or not users.device_matches(user, device_id):
        raise HTTPException(403, "X-Device-Id does not match this user")
    return user


# X-Device-Id is read as a plain string, so no validation error echoes it back, and it is never
# logged: it is the only secret that proves a request comes from the user's phone.
DeviceHeader = Header(None, alias="X-Device-Id")


@app.post("/users", response_model=UserResponse, status_code=201)
def create_user(
    body: UserCreate,
    response: Response,
    x_device_id: str | None = DeviceHeader,
    session: Session = Depends(_session),
) -> UserResponse:
    """Register this phone (anonymous) with its skin type and notification settings.

    Idempotent per device: calling again with the same ``X-Device-Id`` updates that user and
    answers 200 instead of 201.
    """
    if not users.valid_device_id(x_device_id):
        raise HTTPException(400, "X-Device-Id header missing or malformed (16-64 chars)")
    try:
        user, created = users.register(session, x_device_id, body.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if not created:
        response.status_code = 200
    log.info("user %d %s", user.id, "created" if created else "re-registered")
    return _user_response(user)


@app.put("/users/{user_id}/settings", response_model=UserResponse)
def update_user_settings(
    user_id: int,
    body: UserSettingsUpdate,
    x_device_id: str | None = DeviceHeader,
    session: Session = Depends(_session),
) -> UserResponse:
    """Change some settings; ``safe_threshold`` follows ``alert_threshold - 2``."""
    user = _owned_user(session, user_id, x_device_id)
    try:
        users.apply_settings(user, body.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    session.commit()
    return _user_response(user)


@app.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    x_device_id: str | None = DeviceHeader,
    session: Session = Depends(_session),
) -> Response:
    """Delete the user and everything linked to them (push tokens, measurements, logs)."""
    _owned_user(session, user_id, x_device_id)
    db.delete_user(session, user_id)
    log.info("user %d deleted", user_id)
    return Response(status_code=204)
