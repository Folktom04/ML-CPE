"""Day 19: anonymous users and their notification settings (``/users`` endpoints).

A user is one installed app, identified by a random ``device_id`` (UUID made on the phone).
The device id works as a bearer secret: ``PUT`` / ``DELETE /users/{id}`` must send it in the
``X-Device-Id`` header and it must match the stored one. It is never returned by the API and
never logged (``mask_device_id`` is the only form that may appear in logs).

Hysteresis: the "safe again" level always follows the alert level,
``safe_threshold = alert_threshold - SAFE_GAP`` (6 -> 4, 8 -> 6, 11 -> 9), so the database
rule ``safe_threshold < alert_threshold`` always holds and the client cannot set it.
"""

from __future__ import annotations

import hmac
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.db import User
from src.risk import normalize_skin_type

SAFE_GAP = 2.0
ALERT_MIN, ALERT_MAX = 3.0, 11.0
BURN_MIN, BURN_MAX = 5, 240
DEVICE_ID_RE = re.compile(r"^[A-Za-z0-9-]{16,64}$")
SETTING_FIELDS = (
    "skin_type",
    "notify_enabled",
    "alert_threshold",
    "alert_burn_minutes",
    "province",
)


def _skin(value: Any) -> str:
    """Skin type I-VI from a Roman numeral or 1-6 (int or digit string)."""
    return normalize_skin_type(int(value) if str(value).strip().isdigit() else value)


def valid_device_id(device_id: str | None) -> bool:
    """Whether ``device_id`` looks like an app-made id (16-64 letters, digits or dashes).

    Args:
        device_id: Value of the ``X-Device-Id`` header.

    Returns:
        True if the format is acceptable.
    """
    return bool(device_id) and DEVICE_ID_RE.fullmatch(device_id) is not None


def mask_device_id(device_id: str) -> str:
    """Log-safe form of a device id: only its length, never any of its characters.

    Args:
        device_id: Device id.

    Returns:
        e.g. ``"<device id, 36 chars>"``.
    """
    return f"<device id, {len(device_id)} chars>"


def safe_threshold_for(alert_threshold: float) -> float:
    """The "safe again" UVI for an alert UVI (hysteresis gap ``SAFE_GAP``).

    Args:
        alert_threshold: UVI at or above which the high-UV alert is sent.

    Returns:
        ``alert_threshold - SAFE_GAP``.

    Raises:
        ValueError: If the alert threshold is outside ``[ALERT_MIN, ALERT_MAX]``.
    """
    a = float(alert_threshold)
    if not ALERT_MIN <= a <= ALERT_MAX:
        raise ValueError(f"alert_threshold must be within {ALERT_MIN:g}-{ALERT_MAX:g}")
    return a - SAFE_GAP


def device_matches(user: User, device_id: str | None) -> bool:
    """Constant-time check that ``device_id`` is the one stored for ``user``.

    Args:
        user: Stored user.
        device_id: Value of the ``X-Device-Id`` header (may be missing).

    Returns:
        True only for an exact match.
    """
    if not device_id:
        return False
    return hmac.compare_digest(user.device_id.encode(), device_id.encode())


def apply_settings(user: User, settings: dict[str, Any]) -> User:
    """Copy validated settings onto ``user`` (``None`` values are ignored).

    ``safe_threshold`` is always derived from ``alert_threshold``.

    Args:
        user: User to change (not committed here).
        settings: Any of ``SETTING_FIELDS``.

    Returns:
        The same user.

    Raises:
        ValueError: On an unknown field or an out-of-range value.
    """
    unknown = set(settings) - set(SETTING_FIELDS)
    if unknown:
        raise ValueError(f"unknown settings: {sorted(unknown)}")
    for key, value in settings.items():
        if value is None:
            continue
        if key == "skin_type":
            user.skin_type = _skin(value)
        elif key == "alert_threshold":
            user.safe_threshold = safe_threshold_for(value)
            user.alert_threshold = float(value)
        elif key == "alert_burn_minutes":
            if not BURN_MIN <= int(value) <= BURN_MAX:
                raise ValueError(f"alert_burn_minutes must be within {BURN_MIN}-{BURN_MAX}")
            user.alert_burn_minutes = int(value)
        else:
            setattr(user, key, value)
    return user


def get_by_device(session: Session, device_id: str) -> User | None:
    """User registered with ``device_id``, if any.

    Args:
        session: Open session.
        device_id: Device id.

    Returns:
        The user or None.
    """
    return session.scalars(select(User).where(User.device_id == device_id)).first()


def register(session: Session, device_id: str, settings: dict[str, Any]) -> tuple[User, bool]:
    """Create the user for ``device_id``, or update and return the existing one.

    Registering again with the same device id (e.g. the app lost its user id) is idempotent:
    the settings are applied to the existing user.

    Args:
        session: Open session (committed here).
        device_id: Valid device id (``valid_device_id``).
        settings: Settings; ``skin_type`` is required for a new user.

    Returns:
        ``(user, created)``.

    Raises:
        ValueError: On invalid settings or a missing skin type for a new user.
    """
    user = get_by_device(session, device_id)
    created = user is None
    if created:
        if not settings.get("skin_type"):
            raise ValueError("skin_type is required")
        alert = float(settings.get("alert_threshold") or 8.0)
        user = User(
            device_id=device_id,
            skin_type=_skin(settings["skin_type"]),
            notify_enabled=True,
            alert_threshold=alert,
            safe_threshold=safe_threshold_for(alert),
            alert_burn_minutes=30,
        )
        session.add(user)
    apply_settings(user, settings)
    try:
        session.commit()
    except IntegrityError:  # same device registered concurrently: use that row
        session.rollback()
        user = get_by_device(session, device_id)
        if user is None:
            raise
        apply_settings(user, settings)
        session.commit()
        created = False
    return user, created
