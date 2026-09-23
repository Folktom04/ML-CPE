"""Download independent UV validation data (TEMIS, NASA OMI OMUVBd) for UV Guard.

**TEST DATA ONLY. Never use these files for training, feature selection or tuning.**
**2023 ("select" split) may only be used in notebooks/02_source_selection.ipynb to choose the**
**target source. 2025 ("test" split) is held out until day 10: do not inspect it; printing a**
**row count is the only allowed output. 2024 is never written or used (it overlaps the model**
**dev year, see src/splits.py).** Always read these files via ``load_validation()``.

- TEMIS v2.0 overpass file for Bangkok (13.667N, 100.612E): daily clear-sky noon UVI + ozone.
  Cloud-modified columns are -1 outside the MSG area, so TEMIS gives clear-sky values only.
- OMI OMUVBd v003: daily 1 x 1 degree L3 grid at local solar noon (UVindex, CSUVindex,
  irradiance at 305/310/324/380 nm). Needs EARTHDATA_USERNAME / EARTHDATA_PASSWORD in ``.env``.

Run from the project root: ``PYTHONPATH=source_code python -m src.fetch_validation``.
"""

from __future__ import annotations

import argparse
import io
import logging
import math
import os
import re
import shutil
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import pandas as pd

from src.fetch_data import LAT, LON, ROOT, make_session, summarize

VAL_DIR = ROOT / "dataset" / "validation"
VAL_RAW_DIR = VAL_DIR / "raw"

TEMIS_URL = (
    "https://d1qb6yzwaaq4he.cloudfront.net/uvradiation/v2.0/overpass/uv_Bangkok_Thailand.dat"
)
TEMIS_COLUMNS = [
    "date",
    "uvi_clear",
    "uvi_clear_err",
    "uvd_ery_clear",
    "uvd_ery_clear_err",
    "uvd_ery_cloudy",
    "uvd_ery_cloudy_err",
    "uvd_vitd_clear",
    "uvd_vitd_clear_err",
    "uvd_vitd_cloudy",
    "uvd_vitd_cloudy_err",
    "uvd_dna_clear",
    "uvd_dna_clear_err",
    "uvd_dna_cloudy",
    "uvd_dna_cloudy_err",
    "cmf",
    "ozone_du",
]
TEMIS_KEEP = ["date", "uvi_clear", "uvi_clear_err", "ozone_du"]
TEMIS_NODATA = -1.0

OMI_SHORT_NAME = "OMUVBd"
OMI_VERSION = "003"
OMI_FIELDS = [
    "UVindex",
    "CSUVindex",
    "Irradiance305",
    "Irradiance310",
    "Irradiance324",
    "Irradiance380",
    "CloudOpticalThickness",
]
OMI_FILE_DATE = re.compile(r"OMUVBd_(\d{4})m(\d{2})(\d{2})")

# 2024 is deliberately absent: it overlaps the model dev year (src/splits.py), so TEMIS/OMI 2024
# is never written or used.
SPLIT_YEARS = {"select": (2023, 2023), "test": (2025, 2025)}
SPLIT_FILES = {
    ("temis", "select"): "temis_select_2023.csv",
    ("temis", "test"): "temis_holdout_2025.csv",
    ("omi", "select"): "omi_select_2023.csv",
    ("omi", "test"): "omi_holdout_2025.csv",
}

log = logging.getLogger(__name__)


def split_range(split: str) -> tuple[date, date]:
    """Return the inclusive date range of a validation split.

    Args:
        split: ``"select"`` (2023) or ``"test"`` (2025).

    Returns:
        ``(first_day, last_day)``.
    """
    if split not in SPLIT_YEARS:
        raise ValueError(f"unknown split {split!r}; use 'select' or 'test'")
    y0, y1 = SPLIT_YEARS[split]
    return date(y0, 1, 1), date(y1, 12, 31)


def filter_split(df: pd.DataFrame, split: str) -> pd.DataFrame:
    """Keep only the rows of ``df`` (with a ``date`` column) that fall in ``split``.

    Args:
        df: DataFrame with a datetime ``date`` column.
        split: ``"select"`` or ``"test"``.

    Returns:
        Filtered copy, index reset.
    """
    start, end = split_range(split)
    mask = (df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))
    return df.loc[mask].reset_index(drop=True)


