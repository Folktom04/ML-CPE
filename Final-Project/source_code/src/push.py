"""Day 23: server push ("UV สูง" / "ปลอดภัยแล้ว") through the Expo Push Service.

Every ``TICK_MINUTES`` an APScheduler job (``start_scheduler``) runs ``run_tick``:

* Only users who exist on the server (they gave consent in the app), have ``notify_enabled`` and
  an ``active`` push token are considered. The place is the user's **province only**
  (``users.province``, turned into the capital's coordinates from the app's ``provinces.json``);
  a user without a known province is skipped. No coordinates are stored.
* The forecast is fetched once per province per tick.
* ``decide`` uses the hour that contains "now": ``alert_uvi`` (q90 after CQR, never below the
  point UVI) with the WHO rounding of ``risk.reaches_alert`` / ``risk.is_safe_again`` and the
  user's own ``alert_threshold`` / ``safe_threshold`` (hysteresis). Nothing is sent at night,
  and the state is read from today's (Asia/Bangkok) log only, so it resets every night.
  Cooldown: at most one sent notification per type per user per ``COOLDOWN``.
* Every attempt is written to ``notifications_log`` (sent or error). A ``DeviceNotRegistered``
  ticket or receipt sets the token ``active = False``; network errors keep the token and the
  next tick tries again (errors do not count for the cooldown).

Push tokens and device ids are never logged (``mask_token``); log lines hold user ids and
token row ids only. Error texts from Expo are scrubbed of tokens before they are stored.

Manual run (prints the messages, sends nothing, writes nothing)::

    .venv\\Scripts\\python.exe -m src.push --once --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, Callable, Iterable, Protocol
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from src.db import NotificationLog, PushToken, User, make_session_factory, utc_now
from src.metrics import WHO_LEVELS, round_uvi, who_level
from src.provinces import APP_JSON
from src.risk import burn_minutes, is_safe_again, reaches_alert

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
EXPO_RECEIPTS_URL = "https://exp.host/--/api/v2/push/getReceipts"
TICK_MINUTES = 30
COOLDOWN = timedelta(hours=3)
BATCH_SIZE = 100  # Expo accepts at most 100 messages per request
RECEIPT_BATCH = 1000
RECEIPT_WINDOW = (timedelta(minutes=15), timedelta(hours=2))  # receipts are ready after ~15 min
POST_RETRIES = 2
POST_TIMEOUT_S = 10.0
POST_BACKOFF_S = 0.5
RETRY_STATUS = (429, 500, 502, 503, 504)
PUSH_TYPES = ("high_uv", "safe_again")
APP_KIND = {"high_uv": "uv_high", "safe_again": "uv_safe"}  # NotificationKind in the app
CHANNEL_ID = "uv-alerts"  # same Android channel as the local alerts (day 22)
TOKEN_MAX_LEN = 255  # push_tokens.token
TOKEN_RE = re.compile(r"^ExponentPushToken\[[A-Za-z0-9_-]+\]$")
TOKEN_ANYWHERE = re.compile(r"Expo(?:nent)?PushToken\[[^\]]*\]")
TOKEN_PLATFORMS = ("ios", "android")
LOCAL_TZ = ZoneInfo("Asia/Bangkok")
ADVISORY_LOCK_KEY = 23_0023  # pg_try_advisory_xact_lock key: one round at a time across workers
OFF_VALUES = ("0", "off", "false", "no")
NOT_REGISTERED = "DeviceNotRegistered"

log = logging.getLogger("uvguard.push")
_tick_lock = threading.Lock()

PredictFn = Callable[[float, float], pd.DataFrame]


class PushSender(Protocol):
    """What ``run_tick`` needs from a push service (the real one or a fake in tests)."""

    def send(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Send up to ``BATCH_SIZE`` messages; return one Expo ticket per message, in order."""
        ...

    def receipts(self, ids: list[str]) -> dict[str, dict[str, Any]]:
        """Receipts for ticket ids (``{id: {"status": ..., "details": ...}}``)."""
        ...


@dataclass(frozen=True)
class HourNow:
    """The forecast hour that contains "now" for one province."""

    alert_uvi: float
    is_daylight: bool


def mask_token(token: str) -> str:
    """Log-safe form of a push token: only its length.

    Args:
        token: Expo push token.

    Returns:
        e.g. ``"<push token, 41 chars>"``.
    """
    return f"<push token, {len(token)} chars>"


