"""Tests for the FastAPI service (real saved models, Open-Meteo mocked)."""

import io
import logging
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from api import main
from fastapi.testclient import TestClient
from PIL import Image
from src import db
from src import inference as inf
from src.fetch_data import ROOT
from src.metrics import WHO_LEVELS, who_level
from src.risk import DISCLAIMER, burn_minutes
from src.sky_infer import SWIM_CLASS_TH, has_exif
from tests.test_inference import fake_bundle, synthetic_raw

NOW = datetime(2026, 9, 27, 5, 20, tzinfo=timezone.utc)  # 12:20 in Bangkok
RULE_KEYS = {
    "uvi",
    "uvi_range",
    "uva_wm2",
    "uvb_wm2",
    "level",
    "skin_type",
    "burn_minutes",
    "cmf",
    "advice",
    "forecast",
    "next_safe_time",
}
PAYLOAD = {"lat": 14.02, "lon": 100.52, "skin_type": "III"}


@pytest.fixture(scope="module")
def real_bundle():
    return inf.ModelBundle.load()


@pytest.fixture
def client(real_bundle, monkeypatch):
    monkeypatch.setattr(inf, "fetch_live", lambda lat, lon: synthetic_raw())
    monkeypatch.setattr(inf, "utc_now", lambda: NOW)
    main.app.state.bundle = real_bundle
    main.app.state.db_engine = db.make_engine("sqlite://")
    main.app.state.db_fallback = False
    with TestClient(main.app) as c:
        yield c


def png_bytes(color=(90, 140, 220), fmt="PNG"):
    buf = io.BytesIO()
    Image.new("RGB", (300, 200), color).save(buf, format=fmt)
    return buf.getvalue()


def test_models_loaded_once_and_health(client, real_bundle, monkeypatch):
    calls = []
    monkeypatch.setattr(inf.ModelBundle, "load", classmethod(lambda cls: calls.append(1)))
    for _ in range(3):
        client.post("/predict", json=PAYLOAD)
    assert calls == [] and main.app.state.bundle is real_bundle  # loaded at start-up only
    r = client.get("/health").json()
    assert r["status"] == "ok" and r["disclaimer"] == DISCLAIMER
    assert r["sky_backend"] in ("ai_edge_litert", "tf.lite")
    assert r["cqr_q"] == pytest.approx(0.0379, abs=1e-4)
    assert (r["db_backend"], r["db_ok"], r["db_fallback"]) == ("sqlite", True, False)


def test_health_reports_sqlite_fallback_and_unreachable_postgres(
    real_bundle, monkeypatch, caplog, tmp_path
):
    monkeypatch.setattr(inf, "fetch_live", lambda lat, lon: synthetic_raw())
    main.app.state.bundle = real_bundle
    main.app.state.db_engine = None
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    monkeypatch.setattr(db, "SQLITE_FALLBACK_PATH", tmp_path / "fallback.sqlite")
    with caplog.at_level("WARNING", logger="src.db"), TestClient(main.app) as c:
        r = c.get("/health").json()
    assert (r["db_backend"], r["db_fallback"], r["db_ok"]) == ("sqlite", True, True)
    assert any("FALLBACK" in m for m in caplog.messages)
    main.app.state.db_engine.dispose()
    main.app.state.db_engine = db.make_engine("postgresql+psycopg://u:p@127.0.0.1:1/x")
    main.app.state.db_fallback = False
    with TestClient(main.app) as c:
        r = c.get("/health")
    assert r.status_code == 200
    assert (r.json()["db_backend"], r.json()["db_ok"]) == ("postgresql", False)
    main.app.state.db_engine.dispose()
    main.app.state.db_engine = None