def write_split(df: pd.DataFrame, source: str, split: str, out_dir: Path = VAL_DIR) -> Path:
    """Write one split to its CSV file and log a summary.

    Only the row count is reported for the held-out ``test`` split.

    Args:
        df: Rows already restricted to ``split``.
        source: ``"temis"`` or ``"omi"``.
        split: ``"select"`` or ``"test"``.
        out_dir: Output directory.

    Returns:
        Path of the written file.
    """
    path = out_dir / SPLIT_FILES[(source, split)]
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    if split == "test":
        print(f"{source} holdout: {len(df)} rows -> {path.name} (not inspected)")
    else:
        print(summarize(f"{source} {split}", df.rename(columns={"date": "time_utc"})))
    return path


def load_validation(source: str, split: str = "select", val_dir: Path = VAL_DIR) -> pd.DataFrame:
    """Load a validation split. The default is the 2023 ``select`` split.

    The held-out 2025 data is returned only when ``split="test"`` is passed explicitly,
    which is reserved for the day-10 final evaluation.

    Args:
        source: ``"temis"`` or ``"omi"``.
        split: ``"select"`` (default) or ``"test"``.
        val_dir: Directory holding the split files.

    Returns:
        DataFrame with a datetime ``date`` column.
    """
    if (source, split) not in SPLIT_FILES:
        raise ValueError(f"unknown source/split {source!r}/{split!r}")
    df = pd.read_csv(val_dir / SPLIT_FILES[(source, split)], parse_dates=["date"])
    y0, y1 = SPLIT_YEARS[split]
    years = df["date"].dt.year
    if not years.between(y0, y1).all():
        raise ValueError(f"{source}/{split} contains rows outside {y0}-{y1}")
    return df


def parse_temis(text: str) -> pd.DataFrame:
    """Parse a TEMIS v2.0 overpass ``.dat`` file.

    Args:
        text: File contents (``#`` comment header followed by 17 whitespace-separated columns).

    Returns:
        DataFrame with ``date``, ``uvi_clear``, ``uvi_clear_err`` and ``ozone_du``;
        the no-data value -1 becomes NaN.
    """
    df = pd.read_csv(
        io.StringIO(text),
        comment="#",
        sep=r"\s+",
        header=None,
        names=TEMIS_COLUMNS,
        dtype={"date": str},
    )
    df = df[TEMIS_KEEP].copy()
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    num = df.columns.drop("date")
    df[num] = df[num].mask(np.isclose(df[num], TEMIS_NODATA))
    return df


def fetch_temis(raw_path: Path | None = None) -> pd.DataFrame:
    """Download (once) and parse the TEMIS Bangkok overpass file.

    Args:
        raw_path: Where to cache the raw ``.dat`` file.

    Returns:
        Full parsed TEMIS record (all years). Callers must split it before looking at it.
    """
    raw_path = raw_path or VAL_RAW_DIR / "uv_Bangkok_Thailand.dat"
    if not raw_path.exists():
        log.info("GET %s", TEMIS_URL)
        resp = make_session().get(TEMIS_URL, timeout=120)
        resp.raise_for_status()
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(resp.content)
    else:
        log.info("cache hit %s", raw_path.name)
    return parse_temis(raw_path.read_text(encoding="utf-8", errors="replace"))


def omi_grid_index(lat: float, lon: float) -> tuple[int, int]:
    """Return ``(row, col)`` of the OMUVBd 1-degree cell containing ``(lat, lon)``.

    OMUVBd arrays are 180 x 360 with row 0 centred at -89.5 (south) and column 0 at -179.5.

    Args:
        lat: Latitude in degrees (-90..90).
        lon: Longitude in degrees (-180..180).

    Returns:
        Row and column indices.
    """
    row = min(int(math.floor(lat + 90.0)), 179)
    col = min(int(math.floor(lon + 180.0)), 359)
    return row, col


def omi_file_date(name: str) -> date:
    """Parse the observation date from an OMUVBd file name (``..._OMUVBd_2023m0101_...``).

    Args:
        name: File name or URL.

    Returns:
        Observation date.
    """
    m = OMI_FILE_DATE.search(name)
    if not m:
        raise ValueError(f"no OMUVBd date in {name!r}")
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def extract_omuvbd_pixel(h5_path: Path, lat: float = LAT, lon: float = LON) -> dict[str, Any]:
    """Read the ``OMI_FIELDS`` values of one grid cell from an OMUVBd ``.he5`` file.

    Datasets are found by name anywhere in the file, so the internal group path does not
    matter. Values equal to the ``MissingValue`` / ``_FillValue`` attribute become NaN.

    Args:
        h5_path: Path to the HDF-EOS5 file.
        lat: Latitude in degrees.
        lon: Longitude in degrees.

    Returns:
        Dict with ``date`` plus one float per field (NaN if missing or absent).
    """
    row, col = omi_grid_index(lat, lon)
    found: dict[str, h5py.Dataset] = {}

    def visit(name: str, obj: Any) -> None:
        leaf = name.rsplit("/", 1)[-1]
        if isinstance(obj, h5py.Dataset) and leaf in OMI_FIELDS and leaf not in found:
            found[leaf] = obj

    out: dict[str, Any] = {"date": pd.Timestamp(omi_file_date(h5_path.name))}
    with h5py.File(h5_path, "r") as f:
        f.visititems(visit)
        for field in OMI_FIELDS:
            ds = found.get(field)
            if ds is None:
                out[field] = np.nan
                continue
            value = float(ds[row, col])
            for attr in ("MissingValue", "_FillValue"):
                if attr in ds.attrs and np.isclose(value, np.ravel(ds.attrs[attr])[0]):
                    value = np.nan
            out[field] = value
    return out


