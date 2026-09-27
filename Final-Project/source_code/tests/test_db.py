"""Tests for the database schema, privacy helpers and the Alembic migration (day 17).

Every test runs on SQLite. If ``TEST_DATABASE_URL`` is set (environment or ``.env``), every
test also runs on that PostgreSQL database. It must be a throwaway database whose name
contains "test": the tests drop and recreate all tables.
"""

import io
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from dotenv import load_dotenv
from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError, StatementError
from src import db
from src.db import Measurement, NotificationLog, PushToken, User
from src.fetch_data import ROOT

load_dotenv(ROOT / ".env")
PG_URL = os.environ.get("TEST_DATABASE_URL", "").strip()
BKK = ZoneInfo("Asia/Bangkok")
NOW = datetime(2026, 9, 27, 6, 0, tzinfo=timezone.utc)
TABLES = {"users", "push_tokens", "measurements", "notifications_log"}

BACKENDS = [
    "sqlite",
    pytest.param(
        "postgresql",
        marks=pytest.mark.skipif(not PG_URL, reason="TEST_DATABASE_URL not set"),
    ),
]


def _drop_everything(engine):
    db.Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))


@pytest.fixture(params=BACKENDS)
def url(request, tmp_path):
    if request.param == "sqlite":
        return f"sqlite:///{(tmp_path / 'test.sqlite').as_posix()}"
    name = make_url(PG_URL).database or ""
    assert "test" in name.lower(), "TEST_DATABASE_URL must point to a *test* database"
    return PG_URL


@pytest.fixture
def empty_engine(url):
    engine = db.make_engine(url)
    _drop_everything(engine)
    yield engine
    _drop_everything(engine)
    engine.dispose()


@pytest.fixture
def engine(empty_engine):
    db.Base.metadata.create_all(empty_engine)
    return empty_engine


@pytest.fixture
def session(engine):
    with db.make_session_factory(engine)() as s:
        yield s


def add_user(s, device="dev-1", **kw):
    u = User(device_id=device, skin_type=kw.pop("skin_type", "III"), **kw)
    s.add(u)
    s.commit()
    return u


def measurement(user=None, when=NOW, source="api", **kw):
    return Measurement(
        user=user, measured_at=when, lat=14.0234, lon=100.5178, source=source, uvi=7.2, **kw
    )


def log_row(user, when=NOW, token=None, type_="high_uv"):
    return NotificationLog(
        user=user,
        push_token_id=token.id if token else None,
        type=type_,
        sent_at=when,
        uvi=8.4,
        title="UV สูงมาก",
        body="ทาครีมกันแดด",
        status="sent",
    )


def count(s, model, **where):
    q = select(func.count()).select_from(model)
    for k, v in where.items():
        q = q.where(getattr(model, k) == v)
    return s.scalar(q)


# --- schema -------------------------------------------------------------------------------


def test_tables_and_requested_columns(engine):
    insp = inspect(engine)
    assert TABLES <= set(insp.get_table_names())
    cols = {t: {c["name"] for c in insp.get_columns(t)} for t in TABLES}
    assert "alert_burn_minutes" in cols["users"]
    assert {"sky_confidence", "interval_adjusted", "data_imputed"} <= cols["measurements"]
    assert "image" not in " ".join(cols["measurements"])  # photos are never stored
    assert not {"name", "email", "phone"} & cols["users"]  # no direct identifiers


def test_user_defaults(session):
    u = add_user(session)
    session.expire_all()
    u = session.get(User, u.id)
    assert (u.notify_enabled, u.alert_threshold, u.safe_threshold) == (True, 8.0, 6.0)
    assert u.alert_burn_minutes == 30
    assert u.created_at.tzinfo is not None


def test_server_defaults_apply_to_raw_inserts(engine):
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO users (device_id, skin_type) VALUES ('raw', 'II')"))
    with db.make_session_factory(engine)() as s:
        u = s.scalar(select(User).where(User.device_id == "raw"))
        assert u.alert_burn_minutes == 30 and u.notify_enabled is True
        assert u.created_at.utcoffset() == timedelta(0)
        assert abs(u.created_at - db.utc_now()) < timedelta(minutes=5)


# --- time zones ---------------------------------------------------------------------------


def test_every_time_column_is_timezone_aware_type():
    time_cols = [
        c
        for t in db.Base.metadata.tables.values()
        for c in t.columns
        if isinstance(c.type, db.UTCDateTime)
    ]
    assert len(time_cols) == 7
    assert all(c.type.impl.timezone for c in time_cols)
    for t in db.Base.metadata.tables.values():
        for c in t.columns:
            if c.name.endswith("_at"):
                assert isinstance(c.type, db.UTCDateTime), f"{t.name}.{c.name}"