def test_predict_matches_rule_schema(client):
    r = client.post("/predict", json=PAYLOAD)
    assert r.status_code == 200
    body = r.json()
    assert RULE_KEYS <= set(body)
    assert body["disclaimer"] == DISCLAIMER and body["skin_type"] == "III"
    lo, hi = body["uvi_range"]
    assert lo <= body["uvi"] <= hi and body["is_daylight"]
    assert body["level"] == WHO_LEVELS[int(who_level(body["uvi"]))]
    assert body["forecast"] and {"time", "uvi"} <= set(body["forecast"][0])
    assert body["time"] == "2026-09-27T12:00:00+07:00"
    assert body["note"] is None  # Pathum Thani is inside Thailand


def test_alerts_and_burn_time_use_alert_uvi(client):
    body = client.post("/predict", json=PAYLOAD).json()
    alert = body["alert_uvi"]
    assert alert == pytest.approx(max(body["uvi_q90_cqr"], body["uvi"]), abs=0.01)
    assert body["burn_minutes"] == burn_minutes(alert, "III")
    assert body["alert_level"] == WHO_LEVELS[int(who_level(alert))]


def test_point_above_q90_alert_uses_point_not_q90(client):
    # item A: q90 below the point value must not lower the warning
    main.app.state.bundle = fake_bundle(cmf=(0.95, 0.7, 0.7), q=(0.3, 0.4, 0.45, 0.5))
    body = client.post("/predict", json=PAYLOAD).json()
    assert body["interval_adjusted"] is True
    assert body["uvi_range"][1] == pytest.approx(body["uvi"], abs=0.01)  # widened, not clipped
    assert body["uvi_q90_cqr"] < body["uvi"]
    assert body["alert_uvi"] == pytest.approx(body["uvi"], abs=0.01)
    assert body["burn_minutes"] == burn_minutes(body["alert_uvi"], "III")
    assert body["burn_minutes"] < burn_minutes(body["uvi_q90_cqr"], "III")
    assert body["alert_level"] == WHO_LEVELS[int(who_level(body["uvi"]))]


def test_missing_live_data_flagged_or_503(client, monkeypatch):
    # item B: a short gap in the current hour is filled and flagged
    raw = synthetic_raw()
    now_row = raw["time_utc"] == pd.Timestamp("2026-09-27 06:00", tz="UTC")  # 12:00-13:00 local
    raw.loc[now_row, ["cloud_cover", "pm2_5"]] = np.nan
    monkeypatch.setattr(inf, "fetch_live", lambda lat, lon: raw)
    body = client.post("/predict", json=PAYLOAD).json()
    assert body["data_imputed"] is True and body["time"] == "2026-09-27T12:00:00+07:00"
    assert not all(h["data_imputed"] for h in body["forecast"])
    # a long gap covering the current hour: 503, never another hour
    gap = raw["time_utc"].between(
        pd.Timestamp("2026-09-27 01:00", tz="UTC"), pd.Timestamp("2026-09-27 10:00", tz="UTC")
    )
    raw2 = synthetic_raw()
    raw2.loc[gap, "temperature_2m"] = np.nan
    monkeypatch.setattr(inf, "fetch_live", lambda lat, lon: raw2)
    r = client.post("/predict", json=PAYLOAD)
    assert r.status_code == 503 and r.json()["disclaimer"] == DISCLAIMER
    fc = client.get("/forecast", params={"lat": 14.02, "lon": 100.52, "hours": 6})
    assert fc.status_code == 200  # forecast still lists the later hours that exist


def test_forecast_endpoint(client):
    r = client.get("/forecast", params={"lat": 14.02, "lon": 100.52, "hours": 12})
    body = r.json()
    assert r.status_code == 200 and body["disclaimer"] == DISCLAIMER
    assert 1 <= len(body["hours"]) <= 12
    assert all(h["uvi_range"][0] <= h["uvi"] <= h["uvi_range"][1] for h in body["hours"])


