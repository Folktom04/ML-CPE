"""Tests for src.users and the /users endpoints (day 19).

Every test runs on SQLite and, when ``TEST_DATABASE_URL`` is set (environment or ``.env``),
also on that PostgreSQL test database (same rule as ``test_db.py``: its name must contain
"test"; tables are dropped and recreated).
"""

import logging
from datetime import datetime, timezone

import pytest
from api import main
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError, OperationalError
from src import db, users
from src.db import Measurement, NotificationLog, PushToken, User
from tests.test_db import BACKENDS, PG_URL, _drop_everything
from tests.test_inference import fake_bundle

DEV = "3f2c9a1e-7b4d-4e8a-9c21-5d6f0b8a4e17"  # letters too, so .upper() differs
OTHER = "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
NOW = datetime(2026, 9, 28, 6, 0, tzinfo=timezone.utc)


@pytest.fixture(params=BACKENDS)
def engine(request, tmp_path):
    if request.param == "sqlite":
        url = f"sqlite:///{(tmp_path / 'users.sqlite').as_posix()}"
    else:
        assert "test" in (make_url(PG_URL).database or "").lower()
        url = PG_URL
    eng = db.make_engine(url)
    _drop_everything(eng)
    db.Base.metadata.create_all(eng)
    yield eng
    _drop_everything(eng)
    eng.dispose()


@pytest.fixture
def session(engine):
    with db.make_session_factory(engine)() as s:
        yield s


@pytest.fixture
def client(engine):
    main.app.state.bundle = fake_bundle()
    main.app.state.db_engine = engine
    main.app.state.db_fallback = False
    with TestClient(main.app) as c:
        yield c


def hdr(device=DEV):
    return {"X-Device-Id": device}


# --- src.users -------------------------------------------------------------------------------


@pytest.mark.parametrize("alert,safe", [(6, 4), (8, 6), (11, 9), (3, 1)])
def test_safe_threshold_follows_alert(alert, safe):
    assert users.safe_threshold_for(alert) == safe


@pytest.mark.parametrize("alert", [2.9, 11.1, 0, 20])
def test_safe_threshold_rejects_out_of_range(alert):
    with pytest.raises(ValueError):
        users.safe_threshold_for(alert)


def test_device_id_format_and_mask():
    assert users.valid_device_id(DEV)
    assert not users.valid_device_id(None)
    assert not users.valid_device_id("short")
    assert not users.valid_device_id("x" * 65)
    assert not users.valid_device_id("a b c d e f g h i j")
    masked = users.mask_device_id(DEV)
    assert DEV not in masked and "36" in masked


def test_device_matches_is_exact():
    u = User(device_id=DEV, skin_type="III")
    assert users.device_matches(u, DEV)
    assert not users.device_matches(u, OTHER)
    assert not users.device_matches(u, None)
    assert not users.device_matches(u, DEV.upper())


def test_register_is_idempotent_and_derives_safe(session):  # "2" = digit string
    u, created = users.register(session, DEV, {"skin_type": "2", "alert_threshold": 11})
    assert created and (u.skin_type, u.alert_threshold, u.safe_threshold) == ("II", 11, 9)
    again, created2 = users.register(session, DEV, {"skin_type": "IV"})
    assert not created2 and again.id == u.id and again.skin_type == "IV"
    assert session.scalar(select(func.count()).select_from(User)) == 1
    with pytest.raises(ValueError):
        users.register(session, OTHER, {})  # new user needs a skin type


def test_apply_settings_validates(session):
    u, _ = users.register(session, DEV, {"skin_type": "III"})
    assert (u.alert_threshold, u.safe_threshold, u.alert_burn_minutes) == (8, 6, 30)
    users.apply_settings(u, {"alert_threshold": 6, "notify_enabled": False, "skin_type": None})
    assert (u.alert_threshold, u.safe_threshold, u.notify_enabled, u.skin_type) == (
        6,
        4,
        False,
        "III",
    )
    for bad in ({"alert_burn_minutes": 4}, {"alert_threshold": 12}, {"safe_threshold": 1}):
        with pytest.raises(ValueError):
            users.apply_settings(u, bad)


def test_get_by_device(session):
    assert users.get_by_device(session, DEV) is None
    u, _ = users.register(session, DEV, {"skin_type": "I"})
    assert users.get_by_device(session, DEV).id == u.id


# --- /users endpoints -----------------------------------------------------------------------


def test_create_user_and_reregister(client):
    r = client.post("/users", json={"skin_type": "III"}, headers=hdr())
    assert r.status_code == 201
    body = r.json()
    assert body["skin_type"] == "III" and body["alert_threshold"] == 8
    assert body["safe_threshold"] == 6 and body["notify_enabled"] is True
    assert "device_id" not in body and DEV not in r.text
    assert body["disclaimer"]
    r2 = client.post("/users", json={"skin_type": "V"}, headers=hdr())
    assert r2.status_code == 200 and r2.json()["id"] == body["id"]
    assert r2.json()["skin_type"] == "V"


@pytest.mark.parametrize("headers", [{}, {"X-Device-Id": "short"}])
def test_create_user_needs_device_id(client, headers):
    r = client.post("/users", json={"skin_type": "III"}, headers=headers)
    assert r.status_code == 400


@pytest.mark.parametrize(
    "body",
    [{}, {"skin_type": "VII"}, {"skin_type": "III", "alert_threshold": 12}],
)
def test_create_user_rejects_bad_body(client, body):
    assert client.post("/users", json=body, headers=hdr()).status_code == 422


