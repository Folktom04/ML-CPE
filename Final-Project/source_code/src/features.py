"""Feature engineering and CMF targets for UV Guard (day 5).

Rule (``.agents/rules/00-project-context.md``): model features come ONLY from Open-Meteo
(available as a forecast at run time) or are computed from time and location. NASA POWER
columns are never features: they are unavailable at run time and are target leakage (same
satellite product as the targets). They stay in the dataset as ``DIAGNOSTIC`` columns only.

Targets (NASA POWER / aerosol-free clear-sky model, hourly means, climatology ozone):
- ``cmf_uvi = nasa_uvi / uvi_clear``        (Madronich)
- ``cmf_a   = nasa_uva_wm2 / uva_clear``    (SPECTRL2, 315-400 nm)
- ``cmf_b   = nasa_uvb_wm2 / uvb_clear``    (SPECTRL2, 300-315 nm)
Rows with ``uvi_clear < MIN_UVI_CLEAR`` are dropped for all three targets.

Run from the project root: ``PYTHONPATH=source_code python -m src.features``.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.fetch_data import LAT, LON, ROOT, summarize
from src.physics import (
    CMF_SUBSTEPS,
    cos_zenith,
    ghi_clear_interval,
    local_month,
    ozone_climatology,
    solar_zenith,
    uva_uvb_clear_interval,
    uvi_clear_interval,
)

PROCESSED_DIR = ROOT / "dataset" / "processed"
SPEC_PATH = ROOT / "source_code" / "models" / "dataset_spec_v1.json"
MIDPOINT_OFFSET = pd.Timedelta(minutes=-30)

MIN_UVI_CLEAR = 0.5  # domain rule: skip dawn/dusk where the denominator is tiny
MIN_GHI_CLEAR_WM2 = 20.0  # below this the Open-Meteo clear-sky index is undefined
KT_MAX = 1.5

TIME_FEATURES = ["cos_sza", "hour_sin", "hour_cos", "month_sin", "month_cos"]
OPENMETEO_FEATURES = [
    "uv_index",
    "uv_index_clear_sky",
    "cloud_cover",
    "cloud_cover_low",
    "cloud_cover_mid",
    "cloud_cover_high",
    "relative_humidity_2m",
    "temperature_2m",
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "precipitation",
    "om_kt",
    "om_diffuse_fraction",
    "aerosol_optical_depth",
    "dust",
    "pm2_5",
    "ozone",
]
FEATURES = TIME_FEATURES + OPENMETEO_FEATURES
TARGETS = ["cmf_uvi", "cmf_a", "cmf_b"]
DENOMINATORS = ["uvi_clear", "uva_clear", "uvb_clear"]
DIAGNOSTIC = [
    "nasa_uvi",
    "nasa_uva_wm2",
    "nasa_uvb_wm2",
    "nasa_cloud_pct",
    "nasa_sw_all_wm2",
    "nasa_sw_clear_wm2",
    "nasa_ozone_du",
    "ozone_clim_du",
    "ghi_clear",
]
TARGET_SOURCES = {
    "cmf_uvi": ("nasa_uvi", "uvi_clear"),
    "cmf_a": ("nasa_uva_wm2", "uva_clear"),
    "cmf_b": ("nasa_uvb_wm2", "uvb_clear"),
}


def add_time_features(df: pd.DataFrame, lat: float = LAT, lon: float = LON) -> pd.DataFrame:
    """Add solar-geometry and cyclic calendar features (computed from time and location).

    ``cos_sza`` is taken at the interval midpoint; hour and month use Asia/Bangkok time.

    Args:
        df: Table with end-of-hour ``time_utc``.
        lat: Latitude in degrees.
        lon: Longitude in degrees.

    Returns:
        Copy of ``df`` with ``TIME_FEATURES`` columns.
    """
    out = df.copy()
    mid = pd.DatetimeIndex(out["time_utc"] + MIDPOINT_OFFSET)
    local = mid.tz_convert("Asia/Bangkok")
    hour = local.hour + local.minute / 60.0
    month = local_month(mid)
    out["cos_sza"] = cos_zenith(solar_zenith(mid, lat, lon))
    out["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    out["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    out["month_sin"] = np.sin(2 * np.pi * (month - 1) / 12.0)
    out["month_cos"] = np.cos(2 * np.pi * (month - 1) / 12.0)
    return out


def add_clear_sky(
    df: pd.DataFrame, lat: float = LAT, lon: float = LON, substeps: int = CMF_SUBSTEPS
) -> pd.DataFrame:
    """Add the CMF denominators (aerosol-free, climatology ozone, hourly means).

    Args:
        df: Table with end-of-hour ``time_utc``.
        lat: Latitude in degrees.
        lon: Longitude in degrees.
        substeps: Instants averaged per hour (``CMF_SUBSTEPS`` by rule).

    Returns:
        Copy of ``df`` with ``uvi_clear``, ``uva_clear``, ``uvb_clear``, ``ozone_clim_du``
        and ``ghi_clear``.
    """
    out = df.copy()
    t = out["time_utc"]
    out["ozone_clim_du"] = ozone_climatology(local_month(t + MIDPOINT_OFFSET))
    out["uvi_clear"] = uvi_clear_interval(t, lat, lon, substeps=substeps)
    uv = uva_uvb_clear_interval(t, lat, lon, substeps=substeps)
    out["uva_clear"] = uv["uva_wm2"].to_numpy()
    out["uvb_clear"] = uv["uvb_wm2"].to_numpy()
    out["ghi_clear"] = ghi_clear_interval(t, lat, lon, substeps=substeps)
    return out


def add_openmeteo_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """Add the Open-Meteo clear-sky index and diffuse fraction.

    ``om_kt = shortwave_radiation / ghi_clear`` (clipped to ``[0, KT_MAX]``) and
    ``om_diffuse_fraction = diffuse_radiation / shortwave_radiation`` (clipped to ``[0, 1]``).
    Both are NaN when ``ghi_clear < MIN_GHI_CLEAR_WM2``; the fraction is 1 when there is no
    shortwave at all.

    Args:
        df: Table with Open-Meteo radiation columns and ``ghi_clear``.

    Returns:
        Copy of ``df`` with ``om_kt`` and ``om_diffuse_fraction``.
    """
    out = df.copy()
    sun = out["ghi_clear"] >= MIN_GHI_CLEAR_WM2
    kt = out["shortwave_radiation"] / out["ghi_clear"].where(sun)
    out["om_kt"] = kt.clip(0.0, KT_MAX)
    sw = out["shortwave_radiation"]
    frac = (out["diffuse_radiation"] / sw.where(sw > 0)).fillna(1.0).clip(0.0, 1.0)
    out["om_diffuse_fraction"] = frac.where(sun)
    return out


def add_targets(df: pd.DataFrame, min_uvi_clear: float = MIN_UVI_CLEAR) -> pd.DataFrame:
    """Add ``cmf_uvi``, ``cmf_a`` and ``cmf_b`` and drop rows with a tiny denominator.

    The same row mask (``uvi_clear >= min_uvi_clear``) is used for all three targets so the
    rows line up for multi-output models. CMF values are not clipped.

    Args:
        df: Table with the NASA POWER columns and the denominators.
        min_uvi_clear: Minimum clear-sky UVI kept.

    Returns:
        Filtered copy with the target columns.
    """
    out = df.loc[df["uvi_clear"] >= min_uvi_clear].copy()
    for target, (num, den) in TARGET_SOURCES.items():
        out[target] = out[num] / out[den]
    return out.reset_index(drop=True)


def target_stats(df: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Summarise each target: quantiles and the share of values above 1 and below 0.05.

    Args:
        df: Table with ``TARGETS``.

    Returns:
        ``{target: {"p01", "p50", "p99", "mean", "share_gt_1", "share_lt_0.05"}}``.
    """
    stats = {}
    for t in TARGETS:
        s = df[t]
        stats[t] = {
            "p01": round(float(s.quantile(0.01)), 4),
            "p50": round(float(s.median()), 4),
            "p99": round(float(s.quantile(0.99)), 4),
            "mean": round(float(s.mean()), 4),
            "share_gt_1": round(float((s > 1).mean()), 4),
            "share_lt_0.05": round(float((s < 0.05).mean()), 4),
        }
    return stats


