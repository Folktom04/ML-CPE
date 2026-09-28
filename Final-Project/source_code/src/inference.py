"""Day 16: run-time inference for the API (Open-Meteo in, UVI/UVA/UVB + range + risk out).

* Inputs come only from Open-Meteo (Forecast API + Air Quality API) and time/location. The
  same 12 weather and 4 air-quality variables as training are requested, with no ``models=`` /
  ``domains=`` parameter, as in ``src.fetch_data`` (day 16: the Historical Forecast API used
  for training and the Forecast API used here returned identical values for all 16 variables
  over 72 h). NASA POWER is never called here.
* Features are built with the training functions (``preprocess.clean`` +
  ``features.add_*``), so train and serve share one code path.
* Point UVI/UVA/UVB: multi-output XGBoost (day 10 final). Range: quantile XGBoost q10/q90 with
  the CQR correction frozen on day 10. The point value is never clipped: if it falls outside
  [q10, q90] the displayed range is widened to include it and ``interval_adjusted`` is set.
  Alerts, burn time and advice use ``alert_uvi = max(q90 after CQR, point UVI)``, so a
  warning is never lower than the value shown.
* Missing live data: missing hours are re-inserted as NaN, implausible values masked, gaps of
  up to ``INTERP_LIMIT_HOURS`` interpolated (as in training) and edge gaps of up to
  ``EDGE_FILL_HOURS`` filled from the nearest hour. Such hours carry ``data_imputed``; hours
  that are still incomplete are dropped and logged, and if the current hour is one of them
  the API answers 503 instead of silently using another hour.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import requests
from src.evaluate_test import CQR_Q_PATH, MULTI_PATH, QUANT_PATH, load_xgb_gz
from src.features import (
    FEATURES,
    MIN_GHI_CLEAR_WM2,
    MIN_UVI_CLEAR,
    add_clear_sky,
    add_openmeteo_ratios,
    add_time_features,
)
from src.fetch_data import AIR_VARS, OPENMETEO_AIR_URL, WEATHER_VARS, parse_openmeteo
from src.metrics import who_level
from src.preprocess import INTERP_LIMIT_HOURS, clean, mask_implausible
from src.quantile import QCOLS, apply_cqr, predict_quantiles
from src.sky_infer import CLOUD_TFLITE_PATH, TFLITE_PATH, cloud_head_result, make_interpreter
from src.train_multi import predict_multi

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
PAST_DAYS = 1
FORECAST_DAYS = 2
CACHE_TTL_S = 600
# Live fetch budget (day 19): answer (or fail with 502) before the app's 20 s timeout. The
# training downloads in ``src.fetch_data`` keep their long retries (5 x backoff 2 s, 30 s).
LIVE_RETRIES = 2
LIVE_TIMEOUT_S = 5.0
LIVE_BUDGET_S = 15.0
LIVE_BACKOFF_S = 0.5
RETRY_STATUS = (429, 500, 502, 503, 504)
_monotonic = time.monotonic  # replaced in tests
_sleep = time.sleep
LOCAL_TZ = "Asia/Bangkok"
SAFE_LEVEL = 0  # WHO level index "ต่ำ" (UVI < 2.5 after rounding)
THAILAND_BBOX = (5.5, 20.5, 97.3, 105.7)  # lat_min, lat_max, lon_min, lon_max
TRAINING_SITE = (14.02, 100.52)  # Pathum Thani: the only place trained and tested
TRAINING_RADIUS_KM = 50.0
OUTSIDE_TRAINING_NOTE = "ความแม่นยำนอกพื้นที่ปทุมธานียังไม่ได้ประเมิน"
NIGHT_ZERO = ["om_kt", "om_diffuse_fraction"]
EDGE_FILL_HOURS = INTERP_LIMIT_HOURS
INPUT_VARS = [*WEATHER_VARS, *AIR_VARS]

log = logging.getLogger(__name__)
_cache: dict[tuple[float, float], tuple[float, pd.DataFrame]] = {}
_cache_lock = threading.Lock()


def request_params(lat: float, lon: float, variables: list[str]) -> dict[str, Any]:
    """Open-Meteo query for live data: the training variables, GMT, past + forecast days.

    Args:
        lat: Latitude.
        lon: Longitude.
        variables: Hourly variable names.

    Returns:
        Query parameters (no ``models``/``domains``: Open-Meteo defaults, as in training).
    """
    return {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(variables),
        "timezone": "GMT",
        "past_days": PAST_DAYS,
        "forecast_days": FORECAST_DAYS,
    }


def get_live(
    session: requests.Session,
    url: str,
    params: dict[str, Any],
    deadline: float,
    clock: Any = None,
    sleep: Any = None,
) -> requests.Response:
    """GET with a few short retries that never run past ``deadline`` (live requests only).

    Retries ``LIVE_RETRIES`` times on connection errors, timeouts and ``RETRY_STATUS``, with
    ``LIVE_BACKOFF_S * 2**k`` pauses. Each attempt gets ``min(LIVE_TIMEOUT_S, time left)``
    (a requests timeout is per connect/read, so an attempt can overrun it only slightly).

    Args:
        session: HTTP session.
        url: Request URL.
        params: Query parameters.
        deadline: ``clock()`` value after which no new attempt is started.
        clock: Monotonic clock (default ``_monotonic``).
        sleep: Sleep function (default ``_sleep``).

    Returns:
        The successful response.

    Raises:
        requests.RequestException: The last error, or ``requests.Timeout`` when the budget
            is used up before an attempt can start.
    """
    clock, sleep = clock or _monotonic, sleep or _sleep
    last: requests.RequestException | None = None
    for attempt in range(LIVE_RETRIES + 1):
        left = deadline - clock()
        if left <= 0:
            break
        try:
            resp = session.get(url, params=params, timeout=min(LIVE_TIMEOUT_S, left))
            if resp.status_code not in RETRY_STATUS:
                resp.raise_for_status()
                return resp
            last = requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
        except (requests.ConnectionError, requests.Timeout) as exc:
            last = exc
        if attempt < LIVE_RETRIES:
            pause = LIVE_BACKOFF_S * 2**attempt
            if clock() + pause >= deadline:
                break
            sleep(pause)
    raise last or requests.Timeout(f"live fetch budget of {LIVE_BUDGET_S:.0f} s used up")


def fetch_live(
    lat: float,
    lon: float,
    session: requests.Session | None = None,
    now: float | None = None,
) -> pd.DataFrame:
    """Hourly Open-Meteo weather + air quality for one place, cached in memory for 10 min.

    Args:
        lat: Latitude.
        lon: Longitude.
        session: HTTP session without adapter retries (default: a plain ``requests.Session``).
        now: Clock value for the cache (tests).

    Both requests share one ``LIVE_BUDGET_S`` deadline (see ``get_live``), so the API answers
    or fails with 502 before the app gives up at 20 s.

    Returns:
        Weather left-joined with air quality on ``time_utc`` (missing air hours stay NaN and
        are handled in ``build_features``).
    """
    key = (round(lat, 2), round(lon, 2))
    now = time.time() if now is None else now
    with _cache_lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < CACHE_TTL_S:
            return hit[1].copy()
    s = session or requests.Session()  # no adapter retries: ``get_live`` owns the budget
    deadline = _monotonic() + LIVE_BUDGET_S
    w = get_live(s, FORECAST_URL, request_params(lat, lon, WEATHER_VARS), deadline)
    a = get_live(s, OPENMETEO_AIR_URL, request_params(lat, lon, AIR_VARS), deadline)
    df = parse_openmeteo(w.json()).merge(parse_openmeteo(a.json()), on="time_utc", how="left")
    with _cache_lock:
        _cache[key] = (now, df)
    return df.copy()


def build_features(raw: pd.DataFrame, lat: float, lon: float) -> pd.DataFrame:
    """Training feature pipeline applied to live Open-Meteo rows (all hours, day and night).

    Args:
        raw: Weather + air-quality rows with ``time_utc`` (end-of-hour labels).
        lat: Latitude.
        lon: Longitude.

    Returns:
        Rows with ``time_utc``, ``FEATURES``, ``uvi_clear``, ``uva_clear``, ``uvb_clear``,
        ``is_day`` (``uvi_clear >= MIN_UVI_CLEAR``) and ``data_imputed`` (some input of that
        hour was missing or implausible and was filled). Hours still incomplete after filling
        are dropped.
    """
    raw = raw.sort_values("time_utc").drop_duplicates("time_utc")
    full = pd.date_range(raw["time_utc"].iloc[0], raw["time_utc"].iloc[-1], freq="h")
    raw = raw.set_index("time_utc").reindex(full).rename_axis("time_utc").reset_index()
    cols = [c for c in INPUT_VARS if c in raw]
    imputed = mask_implausible(raw)[cols].isna().any(axis=1).to_numpy()
    df, _ = clean(raw, dropna=False)
    edge = {"limit": EDGE_FILL_HOURS, "limit_area": "outside"}  # interior gaps: interpolation only
    df[cols] = df[cols].ffill(**edge).bfill(**edge)
    complete = df[cols].notna().all(axis=1).to_numpy()
    if not complete.all():
        log.warning("dropped %d hour(s) with inputs still missing", int((~complete).sum()))
    df = df.loc[complete].reset_index(drop=True)
    df["data_imputed"] = imputed[complete]
    if df["data_imputed"].any():
        log.info("%d hour(s) use filled inputs", int(df["data_imputed"].sum()))
    df = add_openmeteo_ratios(add_clear_sky(add_time_features(df, lat, lon), lat, lon))
    night = df["ghi_clear"] < MIN_GHI_CLEAR_WM2
    df.loc[night, NIGHT_ZERO] = 0.0
    df["is_day"] = df["uvi_clear"] >= MIN_UVI_CLEAR
    return df[
        ["time_utc", *FEATURES, "uvi_clear", "uva_clear", "uvb_clear", "is_day", "data_imputed"]
    ]


@dataclass
class ModelBundle:
    """Models loaded once at API start-up."""

    multi: Any
    quant: Any
    cqr_q: float
    sky: Any = None
    sky_backend: str = "none"
    sky_cloud: Any = None  # SWIMSEG head; None unless it passed C1/C2 (``cloud_head_result``)
    files: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(
        cls,
        multi_path: Path = MULTI_PATH,
        quant_path: Path = QUANT_PATH,
        cqr_path: Path = CQR_Q_PATH,
        tflite_path: Path = TFLITE_PATH,
        cloud_tflite_path: Path = CLOUD_TFLITE_PATH,
        cloud_ships: bool | None = None,
    ) -> ModelBundle:
        """Load the day-10 final models, the frozen CQR correction and the sky TFLite model.

        Args:
            multi_path: Multi-output XGBoost (joblib).
            quant_path: Quantile XGBoost (``.ubj.gz``).
            cqr_path: JSON with the frozen CQR ``q``.
            tflite_path: Sky-CNN TFLite model.
            cloud_tflite_path: SWIMSEG cloud-fraction TFLite model.
            cloud_ships: Whether to load it; None = only if ``cloud_head_result()`` says it
                passed C1 and C2.

        Returns:
            Loaded bundle.
        """
        sky, backend = make_interpreter(tflite_path)
        if cloud_ships is None:
            cloud_ships = cloud_head_result() is not None
        sky_cloud = make_interpreter(cloud_tflite_path)[0] if cloud_ships else None
        paths = [multi_path, quant_path, cqr_path, tflite_path]
        paths += [cloud_tflite_path] if cloud_ships else []
        return cls(
            multi=joblib.load(multi_path),
            quant=load_xgb_gz(quant_path),
            cqr_q=float(json.loads(Path(cqr_path).read_text(encoding="utf-8"))["q"]),
            sky=sky,
            sky_backend=backend,
            sky_cloud=sky_cloud,
            files={p.stem: p.name for p in paths},
        )


def predict_hours(feat: pd.DataFrame, bundle: ModelBundle) -> pd.DataFrame:
    """Point and interval predictions for every hour (zeros at night).

    Args:
        feat: Output of ``build_features``.
        bundle: Loaded models.

    Returns:
        ``time_utc``, ``is_day``, ``uvi``, ``uva_wm2``, ``uvb_wm2``, ``cmf``, ``q10``, ``q50``,
        ``q90`` (UVI after CQR), ``uvi_lo`` / ``uvi_hi`` (range shown, widened to include the
        point), ``interval_adjusted``, ``alert_uvi`` (``max(q90, uvi)``: drives alerts, burn
        time, advice and the next safe time) and ``data_imputed``.
    """
    out = feat[["time_utc", "is_day"]].copy()
    out["data_imputed"] = feat["data_imputed"] if "data_imputed" in feat else False
    X = feat[FEATURES]
    cmf = predict_multi(bundle.multi, X)
    cmf_q = apply_cqr(predict_quantiles(bundle.quant, X), bundle.cqr_q)
    day = feat["is_day"].to_numpy()
    out["cmf"] = np.where(day, cmf["cmf_uvi"].to_numpy(), np.nan)
    out["uvi"] = np.where(day, feat["uvi_clear"].to_numpy() * cmf["cmf_uvi"].to_numpy(), 0.0)
    out["uva_wm2"] = np.where(day, feat["uva_clear"].to_numpy() * cmf["cmf_a"].to_numpy(), 0.0)
    out["uvb_wm2"] = np.where(day, feat["uvb_clear"].to_numpy() * cmf["cmf_b"].to_numpy(), 0.0)
    for c in QCOLS:
        out[c] = np.where(day, feat["uvi_clear"].to_numpy() * cmf_q[c].to_numpy(), 0.0)
    out["interval_adjusted"] = (out["uvi"] < out["q10"]) | (out["uvi"] > out["q90"])
    out["uvi_lo"] = np.minimum(out["q10"], out["uvi"])
    out["uvi_hi"] = np.maximum(out["q90"], out["uvi"])
    out["alert_uvi"] = np.maximum(out["q90"], out["uvi"])
    n_adj = int(out["interval_adjusted"].sum())
    if n_adj:
        log.info("point UVI outside [q10, q90] in %d hour(s); displayed range widened", n_adj)
    return out.reset_index(drop=True)


class NoCurrentHourError(LookupError):
    """The hour that contains ``now`` is missing from the live data."""


def current_index(pred: pd.DataFrame, now: datetime, strict: bool = True) -> int:
    """Row of the hour that contains ``now`` (labels are hour ends: 10:20 -> 11:00 row).

    Args:
        pred: Output of ``predict_hours``.
        now: Aware datetime.
        strict: Raise ``NoCurrentHourError`` if that hour is missing (dropped for missing
            data or outside the data). If False, return the first later hour instead.

    Returns:
        Positional index (last row if ``now`` is after the data and ``strict`` is False).
    """
    now = pd.Timestamp(now)
    later = np.nonzero((pred["time_utc"] > now).to_numpy())[0]
    i = int(later[0]) if len(later) else len(pred) - 1
    end = pred["time_utc"].iloc[i]
    if strict and not (end - pd.Timedelta(hours=1) <= now < end):
        raise NoCurrentHourError(f"no live data for the hour containing {now.isoformat()}")
    return i


def hour_start_local(t: pd.Timestamp) -> str:
    """ISO start of the hourly interval that ends at ``t``, in Asia/Bangkok.

    Args:
        t: End-of-hour UTC label.

    Returns:
        e.g. ``"2026-09-27T13:00:00+07:00"`` for the 13:00-14:00 local hour.
    """
    return (t - pd.Timedelta(hours=1)).tz_convert(LOCAL_TZ).isoformat()


def next_safe_time(pred: pd.DataFrame, now: datetime) -> str | None:
    """First hour from now whose alert UVI (``max(q90, uvi)``) is at WHO level "ต่ำ".

    Args:
        pred: Output of ``predict_hours``.
        now: Aware datetime.

    Returns:
        ``now`` (local ISO) if the current hour is already low, else the local start of the
        first low hour, or None if none within the forecast.
    """
    i = current_index(pred, now, strict=False)
    low = who_level(pred["alert_uvi"].to_numpy()) <= SAFE_LEVEL
    if low[i]:
        return pd.Timestamp(now).tz_convert(LOCAL_TZ).isoformat()
    later = np.nonzero(low[i + 1 :])[0]
    return hour_start_local(pred["time_utc"].iloc[i + 1 + later[0]]) if len(later) else None


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle (haversine) distance between two points.

    Args:
        lat1: Latitude of point 1 (degrees).
        lon1: Longitude of point 1.
        lat2: Latitude of point 2.
        lon2: Longitude of point 2.

    Returns:
        Distance in km (Earth radius 6371 km).
    """
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = p2 - p1, np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return float(2 * 6371.0 * np.arcsin(np.sqrt(a)))


def training_area_note(lat: float, lon: float) -> str | None:
    """Note for places farther than ``TRAINING_RADIUS_KM`` from Pathum Thani, else None.

    The model was trained and tested at one point only (NASA POWER at Pathum Thani, with that
    site's ozone climatology), so its accuracy elsewhere has not been measured (day 21).

    Args:
        lat: Latitude.
        lon: Longitude.

    Returns:
        ``OUTSIDE_TRAINING_NOTE`` or None.
    """
    far = distance_km(lat, lon, *TRAINING_SITE) > TRAINING_RADIUS_KM
    return OUTSIDE_TRAINING_NOTE if far else None


def in_thailand(lat: float, lon: float) -> bool:
    """Whether a point is inside the rough Thailand bounding box.

    Args:
        lat: Latitude.
        lon: Longitude.

    Returns:
        True inside ``THAILAND_BBOX``.
    """
    a, b, c, d = THAILAND_BBOX
    return a <= lat <= b and c <= lon <= d


def utc_now() -> datetime:
    """Current time, timezone-aware UTC (patched in tests)."""
    return datetime.now(timezone.utc)