def fetch_omi(
    split: str = "select",
    lat: float = LAT,
    lon: float = LON,
    keep_he5: bool = False,
    batch_size: int = 30,
) -> pd.DataFrame:
    """Download OMUVBd files for one split and extract the pixel over ``(lat, lon)``.

    Extracted rows are appended to ``dataset/validation/omi_pixel_cache_<split>.csv`` after
    every batch, and days already in the cache are skipped, so the run can be resumed.
    The ``.he5`` files are deleted after extraction unless ``keep_he5`` is True.

    Args:
        split: ``"select"`` (2023, day 2) or ``"test"`` (2025, day 10 only).
        lat: Latitude in degrees.
        lon: Longitude in degrees.
        keep_he5: Keep the downloaded files in ``dataset/validation/raw/omi/``.
        batch_size: Files downloaded per batch.

    Returns:
        One row per day with ``date`` and ``OMI_FIELDS`` columns.
    """
    import earthaccess
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    if not (os.getenv("EARTHDATA_USERNAME") and os.getenv("EARTHDATA_PASSWORD")):
        raise RuntimeError("EARTHDATA_USERNAME / EARTHDATA_PASSWORD are not set in .env")
    earthaccess.login(strategy="environment")

    start, end = split_range(split)
    cache = VAL_DIR / f"omi_pixel_cache_{split}.csv"
    done = (
        set(pd.read_csv(cache, parse_dates=["date"])["date"].dt.date) if cache.exists() else set()
    )

    granules = earthaccess.search_data(
        short_name=OMI_SHORT_NAME,
        version=OMI_VERSION,
        temporal=(start.isoformat(), end.isoformat()),
        bounding_box=(lon - 0.5, lat - 0.5, lon + 0.5, lat + 0.5),
    )
    todo = [g for g in granules if omi_file_date(g.data_links()[0]) not in done]
    log.info("OMI %s: %d granules, %d to download", split, len(granules), len(todo))

    keep_dir = VAL_RAW_DIR / "omi"
    for i in range(0, len(todo), batch_size):
        batch = todo[i : i + batch_size]
        tmp = Path(tempfile.mkdtemp(prefix="omuvbd_"))
        try:
            paths = earthaccess.download(batch, local_path=str(tmp))
            rows = [extract_omuvbd_pixel(Path(p), lat, lon) for p in paths]
            pd.DataFrame(rows).to_csv(cache, mode="a", header=not cache.exists(), index=False)
            if keep_he5:
                keep_dir.mkdir(parents=True, exist_ok=True)
                for p in paths:
                    shutil.move(str(p), keep_dir / Path(p).name)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        log.info("OMI %s: %d/%d done", split, min(i + batch_size, len(todo)), len(todo))

    if not cache.exists():
        return pd.DataFrame(columns=["date", *OMI_FIELDS])
    df = pd.read_csv(cache, parse_dates=["date"]).drop_duplicates("date").sort_values("date")
    return filter_split(df, split)


def main(argv: list[str] | None = None) -> None:
    """Fetch TEMIS (both splits written, test split only counted) and OMI for one split.

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).
    """
    parser = argparse.ArgumentParser(description="Fetch TEMIS / OMI validation data")
    parser.add_argument(
        "--split",
        choices=sorted(SPLIT_YEARS),
        default="select",
        help="OMI split to download: select=2023 (day 2), test=2025 (day 10 only)",
    )
    parser.add_argument("--keep-he5", action="store_true", help="keep downloaded OMI files")
    parser.add_argument("--skip-omi", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    temis = fetch_temis()
    for split in ("select", "test"):
        write_split(filter_split(temis, split), "temis", split)

    if args.skip_omi:
        return
    try:
        omi = fetch_omi(args.split, keep_he5=args.keep_he5)
    except RuntimeError as exc:
        print(f"OMI skipped: {exc}")
        return
    write_split(omi, "omi", args.split)


if __name__ == "__main__":
    main()
