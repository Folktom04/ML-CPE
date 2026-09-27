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
  Alerts, burn time and advice always use q90 after CQR (``alert_uvi``).
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
from src.fetch_data import AIR_VARS, OPENMETEO_AIR_URL, WEATHER_VARS, make_session, parse_openmeteo
from src.metrics import who_level
from src.preprocess import clean
from src.quantile import QCOLS, apply_cqr, predict_quantiles
from src.sky_infer import TFLITE_PATH, make_interpreter
from src.train_multi import predict_multi

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
PAST_DAYS = 1
FORECAST_DAYS = 2
CACHE_TTL_S = 600
LOCAL_TZ = "Asia/Bangkok"
SAFE_LEVEL = 0  # WHO level index "ต่ำ" (UVI < 2.5 after rounding)
THAILAND_BBOX = (5.5, 20.5, 97.3, 105.7)  # lat_min, lat_max, lon_min, lon_max
NIGHT_ZERO = ["om_kt", "om_diffuse_fraction"]

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
        session: HTTP session (retries/backoff from ``fetch_data.make_session`` by default).
        now: Clock value for the cache (tests).

    Returns:
        Inner join of weather and air quality on ``time_utc``.
    """
    key = (round(lat, 2), round(lon, 2))
    now = time.time() if now is None else now
    with _cache_lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < CACHE_TTL_S:
            return hit[1].copy()
    s = session or make_session()
    w = s.get(FORECAST_URL, params=request_params(lat, lon, WEATHER_VARS), timeout=30)
    w.raise_for_status()
    a = s.get(OPENMETEO_AIR_URL, params=request_params(lat, lon, AIR_VARS), timeout=30)
    a.raise_for_status()
    df = parse_openmeteo(w.json()).merge(parse_openmeteo(a.json()), on="time_utc", how="inner")
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
        Rows with ``time_utc``, ``FEATURES``, ``uvi_clear``, ``uva_clear``, ``uvb_clear`` and
        ``is_day`` (``uvi_clear >= MIN_UVI_CLEAR``).
    """
    df, _ = clean(raw)
    df = add_openmeteo_ratios(add_clear_sky(add_time_features(df, lat, lon), lat, lon))
    night = df["ghi_clear"] < MIN_GHI_CLEAR_WM2
    df.loc[night, NIGHT_ZERO] = 0.0
    df["is_day"] = df["uvi_clear"] >= MIN_UVI_CLEAR
    return df[["time_utc", *FEATURES, "uvi_clear", "uva_clear", "uvb_clear", "is_day"]]


@dataclass
class ModelBundle:
    """Models loaded once at API start-up."""

    multi: Any
    quant: Any
    cqr_q: float
    sky: Any = None
    sky_backend: str = "none"
    files: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(
        cls,
        multi_path: Path = MULTI_PATH,
        quant_path: Path = QUANT_PATH,
        cqr_path: Path = CQR_Q_PATH,
        tflite_path: Path = TFLITE_PATH,
    ) -> ModelBundle:
        """Load the day-10 final models, the frozen CQR correction and the sky TFLite model.

        Args:
            multi_path: Multi-output XGBoost (joblib).
            quant_path: Quantile XGBoost (``.ubj.gz``).
            cqr_path: JSON with the frozen CQR ``q``.
            tflite_path: Sky-CNN TFLite model.

        Returns:
            Loaded bundle.
        """
        sky, backend = make_interpreter(tflite_path)
        return cls(
            multi=joblib.load(multi_path),
            quant=load_xgb_gz(quant_path),
            cqr_q=float(json.loads(Path(cqr_path).read_text(encoding="utf-8"))["q"]),
            sky=sky,
            sky_backend=backend,
            files={p.stem: p.name for p in (multi_path, quant_path, cqr_path, tflite_path)},
        )


def predict_hours(feat: pd.DataFrame, bundle: ModelBundle) -> pd.DataFrame:
    """Point and interval predictions for every hour (zeros at night).

    Args:
        feat: Output of ``build_features``.
        bundle: Loaded models.

    Returns:
        ``time_utc``, ``is_day``, ``uvi``, ``uva_wm2``, ``uvb_wm2``, ``cmf``, ``q10``, ``q50``,
        ``q90`` (UVI after CQR), ``uvi_lo`` / ``uvi_hi`` (range shown, widened to include the
        point) and ``interval_adjusted``.
    """
    out = feat[["time_utc", "is_day"]].copy()
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
    n_adj = int(out["interval_adjusted"].sum())
    if n_adj:
        log.info("point UVI outside [q10, q90] in %d hour(s); displayed range widened", n_adj)
    return out.reset_index(drop=True)


def current_index(pred: pd.DataFrame, now: datetime) -> int:
    """Row of the hour that contains ``now`` (labels are hour ends: 10:20 -> 11:00 row).

    Args:
        pred: Output of ``predict_hours``.
        now: Aware datetime.

    Returns:
        Positional index (last row if ``now`` is after the data).
    """
    later = np.nonzero((pred["time_utc"] > pd.Timestamp(now)).to_numpy())[0]
    return int(later[0]) if len(later) else len(pred) - 1


def hour_start_local(t: pd.Timestamp) -> str:
    """ISO start of the hourly interval that ends at ``t``, in Asia/Bangkok.

    Args:
        t: End-of-hour UTC label.

    Returns:
        e.g. ``"2026-09-27T13:00:00+07:00"`` for the 13:00-14:00 local hour.
    """
    return (t - pd.Timedelta(hours=1)).tz_convert(LOCAL_TZ).isoformat()


def next_safe_time(pred: pd.DataFrame, now: datetime) -> str | None:
    """First hour from now whose alert UVI (q90 after CQR) is at WHO level "ต่ำ".

    Args:
        pred: Output of ``predict_hours``.
        now: Aware datetime.

    Returns:
        ``now`` (local ISO) if the current hour is already low, else the local start of the
        first low hour, or None if none within the forecast.
    """
    i = current_index(pred, now)
    low = who_level(pred["q90"].to_numpy()) <= SAFE_LEVEL
    if low[i]:
        return pd.Timestamp(now).tz_convert(LOCAL_TZ).isoformat()
    later = np.nonzero(low[i + 1 :])[0]
    return hour_start_local(pred["time_utc"].iloc[i + 1 + later[0]]) if len(later) else None


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