def test_times_roundtrip_as_utc_aware(engine):
    local = datetime(2026, 9, 27, 13, 30, tzinfo=BKK)  # 06:30 UTC
    with db.make_session_factory(engine)() as s:
        u = add_user(s)
        tok = PushToken(
            user=u, token="ExponentPushToken[a]", platform="android", last_seen_at=local
        )
        s.add_all([tok, measurement(u, when=local)])
        s.commit()
        s.add(log_row(u, when=local, token=tok))
        s.commit()
    with db.make_session_factory(engine)() as s:  # fresh session: values come from the DB
        m = s.scalars(select(Measurement)).one()
        n = s.scalars(select(NotificationLog)).one()
        t = s.scalars(select(PushToken)).one()
        u = s.scalars(select(User)).one()
        for v in (m.measured_at, n.sent_at, t.last_seen_at, m.created_at, u.updated_at):
            assert v.tzinfo is not None and v.utcoffset() == timedelta(0)
        assert m.measured_at == local and m.measured_at.hour == 6 and m.measured_at.minute == 30
        assert n.sent_at == local and t.last_seen_at == local


def test_naive_datetime_rejected(session):
    u = add_user(session)
    session.add(measurement(u, when=datetime(2026, 9, 27, 13, 0)))
    with pytest.raises(StatementError, match="naive datetime"):
        session.commit()
    session.rollback()


def test_updated_at_changes_on_update(session):
    u = add_user(session)
    first = u.updated_at
    u.province = "ปทุมธานี"
    session.commit()
    assert u.updated_at >= first and u.updated_at.tzinfo is not None


