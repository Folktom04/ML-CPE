"""Day 17: database schema (SQLAlchemy 2.0) for users, push tokens, measurements and alerts.

PostgreSQL is the target (``DATABASE_URL`` in ``.env``). SQLite is only a fallback used when
``DATABASE_URL`` is not set; it is logged as a WARNING and reported by ``/health``. A
configured PostgreSQL that is down is NOT replaced by SQLite (that would split the data).

The schema is created with Alembic (``alembic upgrade head``, ``source_code/migrations``);
``Base.metadata.create_all`` is used by tests only.

Privacy (PDPA, see ``docs/db.md``): no names, e-mails or photos are stored; a user is an
anonymous ``device_id``. Coordinates are rounded to ``COORD_DECIMALS`` (about 1 km). Deleting
a user removes every linked row (``ON DELETE CASCADE``). ``purge_old_rows`` removes
measurements (except ``source='field'``) and notification logs older than ``RETENTION_DAYS``.
All times are stored as UTC-aware datetimes (``UTCDateTime``).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Dialect,
    Engine,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    create_engine,
    delete,
    event,
    func,
    text,
)
from sqlalchemy.engine import make_url
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
    validates,
)
from sqlalchemy.types import DateTime, TypeDecorator
from src.fetch_data import ROOT

SQLITE_FALLBACK_PATH = ROOT / "dataset" / "uvguard.sqlite"
COORD_DECIMALS = 2  # ~1.1 km at the equator
RETENTION_DAYS = 90
SKIN_TYPES = ("I", "II", "III", "IV", "V", "VI")
PLATFORMS = ("ios", "android", "web")
SOURCES = ("api", "phone_lux", "sky_image", "field")
KEEP_SOURCES = ("field",)  # never purged by age (field validation data)
NOTIFICATION_TYPES = ("high_uv", "safe_again", "burn_time")
NOTIFICATION_STATUS = ("sent", "error")

log = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def _in(col: str, values: tuple[str, ...]) -> str:
    """SQL ``col IN (...)`` text for a CHECK constraint."""
    return f"{col} IN ({', '.join(repr(v) for v in values)})"


class UTCDateTime(TypeDecorator):
    """``DateTime(timezone=True)`` that only accepts aware datetimes and returns UTC-aware.

    PostgreSQL stores ``timestamptz``; SQLite has no time zone, so values are written as UTC
    and the UTC zone is attached again on read.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        """Reject naive datetimes and convert to UTC before writing."""
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("naive datetime; pass a timezone-aware value (UTC)")
        value = value.astimezone(timezone.utc)
        return value.replace(tzinfo=None) if dialect.name == "sqlite" else value

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        """Return a UTC-aware datetime."""
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base with a fixed constraint naming convention (stable migrations)."""

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_N_name)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


def _created() -> Mapped[datetime]:
    """``created_at`` column (UTC, set by Python and by the server)."""
    return mapped_column(UTCDateTime(), default=utc_now, server_default=func.now())


class User(Base):
    """Anonymous app user (one per installed device) and their notification settings."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(_in("skin_type", SKIN_TYPES), name="skin_type"),
        CheckConstraint("alert_threshold >= 1 AND alert_threshold <= 20", name="alert_threshold"),
        CheckConstraint("safe_threshold >= 0 AND safe_threshold < alert_threshold", name="safe"),
        CheckConstraint("alert_burn_minutes >= 5 AND alert_burn_minutes <= 240", name="burn"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[str] = mapped_column(String(64), unique=True)
    skin_type: Mapped[str] = mapped_column(String(3))
    province: Mapped[str | None] = mapped_column(String(64))
    notify_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    alert_threshold: Mapped[float] = mapped_column(Float, default=8.0, server_default=text("8"))
    safe_threshold: Mapped[float] = mapped_column(Float, default=6.0, server_default=text("6"))
    alert_burn_minutes: Mapped[int] = mapped_column(Integer, default=30, server_default=text("30"))
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now, server_default=func.now()
    )

    push_tokens: Mapped[list[PushToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    measurements: Mapped[list[Measurement]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    notifications: Mapped[list[NotificationLog]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class PushToken(Base):
    """Expo push token of a user's device."""

    __tablename__ = "push_tokens"
    __table_args__ = (CheckConstraint(_in("platform", PLATFORMS), name="platform"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(String(255), unique=True)
    platform: Mapped[str] = mapped_column(String(10))
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = _created()
    last_seen_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="push_tokens")


class Measurement(Base):
    """One UV estimate or phone reading at a time and (rounded) place.

    ``user_id`` may be NULL for anonymous API calls. No image is ever stored, only the sky
    class/confidence/cloud fraction derived from it.
    """

    __tablename__ = "measurements"
    __table_args__ = (
        CheckConstraint(_in("source", SOURCES), name="source"),
        CheckConstraint("lat >= -90 AND lat <= 90 AND lon >= -180 AND lon <= 180", name="coords"),
        CheckConstraint("sky_confidence >= 0 AND sky_confidence <= 1", name="sky_confidence"),
        CheckConstraint(
            "cloud_fraction_rb >= 0 AND cloud_fraction_rb <= 1", name="cloud_fraction_rb"
        ),
        Index("ix_measurements_user_id_measured_at", "user_id", "measured_at"),
        Index("ix_measurements_source_measured_at", "source", "measured_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    measured_at: Mapped[datetime] = mapped_column(UTCDateTime())
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(16))
    uvi: Mapped[float | None] = mapped_column(Float)
    uvi_lo: Mapped[float | None] = mapped_column(Float)
    uvi_hi: Mapped[float | None] = mapped_column(Float)
    uva_wm2: Mapped[float | None] = mapped_column(Float)
    uvb_wm2: Mapped[float | None] = mapped_column(Float)
    cmf: Mapped[float | None] = mapped_column(Float)
    interval_adjusted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    data_imputed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    lux: Mapped[float | None] = mapped_column(Float)
    sky_class: Mapped[str | None] = mapped_column(String(32))
    sky_confidence: Mapped[float | None] = mapped_column(Float)
    cloud_fraction_rb: Mapped[float | None] = mapped_column(Float)
    openmeteo_uvi: Mapped[float | None] = mapped_column(Float)
    model_version: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = _created()

    user: Mapped[User | None] = relationship(back_populates="measurements")

    @validates("lat", "lon")
    def _round_coord(self, key: str, value: float) -> float:
        """Round coordinates to ``COORD_DECIMALS`` before storing (privacy)."""
        return round_coord(value)


class NotificationLog(Base):
    """Every push notification attempt (used for the 3 h cooldown per type per user)."""

    __tablename__ = "notifications_log"
    __table_args__ = (
        CheckConstraint(_in("type", NOTIFICATION_TYPES), name="type"),
        CheckConstraint(_in("status", NOTIFICATION_STATUS), name="status"),
        Index("ix_notifications_log_user_id_type_sent_at", "user_id", "type", "sent_at"),
        Index("ix_notifications_log_sent_at", "sent_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    push_token_id: Mapped[int | None] = mapped_column(
        ForeignKey("push_tokens.id", ondelete="SET NULL")
    )
    type: Mapped[str] = mapped_column(String(16))
    sent_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    uvi: Mapped[float | None] = mapped_column(Float)
    title: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(8))
    expo_ticket_id: Mapped[str | None] = mapped_column(String(64))
    error: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="notifications")


def round_coord(value: float) -> float:
    """Round a latitude/longitude to ``COORD_DECIMALS`` (about 1 km).

    Args:
        value: Degrees.

    Returns:
        Rounded degrees.
    """
    return round(float(value), COORD_DECIMALS)


def database_url(env: dict[str, str] | None = None) -> tuple[str, bool]:
    """Database URL from ``DATABASE_URL`` (``.env``), or the SQLite fallback.

    Args:
        env: Mapping to read instead of the process environment (tests). When None,
            ``.env`` at the project root is loaded first (existing variables win).

    Returns:
        ``(url, is_fallback)``; a WARNING is logged when the SQLite fallback is used.
    """
    if env is None:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
        env = dict(os.environ)
    url = (env.get("DATABASE_URL") or "").strip()
    if url:
        return url, False
    fallback = f"sqlite:///{SQLITE_FALLBACK_PATH.as_posix()}"
    log.warning(
        "DATABASE_URL is not set: using the SQLite FALLBACK %s (PostgreSQL is the target; "
        "set DATABASE_URL in .env)",
        SQLITE_FALLBACK_PATH,
    )
    return fallback, True


def _sqlite_foreign_keys(dbapi_conn: Any, _record: Any) -> None:
    """Turn on foreign keys (and so ON DELETE CASCADE) for every SQLite connection."""
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


def make_engine(url: str | None = None, echo: bool = False) -> Engine:
    """Create an engine; SQLite gets foreign keys on, PostgreSQL a short connect timeout.

    Bound parameters are hidden from error messages and logs (``hide_parameters``).

    Args:
        url: Database URL (default: ``database_url()``).
        echo: Log SQL.

    Returns:
        SQLAlchemy engine (no connection is opened yet).
    """
    url = url or database_url()[0]
    backend = make_url(url).get_backend_name()
    # hide_parameters: errors and logs never show bound values (device ids, coordinates)
    kwargs: dict[str, Any] = {"echo": echo, "pool_pre_ping": True, "hide_parameters": True}
    if backend == "postgresql":
        kwargs["connect_args"] = {"connect_timeout": 5}
    engine = create_engine(url, **kwargs)
    if backend == "sqlite":
        event.listen(engine, "connect", _sqlite_foreign_keys)
    return engine


def backend_name(engine: Engine) -> str:
    """Dialect name of an engine, e.g. ``"postgresql"`` or ``"sqlite"``."""
    return engine.dialect.name


def ping(engine: Engine) -> bool:
    """Whether the database answers ``SELECT 1``.

    Args:
        engine: Engine to test.

    Returns:
        True if the query succeeds.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # any driver/connection error means "not reachable"
        log.warning("database not reachable (%s): %s", backend_name(engine), exc.__class__.__name__)
        return False


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Session factory bound to ``engine`` (objects stay usable after commit).

    Args:
        engine: Engine.

    Returns:
        ``sessionmaker``.
    """
    return sessionmaker(bind=engine, expire_on_commit=False)


def delete_user(session: Session, user_id: int) -> bool:
    """Delete a user and, through ``ON DELETE CASCADE``, all of their rows.

    Args:
        session: Open session (committed here).
        user_id: User id.

    Returns:
        True if the user existed.
    """
    user = session.get(User, user_id)
    if user is None:
        return False
    session.delete(user)
    session.commit()
    return True


def purge_old_rows(
    session: Session, days: int = RETENTION_DAYS, now: datetime | None = None
) -> dict[str, int]:
    """Delete measurements (except ``KEEP_SOURCES``) and notification logs older than ``days``.

    Args:
        session: Open session (committed here).
        days: Retention period in days.
        now: Aware "current" time (tests); default ``utc_now()``.

    Returns:
        ``{"measurements": n, "notifications_log": n}`` rows deleted.
    """
    if days < 1:
        raise ValueError("days must be >= 1")
    cutoff = (now or utc_now()) - timedelta(days=days)
    m = session.execute(
        delete(Measurement).where(
            Measurement.measured_at < cutoff, Measurement.source.not_in(KEEP_SOURCES)
        )
    )
    n = session.execute(delete(NotificationLog).where(NotificationLog.sent_at < cutoff))
    session.commit()
    counts = {"measurements": m.rowcount, "notifications_log": n.rowcount}
    log.info("purged rows older than %d days: %s", days, counts)
    return counts
