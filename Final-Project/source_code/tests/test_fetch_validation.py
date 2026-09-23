"""Tests for src.fetch_validation (no real network access)."""

import sys
import types
from datetime import date
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import pytest

from src import fetch_validation as fv

TEMIS_SAMPLE = """# TEMIS v2.0 UV index and UV dose overpass file
# No-data entry = -1.000
  20221231   10.000   0.500   5.0   0.3  -1.000  -1.000   9.0   0.8  -1.000  -1.000   3.0   0.2  -1.000  -1.000  -1.000  250.0
  20230101   11.000   0.500   5.0   0.3  -1.000  -1.000   9.0   0.8  -1.000  -1.000   3.0   0.2  -1.000  -1.000  -1.000  -1.000
  20240101   12.000   0.500   5.0   0.3  -1.000  -1.000   9.0   0.8  -1.000  -1.000   3.0   0.2  -1.000  -1.000  -1.000  260.0
  20250101   13.000   0.500   5.0   0.3  -1.000  -1.000   9.0   0.8  -1.000  -1.000   3.0   0.2  -1.000  -1.000  -1.000  270.0
"""


def make_omuvbd(path: Path, uvi: float, fill: float = -1.0e30) -> Path:
    """Write a tiny OMUVBd-like HDF5 file with a 180x360 grid."""
    row, col = fv.omi_grid_index(fv.LAT, fv.LON)
    with h5py.File(path, "w") as f:
        grp = f.create_group("HDFEOS/GRIDS/OMI UVB Product/Data Fields")
        for field in fv.OMI_FIELDS:
            arr = np.zeros((180, 360), dtype="f4")
            arr[row, col] = uvi if field == "UVindex" else fill
            ds = grp.create_dataset(field, data=arr)
            ds.attrs["MissingValue"] = np.array([fill], dtype="f4")
    return path


def test_parse_temis_keeps_columns_and_masks_nodata():
    df = fv.parse_temis(TEMIS_SAMPLE)
    assert list(df.columns) == fv.TEMIS_KEEP
    assert df["date"].tolist()[1] == pd.Timestamp("2023-01-01")
    assert df["uvi_clear"].tolist() == [10.0, 11.0, 12.0, 13.0]
    assert pd.isna(df.loc[1, "ozone_du"])


def test_split_range_and_unknown_split():
    assert fv.split_range("select") == (date(2023, 1, 1), date(2023, 12, 31))
    assert fv.split_range("test") == (date(2025, 1, 1), date(2025, 12, 31))
    with pytest.raises(ValueError):
        fv.split_range("train")


def test_filter_split_separates_years_and_never_returns_2024():
    df = fv.parse_temis(TEMIS_SAMPLE)
    assert fv.filter_split(df, "select")["date"].dt.year.tolist() == [2023]
    assert fv.filter_split(df, "test")["date"].dt.year.tolist() == [2025]
    assert 2024 not in set(fv.SPLIT_YEARS["select"]) | set(fv.SPLIT_YEARS["test"])


def test_write_split_holdout_prints_only_row_count(tmp_path, capsys):
    df = fv.filter_split(fv.parse_temis(TEMIS_SAMPLE), "test")
    path = fv.write_split(df, "temis", "test", out_dir=tmp_path)
    out = capsys.readouterr().out
    assert path.name == "temis_holdout_2025.csv"
    assert "1 rows" in out
    assert "13.0" not in out and "missing" not in out


def test_load_validation_test_split_is_2025_only(tmp_path):
    df = fv.parse_temis(TEMIS_SAMPLE)
    fv.write_split(fv.filter_split(df, "test"), "temis", "test", out_dir=tmp_path)
    loaded = fv.load_validation("temis", split="test", val_dir=tmp_path)
    assert loaded["date"].dt.year.unique().tolist() == [2025]
    df.to_csv(tmp_path / fv.SPLIT_FILES[("temis", "test")], index=False)  # 2024 leaked in
    with pytest.raises(ValueError):
        fv.load_validation("temis", split="test", val_dir=tmp_path)


def test_load_validation_defaults_to_select_and_rejects_other_years(tmp_path):
    df = fv.parse_temis(TEMIS_SAMPLE)
    fv.write_split(fv.filter_split(df, "select"), "temis", "select", out_dir=tmp_path)
    loaded = fv.load_validation("temis", val_dir=tmp_path)
    assert loaded["date"].dt.year.unique().tolist() == [2023]

    df.to_csv(tmp_path / fv.SPLIT_FILES[("temis", "select")], index=False)  # leaked years
    with pytest.raises(ValueError):
        fv.load_validation("temis", val_dir=tmp_path)
    with pytest.raises(ValueError):
        fv.load_validation("temis", split="train", val_dir=tmp_path)


def test_omi_grid_index_matches_south_up_layout():
    assert fv.omi_grid_index(14.02, 100.52) == (104, 280)
    assert fv.omi_grid_index(-90.0, -180.0) == (0, 0)
    assert fv.omi_grid_index(90.0, 180.0) == (179, 359)


def test_omi_file_date():
    name = "OMI-Aura_L3-OMUVBd_2023m0315_v003-2023m0321t084413.he5"
    assert fv.omi_file_date(name) == date(2023, 3, 15)
    with pytest.raises(ValueError):
        fv.omi_file_date("other.he5")


def test_extract_omuvbd_pixel_reads_cell_and_masks_fill(tmp_path):
    path = make_omuvbd(tmp_path / "OMI-Aura_L3-OMUVBd_2023m0101_v003-x.he5", uvi=9.5)
    row = fv.extract_omuvbd_pixel(path)
    assert row["date"] == pd.Timestamp("2023-01-01")
    assert row["UVindex"] == pytest.approx(9.5)
    assert np.isnan(row["CSUVindex"])


def test_fetch_omi_skips_days_already_cached(tmp_path, monkeypatch):
    monkeypatch.setattr(fv, "VAL_DIR", tmp_path)
    monkeypatch.setenv("EARTHDATA_USERNAME", "u")
    monkeypatch.setenv("EARTHDATA_PASSWORD", "p")
    pd.DataFrame([{"date": "2023-01-01", **{k: 1.0 for k in fv.OMI_FIELDS}}]).to_csv(
        tmp_path / "omi_pixel_cache_select.csv", index=False
    )

    class Granule:
        def __init__(self, name):
            self.name = name

        def data_links(self):
            return [f"https://x/{self.name}"]

    names = [f"OMI-Aura_L3-OMUVBd_2023m010{d}_v003-x.he5" for d in (1, 2)]
    downloaded = []

    def download(batch, local_path):
        downloaded.extend(g.name for g in batch)
        return [make_omuvbd(Path(local_path) / g.name, uvi=7.0) for g in batch]

    fake = types.SimpleNamespace(
        login=lambda strategy: None,
        search_data=lambda **kw: [Granule(n) for n in names],
        download=download,
    )
    monkeypatch.setitem(sys.modules, "earthaccess", fake)

    df = fv.fetch_omi("select")
    assert downloaded == [names[1]]
    assert df["date"].tolist() == [pd.Timestamp("2023-01-01"), pd.Timestamp("2023-01-02")]
    assert df["UVindex"].tolist() == [1.0, 7.0]


def test_fetch_omi_requires_credentials(monkeypatch):
    monkeypatch.setattr(fv, "ROOT", Path("does-not-exist"))
    monkeypatch.delenv("EARTHDATA_USERNAME", raising=False)
    monkeypatch.delenv("EARTHDATA_PASSWORD", raising=False)
    with pytest.raises(RuntimeError):
        fv.fetch_omi("select")