def test_errors_carry_disclaimer(client, monkeypatch):
    bad = client.post("/predict", json={"lat": 200, "lon": 100.5, "skin_type": "III"})
    assert bad.status_code == 422 and bad.json()["disclaimer"] == DISCLAIMER
    skin = client.post("/predict", json={**PAYLOAD, "skin_type": "IX"})
    assert skin.status_code == 422 and skin.json()["disclaimer"] == DISCLAIMER
    fc = client.get("/forecast", params={"lat": 14, "lon": 100, "hours": 99})
    assert fc.status_code == 422 and fc.json()["disclaimer"] == DISCLAIMER

    def down(lat, lon):
        import requests

        raise requests.ConnectionError("offline")

    monkeypatch.setattr(inf, "fetch_live", down)
    up = client.post("/predict", json=PAYLOAD)
    assert up.status_code == 502 and up.json()["disclaimer"] == DISCLAIMER
    img = client.post("/sky-image", files={"file": ("x.png", b"not an image", "image/png")})
    assert img.status_code == 415 and img.json()["disclaimer"] == DISCLAIMER


def test_outside_thailand_note(client):
    body = client.post("/predict", json={**PAYLOAD, "lat": 35.68, "lon": 139.69}).json()
    assert body["note"] and "นอกประเทศไทย" in body["note"]


@pytest.mark.parametrize("fmt", ["PNG", "JPEG"])
def test_sky_image_result_and_nothing_stored(client, fmt):
    project = [ROOT / "source_code", ROOT / "docs", ROOT / "dataset"]
    temp = Path(tempfile.gettempdir())
    skip_dirs = {"node_modules", ".expo", "dist", "__pycache__", ".pytest_cache"}

    def snapshot(dirs):
        files = set()
        for d in dirs:
            for dirpath, subdirs, names in os.walk(d):
                subdirs[:] = [s for s in subdirs if s not in skip_dirs and "pytest-of" not in s]
                files.update(os.path.join(dirpath, n) for n in names)
        return files

    def is_upload(path, upload):
        """Image file or a copy of the uploaded bytes (other programs also write to Temp)."""
        try:
            head = Path(path).read_bytes()
        except OSError:
            return False
        return head[:4] in (b"\x89PNG", b"\xff\xd8\xff\xe0", b"\xff\xd8\xff\xdb") or (
            upload[:64] in head
        )

    upload = png_bytes(fmt=fmt)
    before_project, before_temp = snapshot(project), snapshot([temp])
    r = client.post("/sky-image", files={"file": (f"sky.{fmt.lower()}", upload, "image/*")})
    new_project = snapshot(project) - before_project
    new_temp = {p for p in snapshot([temp]) - before_temp if is_upload(p, upload)}
    assert r.status_code == 200
    body = r.json()
    assert body["stored"] is False and body["disclaimer"] == DISCLAIMER
    assert abs(sum(body["sky_class_probs"].values()) - 1) < 0.02
    assert (
        body["sky_class"] in SWIM_CLASS_TH
        and body["sky_class_th"] == SWIM_CLASS_TH[body["sky_class"]]
    )
    assert body["sky_confidence"] == pytest.approx(max(body["sky_class_probs"].values()))
    assert body["sky_confidence"] == pytest.approx(body["sky_class_probs"][body["sky_class"]])
    # the CCSN head (genus / UV cloud group) missed its criteria and is not shown in the app
    assert not {"genus", "cloud_group", "cloud_group_th", "cloud_group_probs"} & set(body)
    assert 0 <= body["cloud_fraction_rb"] <= 1
    assert set(body["reliability"]) == {"sky_class", "cloud_fraction_rb"}
    assert new_project == set(), f"files written: {sorted(new_project)[:5]}"
    assert new_temp == set(), f"image files written to Temp: {sorted(new_temp)[:5]}"


def test_sky_image_never_changes_uvi(client):
    first = client.post("/predict", json=PAYLOAD).json()
    for color in ((250, 250, 250), (20, 60, 200)):
        client.post("/sky-image", files={"file": ("s.png", png_bytes(color), "image/png")})
    second = client.post("/predict", json=PAYLOAD).json()
    assert first == second
    assert "sky" not in main.PredictRequest.model_fields  # /predict takes no image input