def test_update_settings_owner_only(client):
    uid = client.post("/users", json={"skin_type": "III"}, headers=hdr()).json()["id"]
    r = client.put(
        f"/users/{uid}/settings",
        json={"alert_threshold": 11, "alert_burn_minutes": 60, "notify_enabled": False},
        headers=hdr(),
    )
    assert r.status_code == 200
    b = r.json()
    assert (b["alert_threshold"], b["safe_threshold"], b["alert_burn_minutes"]) == (11, 9, 60)
    assert b["notify_enabled"] is False and b["skin_type"] == "III"
    wrong = client.put(f"/users/{uid}/settings", json={"skin_type": "I"}, headers=hdr(OTHER))
    assert wrong.status_code == 403
    assert client.put(f"/users/{uid}/settings", json={"skin_type": "I"}).status_code == 403
    missing = client.put("/users/99999/settings", json={"skin_type": "I"}, headers=hdr())
    assert missing.status_code == 404


@pytest.mark.parametrize(
    "body",
    [{"safe_threshold": 2}, {"alert_threshold": 2}, {"alert_burn_minutes": 300}, {"x": 1}],
)
def test_update_settings_rejects_bad_values(client, body):
    uid = client.post("/users", json={"skin_type": "III"}, headers=hdr()).json()["id"]
    assert client.put(f"/users/{uid}/settings", json=body, headers=hdr()).status_code == 422


def test_delete_user_cascades(client, engine):
    uid = client.post("/users", json={"skin_type": "III"}, headers=hdr()).json()["id"]
    keep = client.post("/users", json={"skin_type": "IV"}, headers=hdr(OTHER)).json()["id"]
    with db.make_session_factory(engine)() as s:
        u = s.get(User, uid)
        tok = PushToken(user=u, token="ExponentPushToken[abc]", platform="android")
        s.add_all(
            [tok, Measurement(user=u, measured_at=NOW, lat=14.02, lon=100.52, source="field")]
        )
        s.flush()
        s.add(
            NotificationLog(
                user=u, push_token_id=tok.id, type="high_uv", title="t", body="b", status="sent"
            )
        )
        s.commit()
    assert client.delete(f"/users/{uid}", headers=hdr(OTHER)).status_code == 403
    assert client.delete(f"/users/{uid}").status_code == 403
    r = client.delete(f"/users/{uid}", headers=hdr())
    assert r.status_code == 204 and r.content == b""
    with db.make_session_factory(engine)() as s:
        for model in (User, PushToken, Measurement, NotificationLog):
            n = s.scalar(select(func.count()).select_from(model))
            assert n == (1 if model is User else 0), model.__name__
        assert s.get(User, keep) is not None
    assert client.delete(f"/users/{uid}", headers=hdr()).status_code == 404
    again = client.post("/users", json={"skin_type": "III"}, headers=hdr())
    assert again.status_code == 201 and again.json()["id"] != uid  # a fresh user


def test_device_id_never_logged(client, caplog, engine, monkeypatch):
    caplog.set_level(logging.DEBUG)
    uid = client.post("/users", json={"skin_type": "III"}, headers=hdr()).json()["id"]
    client.put(f"/users/{uid}/settings", json={"alert_threshold": 6}, headers=hdr())
    client.put(f"/users/{uid}/settings", json={"skin_type": "I"}, headers=hdr(OTHER))
    client.post("/users", json={"skin_type": "III"}, headers=hdr("bad id " * 3))

    def boom(*a, **k):  # a database outage must not leak the device id either
        raise OperationalError("INSERT ...", {"device_id": DEV}, Exception(f"down {DEV}"))

    monkeypatch.setattr(users, "register", boom)
    r = client.post("/users", json={"skin_type": "III"}, headers=hdr())
    assert r.status_code == 503 and r.json()["detail"] == "database unavailable"
    assert DEV not in r.text
    client.delete(f"/users/{uid}", headers=hdr())
    text = caplog.text
    assert "user %d created" % uid in text and "user %d deleted" % uid in text
    for secret in (DEV, OTHER, "bad id"):
        assert secret not in text


def test_engine_hides_sql_parameters(session):
    users.register(session, DEV, {"skin_type": "III"})
    session.add(User(device_id=DEV, skin_type="III"))  # duplicate device id
    with pytest.raises(IntegrityError) as exc:
        session.commit()
    session.rollback()
    assert "SQL parameters hidden" in str(exc.value)
    # PostgreSQL's own DETAIL line still names the value ("Key (device_id)=(...) already
    # exists"), so the API must never log or return exception text: see the next test.


def test_integrity_error_is_409_without_database_text(client, caplog, monkeypatch):
    caplog.set_level(logging.DEBUG)
    assert client.post("/users", json={"skin_type": "III"}, headers=hdr()).status_code == 201

    def duplicate(session, device_id, settings):  # a real unique-violation from the database
        session.add(User(device_id=device_id, skin_type="III"))
        session.commit()

    monkeypatch.setattr(users, "register", duplicate)
    r = client.post("/users", json={"skin_type": "III"}, headers=hdr())
    assert r.status_code == 409
    assert r.json()["detail"] == "conflict with existing data" and r.json()["disclaimer"]
    for leaked in (DEV, "Key (", "duplicate", "UNIQUE", "IntegrityError", "INSERT"):
        assert leaked not in r.text  # nothing from the database reaches the client
    assert "IntegrityError" in caplog.text and DEV not in caplog.text


def test_cors_allows_delete_and_device_header():
    assert main.cors_origins({})  # defaults exist
    mw = next(m for m in main.app.user_middleware if "CORS" in m.cls.__name__)
    assert "DELETE" in mw.kwargs["allow_methods"]
    assert "X-Device-Id" in mw.kwargs["allow_headers"]