def scrub(message: str) -> str:
    """Remove any Expo push token from a text (Expo error messages quote the token).

    Args:
        message: Text to clean.

    Returns:
        The text with every token replaced by ``<push token>``.
    """
    return TOKEN_ANYWHERE.sub("<push token>", message)


def valid_token(token: Any) -> bool:
    """Whether ``token`` is an ``ExponentPushToken[...]`` of at most ``TOKEN_MAX_LEN`` chars.

    Args:
        token: Value sent by the app.

    Returns:
        True if the format is acceptable.
    """
    return (
        isinstance(token, str)
        and len(token) <= TOKEN_MAX_LEN
        and TOKEN_RE.fullmatch(token) is not None
    )


def register_token(session: Session, user: User, token: str, platform: str) -> PushToken:
    """Store ``token`` for ``user`` (reactivate it, or move it from another user).

    A phone that reinstalled the app gets a new user but can keep the same Expo token, so a
    token already stored for another user is moved to this one.

    Args:
        session: Open session (committed here).
        user: Owner (already checked against ``X-Device-Id``).
        token: Valid token (``valid_token``).
        platform: ``"ios"`` or ``"android"``.

    Returns:
        The stored row.

    Raises:
        ValueError: On an invalid token or platform.
    """
    if not valid_token(token):
        raise ValueError("invalid Expo push token")
    if platform not in TOKEN_PLATFORMS:
        raise ValueError("invalid platform")
    row = session.scalars(select(PushToken).where(PushToken.token == token)).first()
    if row is None:
        row = PushToken(user_id=user.id, token=token, platform=platform)
        session.add(row)
    else:
        if row.user_id != user.id:
            log.info("push token #%d moved to user %d", row.id, user.id)
        row.user_id, row.platform, row.active, row.last_seen_at = user.id, platform, True, utc_now()
    session.commit()
    log.info("user %d push token #%d registered (%s)", user.id, row.id, platform)
    return row


@lru_cache(maxsize=1)
def _province_table() -> dict[str, tuple[float, float]]:
    """Thai province name -> capital (lat, lon), from the app's ``provinces.json``."""
    rows = json.loads(APP_JSON.read_text(encoding="utf-8"))["provinces"]
    return {r["name_th"]: (float(r["lat"]), float(r["lon"])) for r in rows}


def province_coords(name: str | None) -> tuple[float, float] | None:
    """Capital coordinates of a Thai province name, or None (unknown or missing).

    There is deliberately no default place: a user without a known province gets no push.

    Args:
        name: Thai province name as sent by the app (e.g. ``"ปทุมธานี"``).

    Returns:
        ``(lat, lon)`` or None.
    """
    if not name:
        return None
    return _province_table().get(name.strip())


def current_hour(pred: pd.DataFrame, now: datetime) -> HourNow:
    """``alert_uvi`` and daylight of the hour that contains ``now``.

    Args:
        pred: Output of ``inference.predict_hours``.
        now: Aware datetime.

    Returns:
        ``HourNow``.

    Raises:
        inference.NoCurrentHourError: If that hour is missing.
    """
    from src.inference import current_index

    row = pred.iloc[current_index(pred, now)]
    return HourNow(alert_uvi=float(row["alert_uvi"]), is_daylight=bool(row["is_day"]))


def _local_date(t: datetime) -> Any:
    """Calendar date in Asia/Bangkok."""
    return t.astimezone(LOCAL_TZ).date()


def decide(
    alert_threshold: float,
    safe_threshold: float,
    hour: HourNow,
    sent: Iterable[tuple[str, datetime]],
    now: datetime,
) -> str | None:
    """Which push to send to one user now: ``"high_uv"``, ``"safe_again"`` or None.

    Args:
        alert_threshold: The user's alert UVI (from the database, never a shared default).
        safe_threshold: The user's "safe again" UVI (``alert_threshold - 2``).
        hour: Current hour of the user's province.
        sent: ``(type, sent_at)`` of the user's notifications with ``status == "sent"``
            (errors must not be passed: they do not count for state or cooldown).
        now: Aware current time.

    Returns:
        The notification type, or None (night, no change, or cooldown).
    """
    if not hour.is_daylight:
        return None  # quiet at night; the state below restarts every day
    sent = [(t, at) for t, at in sent if t in PUSH_TYPES]
    today = [(t, at) for t, at in sent if _local_date(at) == _local_date(now)]
    alerting = bool(today) and max(today, key=lambda x: x[1])[0] == "high_uv"
    if not alerting and reaches_alert(hour.alert_uvi, alert_threshold):
        kind = "high_uv"
    elif alerting and is_safe_again(hour.alert_uvi, safe_threshold):
        kind = "safe_again"
    else:
        return None
    if any(t == kind and now - at < COOLDOWN for t, at in sent):
        return None
    return kind