def test_cors_origins_from_env_or_expo_web_default():
    assert main.cors_origins({}) == main.DEFAULT_CORS_ORIGINS
    assert main.cors_origins({"CORS_ORIGINS": "  "}) == main.DEFAULT_CORS_ORIGINS
    got = main.cors_origins({"CORS_ORIGINS": "http://a.test:8081/, http://b.test ,"})
    assert got == ["http://a.test:8081", "http://b.test"]


def test_cors_allows_expo_web_origin_only(client):
    ok = main.cors_origins()[0]  # the default Expo web origin unless .env sets CORS_ORIGINS
    pre = client.options(
        "/predict",
        headers={
            "Origin": ok,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert pre.status_code == 200 and pre.headers["access-control-allow-origin"] == ok
    r = client.post("/predict", json=PAYLOAD, headers={"Origin": ok})
    assert r.status_code == 200 and r.headers["access-control-allow-origin"] == ok
    evil = client.post("/predict", json=PAYLOAD, headers={"Origin": "http://evil.test"})
    assert "access-control-allow-origin" not in evil.headers
    assert "access-control-allow-origin" not in client.get("/health").headers  # no Origin


def jpeg_with_exif() -> bytes:
    """JPEG carrying phone-like EXIF: camera model and a GPS position (Pathum Thani)."""
    exif = Image.Exif()
    exif[0x0110] = "SM-TEST-MODEL"  # Model
    exif[0x8825] = {1: "N", 2: (14.0, 1.0, 12.0), 3: "E", 4: (100.0, 31.0, 12.0)}  # GPSInfo
    buf = io.BytesIO()
    Image.new("RGB", (300, 200), (90, 140, 220)).save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def test_has_exif_detects_gps_and_reencoding_removes_it():
    raw = jpeg_with_exif()
    assert has_exif(raw) is True
    # re-encoding the pixels (what the app's image-manipulator does) leaves no EXIF
    buf = io.BytesIO()
    Image.open(io.BytesIO(raw)).convert("RGB").save(buf, format="JPEG", quality=80)
    assert has_exif(buf.getvalue()) is False
    assert has_exif(png_bytes()) is False and has_exif(png_bytes(fmt="JPEG")) is False
    assert has_exif(b"not an image") is False


def test_sky_image_logs_only_exif_boolean(client, caplog):
    caplog.set_level("INFO", logger="uvguard.api")
    r = client.post("/sky-image", files={"file": ("s.jpg", jpeg_with_exif(), "image/jpeg")})
    assert r.status_code == 200
    lines = [rec.getMessage() for rec in caplog.records if "has_exif" in rec.getMessage()]
    assert lines == ["sky-image upload has_exif=True"]
    text = caplog.text
    assert "SM-TEST-MODEL" not in text and "GPS" not in text and "14.0" not in text
    caplog.clear()
    client.post("/sky-image", files={"file": ("s.jpg", png_bytes(fmt="JPEG"), "image/jpeg")})
    assert "sky-image upload has_exif=False" in caplog.text


def test_app_sky_class_names_match_api():
    """The app's top-2 list (app/src/lib/sky.ts) uses the same Thai names as the API."""
    ts = (ROOT / "source_code" / "app" / "src" / "lib" / "sky.ts").read_text(encoding="utf-8")
    block = ts.split("export const SKY_CLASS_TH", 1)[1].split("};", 1)[0]
    pairs = dict(re.findall(r"^\s*(\w+): '([^']+)',", block, flags=re.M))
    assert pairs == SWIM_CLASS_TH


def test_configure_logging_adds_one_info_handler():
    logger = logging.getLogger("uvguard.test_configure_logging")
    main.configure_logging(logger)
    main.configure_logging(logger)
    assert len(logger.handlers) == 1 and logger.level == logging.INFO