# --- constraints --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "make",
    [
        lambda s: s.add(User(device_id="x", skin_type="VII")),
        lambda s: s.add(User(device_id="x", skin_type="I", alert_threshold=6, safe_threshold=7)),
        lambda s: s.add(User(device_id="x", skin_type="I", alert_burn_minutes=1)),
        lambda s: s.add(measurement(source="satellite")),
        lambda s: s.add(measurement(sky_confidence=1.5)),
        lambda s: s.add(measurement(cloud_fraction_rb=-0.1)),
    ],
    ids=["skin", "safe>=alert", "burn", "source", "sky_conf", "cloud_fraction"],
)
def test_check_constraints(session, make):
    make(session)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_unique_device_and_token(session):
    u = add_user(session)
    session.add(User(device_id="dev-1", skin_type="II"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    session.add_all([PushToken(user=u, token="t", platform="ios")])
    session.commit()
    session.add(PushToken(user=u, token="t", platform="android"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_coordinates_rounded_to_about_1_km(session):
    session.add(measurement())
    session.commit()
    session.expire_all()
    m = session.scalars(select(Measurement)).one()
    assert (m.lat, m.lon) == (14.02, 100.52)
    assert db.round_coord(-33.8688) == -33.87


# --- privacy: delete user, purge ------------------------------------------------------------


def _populate(s, device):
    u = add_user(s, device)
    tok = PushToken(user=u, token=f"tok-{device}", platform="ios")
    s.add_all([tok, measurement(u), measurement(u, source="field")])
    s.commit()
    s.add_all([log_row(u, token=tok), log_row(u, type_="safe_again")])
    s.commit()
    return u.id


@pytest.mark.parametrize("how", ["orm", "sql"])
def test_delete_user_removes_all_linked_rows(session, how):
    gone, kept = _populate(session, "a"), _populate(session, "b")
    if how == "orm":
        assert db.delete_user(session, gone) is True
        assert db.delete_user(session, gone) is False
    else:  # ON DELETE CASCADE in the database itself, without the ORM
        session.execute(text("DELETE FROM users WHERE id = :i"), {"i": gone})
        session.commit()
    session.expire_all()
    for model in (PushToken, Measurement, NotificationLog):
        assert count(session, model, user_id=gone) == 0, model.__tablename__
    assert count(session, User) == 1
    assert count(session, PushToken, user_id=kept) == 1
    assert count(session, Measurement, user_id=kept) == 2  # includes source='field'
    assert count(session, NotificationLog, user_id=kept) == 2


def test_deleting_push_token_keeps_log_with_null_token(session):
    _populate(session, "a")
    session.execute(text("DELETE FROM push_tokens"))
    session.commit()
    session.expire_all()
    logs = session.scalars(select(NotificationLog)).all()
    assert len(logs) == 2 and all(n.push_token_id is None for n in logs)


def test_purge_old_rows(session):
    u = add_user(session)
    old, recent = NOW - timedelta(days=100), NOW - timedelta(days=10)
    for when in (old, recent):
        for src in db.SOURCES:
            session.add(measurement(u, when=when, source=src))
        session.add(measurement(None, when=when))  # anonymous API call
        session.add(log_row(u, when=when))
    session.commit()
    n = db.purge_old_rows(session, days=90, now=NOW)
    assert n == {"measurements": len(db.SOURCES), "notifications_log": 1}
    session.expire_all()
    left = session.scalars(select(Measurement)).all()
    assert all(m.measured_at >= NOW - timedelta(days=90) or m.source == "field" for m in left)
    assert count(session, Measurement, source="field") == 2  # field data kept at any age
    assert count(session, NotificationLog) == 1
    assert count(session, User) == 1 and count(session, PushToken) == 0
    assert db.purge_old_rows(session, days=90, now=NOW) == {
        "measurements": 0,
        "notifications_log": 0,
    }
    with pytest.raises(ValueError):
        db.purge_old_rows(session, days=0)


def test_purge_boundary_uses_utc_instant(session):
    u = add_user(session)
    cutoff = NOW - timedelta(days=90)
    session.add_all(
        [
            measurement(u, when=(cutoff - timedelta(minutes=1)).astimezone(BKK)),
            measurement(u, when=(cutoff + timedelta(minutes=1)).astimezone(BKK)),
        ]
    )
    session.commit()
    assert db.purge_old_rows(session, now=NOW.astimezone(BKK))["measurements"] == 1


# --- engine / URL -----------------------------------------------------------------------------


def test_database_url_env_and_sqlite_fallback_warning(caplog):
    pg = "postgresql+psycopg://u:p@localhost:5432/uvguard"
    assert db.database_url({"DATABASE_URL": pg}) == (pg, False)
    with caplog.at_level(logging.WARNING, logger="src.db"):
        url, fallback = db.database_url({"DATABASE_URL": "  "})
    assert fallback is True and url.startswith("sqlite:///")
    assert url.endswith("dataset/uvguard.sqlite")
    assert any("FALLBACK" in r.getMessage() for r in caplog.records)


def test_make_engine_backends_and_ping(engine, url):
    assert db.backend_name(engine) == make_url(url).get_backend_name()
    assert db.ping(engine) is True
    if db.backend_name(engine) == "sqlite":
        with engine.connect() as conn:
            assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_ping_false_when_postgres_unreachable(caplog):
    dead = db.make_engine("postgresql+psycopg://u:p@127.0.0.1:1/uvguard_test")
    assert db.backend_name(dead) == "postgresql"
    with caplog.at_level(logging.WARNING, logger="src.db"):
        assert db.ping(dead) is False
    assert any("not reachable" in r.getMessage() for r in caplog.records)


# --- migration ------------------------------------------------------------------------------


def alembic_config(buf=None):
    cfg = Config(str(ROOT / "alembic.ini"), output_buffer=buf)
    cfg.attributes["configure_logger"] = False
    return cfg


def test_migration_matches_models_and_downgrades(empty_engine):
    cfg = alembic_config()
    with empty_engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")
    insp = inspect(empty_engine)
    assert TABLES | {"alembic_version"} <= set(insp.get_table_names())
    with empty_engine.connect() as conn:
        diff = compare_metadata(
            MigrationContext.configure(conn, opts={"compare_type": True}), db.Base.metadata
        )
    assert diff == [], diff
    ondelete = {
        (t, fk["referred_table"]): fk["options"].get("ondelete")
        for t in TABLES
        for fk in insp.get_foreign_keys(t)
    }
    assert ondelete[("push_tokens", "users")] == "CASCADE"
    assert ondelete[("measurements", "users")] == "CASCADE"
    assert ondelete[("notifications_log", "users")] == "CASCADE"
    assert ondelete[("notifications_log", "push_tokens")] == "SET NULL"
    with empty_engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.downgrade(cfg, "base")
    assert not TABLES & set(inspect(empty_engine).get_table_names())


def test_migrated_schema_works_with_models(empty_engine):
    cfg = alembic_config()
    with empty_engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")
    with db.make_session_factory(empty_engine)() as s:
        uid = _populate(s, "m")
        assert s.get(User, uid).alert_burn_minutes == 30
        assert db.delete_user(s, uid) and count(s, Measurement) == 0


def test_offline_postgresql_ddl():
    buf = io.StringIO()
    cfg = alembic_config(buf)
    cfg.set_main_option("sqlalchemy.url", "postgresql+psycopg://u:p@localhost/uvguard")
    command.upgrade(cfg, "head", sql=True)
    sql = buf.getvalue()
    for table in TABLES:
        assert f"CREATE TABLE {table}" in sql
    n_time = sum(
        isinstance(c.type, db.UTCDateTime)
        for t in db.Base.metadata.tables.values()
        for c in t.columns
    )
    assert sql.count("TIMESTAMP WITH TIME ZONE") == n_time == 7
    assert "TIMESTAMP WITHOUT" not in sql
    assert sql.count("ON DELETE CASCADE") == 3 and sql.count("ON DELETE SET NULL") == 1


def test_migration_file_is_self_contained():
    files = list((ROOT / "source_code" / "migrations" / "versions").glob("*.py"))
    assert [f.name for f in files] == ["0001_initial_schema.py"]
    code = Path(files[0]).read_text(encoding="utf-8")
    assert "from src" not in code and "import src" not in code