def build_dataset(merged: pd.DataFrame, substeps: int = CMF_SUBSTEPS) -> pd.DataFrame:
    """Build the training table from ``train_merged.parquet`` content.

    Args:
        merged: Output of ``src.preprocess`` (daytime, cleaned, end-of-hour ``time_utc``).
        substeps: Instants averaged per hour for the denominators.

    Returns:
        Table with ``time_utc``, ``FEATURES``, ``TARGETS``, ``DENOMINATORS`` and ``DIAGNOSTIC``,
        with no NaN in features or targets.
    """
    df = add_time_features(merged)
    df = add_clear_sky(df, substeps=substeps)
    df = add_openmeteo_ratios(df)
    df = add_targets(df)
    cols = ["time_utc", *FEATURES, *TARGETS, *DENOMINATORS, *DIAGNOSTIC]
    df = df[cols].dropna(subset=FEATURES + TARGETS)
    return df.sort_values("time_utc").reset_index(drop=True)


def write_spec(df: pd.DataFrame, path: Path = SPEC_PATH, n_input: int | None = None) -> Path:
    """Write the dataset spec JSON (feature/target lists, formulas, row counts, target stats).

    Args:
        df: Output of ``build_dataset``.
        path: Output file.
        n_input: Rows before target masking / NaN removal (for the record).

    Returns:
        The written path.
    """
    spec: dict[str, Any] = {
        "version": 1,
        "created": date.today().isoformat(),
        "features": FEATURES,
        "targets": TARGETS,
        "denominators": DENOMINATORS,
        "diagnostic_not_features": DIAGNOSTIC,
        "target_formulas": {t: f"{n} / {d}" for t, (n, d) in TARGET_SOURCES.items()},
        "row_mask": f"uvi_clear >= {MIN_UVI_CLEAR}",
        "clear_sky": {
            "substeps": CMF_SUBSTEPS,
            "ozone": "monthly climatology (models/ozone_climatology_v1.json)",
            "aod500": 0.0,
        },
        "feature_rule": "Open-Meteo or time/location only; no NASA POWER columns",
        "n_rows": int(len(df)),
        "n_input_rows": n_input,
        "time_range_utc": [str(df["time_utc"].min()), str(df["time_utc"].max())],
        "target_stats": target_stats(df),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> None:
    """Build ``dataset/processed/train.parquet`` and ``models/dataset_spec_v1.json``.

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).
    """
    parser = argparse.ArgumentParser(description="Build features and CMF targets")
    parser.parse_args(argv)

    merged = pd.read_parquet(PROCESSED_DIR / "train_merged.parquet")
    df = build_dataset(merged)
    out = PROCESSED_DIR / "train.parquet"
    df.to_parquet(out, index=False)
    write_spec(df, n_input=len(merged))

    print(summarize("train", df[["time_utc", *FEATURES, *TARGETS]]))
    print(json.dumps(target_stats(df), indent=2))
    print(f"-> {out}\n-> {SPEC_PATH}")


if __name__ == "__main__":
    main()