def build_message(
    kind: str, alert_uvi: float, province: str, skin_type: str, safe_threshold: float
) -> tuple[str, str]:
    """Thai title and body of a push; both say "ประมาณ" (the values are estimates).

    Args:
        kind: ``"high_uv"`` or ``"safe_again"``.
        alert_uvi: Upper UVI of the current hour.
        province: Thai province name.
        skin_type: Fitzpatrick type I-VI.
        safe_threshold: The user's "safe again" UVI.

    Returns:
        ``(title, body)``.
    """
    r = int(round_uvi(alert_uvi))
    level = WHO_LEVELS[int(who_level(alert_uvi))]
    if kind == "high_uv":
        mins = burn_minutes(alert_uvi, skin_type)
        burn = f" ผิวประเภท {skin_type} อาจไหม้ในประมาณ {mins} นาที" if mins else ""
        return (
            f"UV สูง ประมาณ {r} ({level})",
            f"จ.{province}: UV ตอนนี้ประมาณ {r} ระดับ{level}{burn} "
            "ทาครีมกันแดด สวมหมวก และหลบแดดถ้าทำได้",
        )
    return (
        "UV ลดลงแล้ว (ประมาณ)",
        f"จ.{province}: UV ตอนนี้ประมาณ {r} ต่ำกว่า {safe_threshold:g} แล้ว "
        "ถ้าจะอยู่กลางแจ้งนาน ยังควรป้องกันแดด",
    )


def chunked(items: list[Any], size: int) -> list[list[Any]]:
    """Split a list into consecutive chunks of at most ``size`` items.

    Args:
        items: Items.
        size: Chunk size (>= 1).

    Returns:
        List of chunks.
    """
    if size < 1:
        raise ValueError("size must be >= 1")
    return [items[i : i + size] for i in range(0, len(items), size)]


def ticket_error(ticket: dict[str, Any]) -> str | None:
    """Error text of an Expo ticket or receipt (None when ``status == "ok"``), token-free.

    Args:
        ticket: ``{"status": "ok" | "error", "message"?, "details"?: {"error"?}}``.

    Returns:
        ``"<details.error>: <message>"`` scrubbed of tokens, or None.
    """
    if ticket.get("status") == "ok":
        return None
    code = (ticket.get("details") or {}).get("error") or "error"
    return scrub(f"{code}: {ticket.get('message') or ''}".strip())[:500]


def _not_registered(ticket: dict[str, Any]) -> bool:
    """Whether a ticket/receipt says the device is no longer registered."""
    return (ticket.get("details") or {}).get("error") == NOT_REGISTERED


class ExpoPushSender:
    """Expo Push Service client with retries and backoff (``EXPO_ACCESS_TOKEN`` optional)."""

    def __init__(
        self,
        access_token: str | None = None,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Create a sender.

        Args:
            access_token: Expo access token (enhanced push security), or None.
            session: HTTP session (tests).
            sleep: Sleep function (tests).
        """
        self.session = session or requests.Session()
        self.sleep = sleep
        self.headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if access_token:
            self.headers["Authorization"] = f"Bearer {access_token}"

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> ExpoPushSender:
        """Sender using ``EXPO_ACCESS_TOKEN`` from the process environment (or ``env``).

        Args:
            env: Mapping to read instead of ``os.environ`` (tests).

        Returns:
            ``ExpoPushSender``.
        """
        env = dict(os.environ) if env is None else env
        return cls(access_token=(env.get("EXPO_ACCESS_TOKEN") or "").strip() or None)

    def _post(self, url: str, payload: Any) -> dict[str, Any]:
        """POST JSON with ``POST_RETRIES`` retries on connection errors and ``RETRY_STATUS``.

        Raises:
            requests.RequestException: The last error (other HTTP errors are not retried).
        """
        last: requests.RequestException | None = None
        for attempt in range(POST_RETRIES + 1):
            try:
                resp = self.session.post(
                    url, json=payload, headers=self.headers, timeout=POST_TIMEOUT_S
                )
                if resp.status_code not in RETRY_STATUS:
                    resp.raise_for_status()
                    return resp.json()
                last = requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last = exc
            if attempt < POST_RETRIES:
                self.sleep(POST_BACKOFF_S * 2**attempt)
        assert last is not None
        raise last

    def send(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Send one batch (<= ``BATCH_SIZE``); one ticket per message.

        Raises:
            ValueError: More than ``BATCH_SIZE`` messages or a malformed response.
            requests.RequestException: Network / HTTP failure after the retries.
        """
        if len(messages) > BATCH_SIZE:
            raise ValueError(f"at most {BATCH_SIZE} messages per request")
        data = self._post(EXPO_PUSH_URL, messages).get("data")
        if not isinstance(data, list) or len(data) != len(messages):
            raise ValueError("unexpected Expo push response")
        return data

    def receipts(self, ids: list[str]) -> dict[str, dict[str, Any]]:
        """Receipts for up to ``RECEIPT_BATCH`` ticket ids."""
        if not ids:
            return {}
        return self._post(EXPO_RECEIPTS_URL, {"ids": ids[:RECEIPT_BATCH]}).get("data") or {}


class DryRunSender:
    """Prints the messages (without tokens) and returns "ok" tickets; sends nothing."""

    def __init__(self) -> None:
        """Start with no printed messages."""
        self.sent: list[dict[str, Any]] = []

    def send(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Print each message's title and body."""
        for m in messages:
            self.sent.append(m)
            print(f"[dry-run] {m['title']} | {m['body']}")
        return [{"status": "ok"} for _ in messages]

    def receipts(self, ids: list[str]) -> dict[str, dict[str, Any]]:
        """No receipts in a dry run."""
        return {}


def check_receipts(session: Session, sender: PushSender, now: datetime) -> int:
    """Deactivate tokens whose recent receipts say ``DeviceNotRegistered``.

    Looks at sent logs from ``RECEIPT_WINDOW`` ago (checking a receipt twice is harmless).

    Args:
        session: Open session (not committed here).
        sender: Push sender.
        now: Aware current time.

    Returns:
        Number of tokens deactivated.
    """
    lo, hi = now - RECEIPT_WINDOW[1], now - RECEIPT_WINDOW[0]
    logs = session.scalars(
        select(NotificationLog).where(
            NotificationLog.status == "sent",
            NotificationLog.expo_ticket_id.is_not(None),
            NotificationLog.sent_at >= lo,
            NotificationLog.sent_at <= hi,
        )
    ).all()
    if not logs:
        return 0
    by_id = {x.expo_ticket_id: x for x in logs}
    n = 0
    for ids in chunked(list(by_id), RECEIPT_BATCH):
        for tid, receipt in sender.receipts(ids).items():
            entry = by_id.get(tid)
            if entry is None or not _not_registered(receipt):
                continue
            entry.error = f"receipt: {ticket_error(receipt)}"
            token = session.get(PushToken, entry.push_token_id) if entry.push_token_id else None
            if token is not None and token.active:
                token.active = False
                n += 1
                log.info("push token #%d deactivated (receipt %s)", token.id, NOT_REGISTERED)
    return n


def _sent_history(session: Session, user_id: int, now: datetime) -> list[tuple[str, datetime]]:
    """``(type, sent_at)`` of a user's successfully sent pushes in the last 24 h."""
    rows = session.execute(
        select(NotificationLog.type, NotificationLog.sent_at).where(
            NotificationLog.user_id == user_id,
            NotificationLog.status == "sent",
            NotificationLog.type.in_(PUSH_TYPES),
            NotificationLog.sent_at >= now - timedelta(hours=24),
        )
    ).all()
    return [(t, at) for t, at in rows]


def _advisory_lock(session: Session) -> bool:
    """Take the PostgreSQL transaction-level advisory lock (always True on SQLite).

    ``pg_try_advisory_xact_lock`` is released by the round's own commit or rollback, so it can
    never stay behind on a pooled connection.
    """
    if session.get_bind().dialect.name != "postgresql":
        return True
    return bool(
        session.execute(
            text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": ADVISORY_LOCK_KEY}
        ).scalar()
    )


def run_tick(
    session: Session,
    predict_fn: PredictFn,
    sender: PushSender,
    now: datetime | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """One scheduler round: decide, send and log the pushes for every eligible user.

    Only one round runs at a time (a thread lock in this process and a PostgreSQL advisory
    lock across processes); a round that cannot get the lock is skipped.

    Args:
        session: Open session.
        predict_fn: ``(lat, lon) -> predict_hours`` output for one place.
        sender: Push sender (``ExpoPushSender`` or a fake).
        now: Aware current time (default ``utc_now()``).
        commit: Commit the logs and token changes (False = dry run, rolled back).

    Returns:
        Counts: ``users``, ``provinces``, ``skipped_no_province``, ``forecast_errors``,
        ``sent``, ``errors``, ``deactivated``; ``skipped: True`` if another round was running.
    """
    if not _tick_lock.acquire(blocking=False):
        log.info("push tick skipped: another tick is running")
        return {"skipped": True}
    try:
        if not _advisory_lock(session):
            session.rollback()
            log.info("push tick skipped: another process holds the lock")
            return {"skipped": True}
        stats = _tick(session, predict_fn, sender, now or utc_now())
        session.commit() if commit else session.rollback()  # also releases the advisory lock
        return stats
    except Exception:
        session.rollback()
        raise
    finally:
        _tick_lock.release()


def _tick(
    session: Session, predict_fn: PredictFn, sender: PushSender, now: datetime
) -> dict[str, Any]:
    """Body of ``run_tick`` (lock already held, no commit)."""
    stats = dict.fromkeys(
        ("users", "provinces", "skipped_no_province", "forecast_errors", "sent", "errors"), 0
    )
    stats["skipped"] = False
    try:
        stats["deactivated"] = check_receipts(session, sender, now)
    except Exception as exc:  # receipts are best effort; never stop the round
        log.warning("push receipts not checked: %s", exc.__class__.__name__)
        stats["deactivated"] = 0

    rows = session.execute(
        select(User, PushToken)
        .join(PushToken, PushToken.user_id == User.id)
        .where(User.notify_enabled.is_(True), PushToken.active.is_(True))
        .order_by(User.id, PushToken.id)
    ).all()
    tokens: dict[int, list[PushToken]] = defaultdict(list)
    people: dict[int, User] = {}
    for user, token in rows:
        people[user.id] = user
        tokens[user.id].append(token)
    stats["users"] = len(people)

    by_province: dict[str, list[User]] = defaultdict(list)
    for user in people.values():
        if province_coords(user.province) is None:
            stats["skipped_no_province"] += 1
            log.info("user %d skipped: no known province", user.id)
            continue
        by_province[user.province.strip()].append(user)

    outbox: list[tuple[User, PushToken, str, float, str, str]] = []
    for province, members in by_province.items():
        stats["provinces"] += 1
        lat, lon = province_coords(province)
        try:
            hour = current_hour(predict_fn(lat, lon), now)
        except Exception as exc:  # Open-Meteo down, missing hour...: skip this province only
            stats["forecast_errors"] += 1
            log.warning("forecast for %s failed: %s", province, exc.__class__.__name__)
            continue
        for user in members:
            kind = decide(
                user.alert_threshold,
                user.safe_threshold,
                hour,
                _sent_history(session, user.id, now),
                now,
            )
            if kind is None:
                continue
            title, body = build_message(
                kind, hour.alert_uvi, province, user.skin_type, user.safe_threshold
            )
            outbox.extend((user, t, kind, hour.alert_uvi, title, body) for t in tokens[user.id])

    for chunk in chunked(outbox, BATCH_SIZE):
        messages = [
            {
                "to": token.token,
                "title": title,
                "body": body,
                "sound": "default",
                "priority": "high",
                "channelId": CHANNEL_ID,
                "data": {"kind": APP_KIND[kind], "source": "server"},
            }
            for _, token, kind, _, title, body in chunk
        ]
        try:
            tickets = sender.send(messages)
        except Exception as exc:  # network / HTTP / malformed answer: log, keep tokens
            log.warning("expo push request failed: %s", exc.__class__.__name__)
            tickets = [
                {"status": "error", "message": exc.__class__.__name__, "details": {"error": "send"}}
            ] * len(chunk)
        for (user, token, kind, uvi, title, body), ticket in zip(chunk, tickets):
            err = ticket_error(ticket)
            session.add(
                NotificationLog(
                    user_id=user.id,
                    push_token_id=token.id,
                    type=kind,
                    sent_at=now,
                    uvi=round(uvi, 2),
                    title=title,
                    body=body,
                    status="sent" if err is None else "error",
                    expo_ticket_id=(ticket.get("id") if err is None else None),
                    error=err,
                )
            )
            if err is None:
                stats["sent"] += 1
                log.info("push %s sent to user %d (token #%d)", kind, user.id, token.id)
            else:
                stats["errors"] += 1
                log.warning("push %s to user %d (token #%d) failed", kind, user.id, token.id)
            if _not_registered(ticket) and token.active:
                token.active = False
                stats["deactivated"] += 1
                log.info("push token #%d deactivated (%s)", token.id, NOT_REGISTERED)
    return stats


def scheduler_enabled(env: dict[str, str] | None = None) -> bool:
    """Whether the push scheduler should run (``PUSH_SCHEDULER``, default on).

    Args:
        env: Mapping to read instead of ``os.environ`` (tests).

    Returns:
        False for ``0``, ``off``, ``false`` or ``no``.
    """
    env = dict(os.environ) if env is None else env
    return (env.get("PUSH_SCHEDULER") or "on").strip().lower() not in OFF_VALUES


def bundle_predictor(bundle: Any) -> PredictFn:
    """``predict_fn`` for ``run_tick`` that uses the API's loaded models.

    Args:
        bundle: ``inference.ModelBundle``.

    Returns:
        ``(lat, lon) -> predict_hours`` output (Open-Meteo cached 10 min per place).
    """
    from src import inference as inf

    def predict(lat: float, lon: float) -> pd.DataFrame:
        """Fetch Open-Meteo and predict every hour for one place."""
        return inf.predict_hours(inf.build_features(inf.fetch_live(lat, lon), lat, lon), bundle)

    return predict


def scheduled_tick(engine: Engine, bundle: Any, sender: PushSender | None = None) -> None:
    """Job run by the scheduler; logs and swallows every error so the scheduler keeps going.

    Args:
        engine: Database engine.
        bundle: Loaded models.
        sender: Push sender (default ``ExpoPushSender.from_env()``).
    """
    try:
        with make_session_factory(engine)() as session:
            stats = run_tick(session, bundle_predictor(bundle), sender or ExpoPushSender.from_env())
        log.info("push tick: %s", stats)
    except Exception:
        log.exception("push tick failed")


def start_scheduler(engine: Engine, bundle: Any, env: dict[str, str] | None = None) -> Any | None:
    """Start the ``TICK_MINUTES`` background job, unless ``PUSH_SCHEDULER`` is off.

    One job, ``max_instances=1`` and ``coalesce=True``: a slow round is never run twice at
    the same time and missed rounds are merged into one.

    Args:
        engine: Database engine.
        bundle: Loaded models.
        env: Mapping to read instead of ``os.environ`` (tests).

    Returns:
        The running ``BackgroundScheduler``, or None when disabled.
    """
    if not scheduler_enabled(env):
        log.info("push scheduler disabled (PUSH_SCHEDULER=off)")
        return None
    from apscheduler.schedulers.background import BackgroundScheduler

    sched = BackgroundScheduler(timezone="UTC")
    sched.add_job(
        scheduled_tick,
        "interval",
        minutes=TICK_MINUTES,
        args=[engine, bundle],
        id="push_tick",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
        replace_existing=True,
    )
    sched.start()
    log.info("push scheduler started (every %d min)", TICK_MINUTES)
    return sched


def main(argv: list[str] | None = None) -> dict[str, Any]:
    """CLI: ``--once`` runs one round now; ``--dry-run`` prints instead of sending.

    Args:
        argv: Arguments (default ``sys.argv``).

    Returns:
        The round's counts.
    """
    from src import db
    from src import inference as inf

    p = argparse.ArgumentParser(description="UV Guard push notifications (one round)")
    p.add_argument("--once", action="store_true", required=True, help="run one round now")
    p.add_argument("--dry-run", action="store_true", help="print messages, send and store none")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    engine = db.make_engine()
    sender: PushSender = DryRunSender() if args.dry_run else ExpoPushSender.from_env()
    with db.make_session_factory(engine)() as session:
        stats = run_tick(
            session,
            bundle_predictor(inf.ModelBundle.load()),
            sender,
            commit=not args.dry_run,
        )
    print(stats)
    return stats


if __name__ == "__main__":
    main()
