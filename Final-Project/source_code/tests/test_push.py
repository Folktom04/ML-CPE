"""Tests for src.push and ``PUT /users/{id}/push-token`` (day 23).

No network: forecasts come from a fake predictor and pushes go to ``FakeSender``. Every
database test runs on SQLite and, when ``TEST_DATABASE_URL`` is set, on that PostgreSQL test
database too (same rule as ``test_users.py``).
"""

import logging
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest
import requests
from api import main
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import make_url
from src import db, push
from src.db import NotificationLog, PushToken, User
from src.push import HourNow
from tests.test_db import BACKENDS, PG_URL, _drop_everything
from tests.test_inference import fake_bundle

NOW = datetime(2026, 9, 28, 5, 10, tzinfo=timezone.utc)  # 12:10 in Bangkok
TOKEN = "ExponentPushToken[abcdefghijklmnopqrstuv]"
DEV = "3f2c9a1e-7b4d-4e8a-9c21-5d6f0b8a4e17"
OTHER = "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"


@pytest.fixture(params=BACKENDS)
def engine(request, tmp_path):
    if request.param == "sqlite":
        url = f"sqlite:///{(tmp_path / 'push.sqlite').as_posix()}"
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


class FakeSender:
    """Records every batch; ``mode`` = "ok", "not_registered" or "raise"."""

    def __init__(self, mode="ok", receipts=None):
        self.mode, self.batches, self.receipt_map, self.receipt_calls = mode, [], receipts, []

    def send(self, messages):
        self.batches.append(messages)
        if self.mode == "raise":
            raise requests.ConnectionError("network down")
        if self.mode == "not_registered":
            return [
                {
                    "status": "error",
                    "message": f'"{m["to"]}" is not a registered push notification recipient',
                    "details": {"error": "DeviceNotRegistered"},
                }
                for m in messages
            ]
        n = sum(len(b) for b in self.batches)
        return [{"status": "ok", "id": f"ticket-{n}-{i}"} for i in range(len(messages))]

    def receipts(self, ids):
        self.receipt_calls.append(ids)
        return {i: self.receipt_map[i] for i in ids if self.receipt_map and i in self.receipt_map}

    @property
    def messages(self):
        return [m for b in self.batches for m in b]


def pred_df(alert_uvi=9.0, is_day=True):
    """predict_hours-like rows; the 06:00 UTC row is the hour that contains NOW."""
    t = pd.date_range("2026-09-28 03:00", periods=6, freq="h", tz="UTC")
    return pd.DataFrame({"time_utc": t, "alert_uvi": alert_uvi, "is_day": is_day})


class Predictor:
    """Counts calls per place; ``values`` maps (lat, lon) -> alert_uvi or an exception."""

    def __init__(self, alert_uvi=9.0, is_day=True, values=None):
        self.alert_uvi, self.is_day, self.values, self.calls = alert_uvi, is_day, values or {}, []

    def __call__(self, lat, lon):
        self.calls.append((lat, lon))
        v = self.values.get((lat, lon), self.alert_uvi)
        if isinstance(v, Exception):
            raise v
        return pred_df(v, self.is_day)


def add_user(
    session,
    n,
    province="ปทุมธานี",
    alert=8.0,
    token=True,
    active=True,
    notify=True,
    skin="III",
):
    u = User(
        device_id=f"device-{n:04d}-xxxxxxxxxxxx",
        skin_type=skin,
        province=province,
        notify_enabled=notify,
        alert_threshold=alert,
        safe_threshold=alert - 2,
    )
    session.add(u)
    session.flush()
    if token:
        session.add(
            PushToken(
                user_id=u.id,
                token=f"ExponentPushToken[user{n:04d}xxxxxxxxxxxx]",
                platform="android",
                active=active,
            )
        )
    session.commit()
    return u


def logs(session, user_id=None):
    q = select(NotificationLog).order_by(NotificationLog.id)
    if user_id is not None:
        q = q.where(NotificationLog.user_id == user_id)
    return session.scalars(q).all()


# --- decide ----------------------------------------------------------------------------------


@pytest.mark.parametrize("uvi,expected", [(7.49, None), (7.5, "high_uv"), (7.8, "high_uv")])
def test_alert_uses_who_rounding(uvi, expected):
    assert push.decide(8, 6, HourNow(uvi, True), [], NOW) == expected


def test_quiet_at_night_even_when_extreme():
    assert push.decide(8, 6, HourNow(12.0, False), [], NOW) is None
    alerting = [("high_uv", NOW - timedelta(hours=1))]
    assert push.decide(8, 6, HourNow(0.0, False), alerting, NOW) is None


def test_cooldown_three_hours_per_type():
    recent = [
        ("high_uv", NOW - timedelta(hours=2, minutes=59)),
        ("safe_again", NOW - timedelta(hours=2)),
    ]
    assert push.decide(8, 6, HourNow(9, True), recent, NOW) is None
    old = [("high_uv", NOW - timedelta(hours=3)), ("safe_again", NOW - timedelta(hours=2))]
    assert push.decide(8, 6, HourNow(9, True), old, NOW) == "high_uv"


def test_hysteresis_safe_again_only_after_todays_alert():
    assert push.decide(8, 6, HourNow(1.0, True), [], NOW) is None
    alerting = [("high_uv", NOW - timedelta(hours=1))]
    assert push.decide(8, 6, HourNow(5.49, True), alerting, NOW) == "safe_again"
    assert push.decide(8, 6, HourNow(5.5, True), alerting, NOW) is None  # rounds to 6
    assert push.decide(8, 6, HourNow(7.0, True), alerting, NOW) is None  # between: no change
    assert push.decide(8, 6, HourNow(9.0, True), alerting, NOW) is None  # already alerting


def test_state_resets_each_day():
    yesterday = [("high_uv", NOW - timedelta(hours=20))]  # 16:10 yesterday in Bangkok
    assert push.decide(8, 6, HourNow(1.0, True), yesterday, NOW) is None  # no safe_again
    assert push.decide(8, 6, HourNow(9.0, True), yesterday, NOW) == "high_uv"


def test_each_users_own_threshold():
    h = HourNow(6.8, True)
    assert push.decide(6, 4, h, [], NOW) == "high_uv"
    assert push.decide(8, 6, h, [], NOW) is None
    assert push.decide(11, 9, h, [], NOW) is None


@pytest.mark.parametrize("kind", ["high_uv", "safe_again"])
def test_messages_say_estimate(kind):
    title, body = push.build_message(kind, 9.2 if kind == "high_uv" else 3.0, "ปทุมธานี", "III", 6)
    assert "ประมาณ" in title and "ประมาณ" in body and "จ.ปทุมธานี" in body


# --- helpers ---------------------------------------------------------------------------------


def test_token_format_and_mask():
    assert push.valid_token(TOKEN)
    for bad in (
        None,
        123,
        "",
        "ExpoPushToken[abc]",
        "ExponentPushToken[]",
        "ExponentPushToken[a b]",
        "ExponentPushToken[abc]x",
        "ExponentPushToken[" + "a" * 237 + "]",
    ):
        assert not push.valid_token(bad), bad
    assert len("ExponentPushToken[" + "a" * 236 + "]") == 255
    assert push.valid_token("ExponentPushToken[" + "a" * 236 + "]")
    assert push.mask_token(TOKEN) == f"<push token, {len(TOKEN)} chars>"
    assert "abcdef" not in push.scrub(f'"{TOKEN}" is not registered')


def test_province_coords_no_default():
    assert push.province_coords("ปทุมธานี") == pytest.approx((14.02, 100.52), abs=0.05)
    assert push.province_coords(None) is None
    assert push.province_coords("") is None
    assert push.province_coords("Tokyo") is None


def test_chunked():
    assert push.chunked(list(range(5)), 2) == [[0, 1], [2, 3], [4]]
    assert push.chunked([], 100) == []
    with pytest.raises(ValueError):
        push.chunked([1], 0)


@pytest.mark.parametrize(
    "env,on",
    [
        ({}, True),
        ({"PUSH_SCHEDULER": "on"}, True),
        ({"PUSH_SCHEDULER": "off"}, False),
        ({"PUSH_SCHEDULER": "0"}, False),
        ({"PUSH_SCHEDULER": "False"}, False),
    ],
)
def test_scheduler_enabled(env, on):
    assert push.scheduler_enabled(env) is on


def test_start_scheduler_off_returns_none_and_on_runs_one_job():
    assert push.start_scheduler(None, None, env={"PUSH_SCHEDULER": "off"}) is None
    sched = push.start_scheduler(None, None, env={})
    try:
        (job,) = sched.get_jobs()
        assert sched.running and job.max_instances == 1 and job.coalesce
        assert job.trigger.interval == timedelta(minutes=push.TICK_MINUTES)
    finally:
        sched.shutdown(wait=False)


def test_scheduled_tick_never_raises(caplog):
    class Boom:
        pass

    push.scheduled_tick(Boom(), fake_bundle(), sender=FakeSender())  # not an engine
    assert "push tick failed" in caplog.text


# --- ExpoPushSender ---------------------------------------------------------------------------


class FakeResp:
    def __init__(self, status, data=None):
        self.status_code, self._data = status, data or {}

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


class FakeHttp:
    def __init__(self, answers):
        self.answers, self.calls = list(answers), []

    def post(self, url, json, headers, timeout):
        self.calls.append((url, json, headers))
        a = self.answers.pop(0)
        if isinstance(a, Exception):
            raise a
        return a


def msgs(n):
    return [{"to": TOKEN, "title": "t", "body": "b"} for _ in range(n)]


def test_sender_retries_503_then_succeeds():
    ok = FakeResp(200, {"data": [{"status": "ok", "id": "x"}]})
    http = FakeHttp([FakeResp(503), requests.ConnectionError(), ok])
    sleeps = []
    tickets = push.ExpoPushSender(session=http, sleep=sleeps.append).send(msgs(1))
    assert tickets == [{"status": "ok", "id": "x"}] and len(http.calls) == 3
    assert sleeps == [0.5, 1.0] and http.calls[0][0] == push.EXPO_PUSH_URL


def test_sender_gives_up_after_retries_and_does_not_retry_400():
    http = FakeHttp([requests.Timeout()] * 3)
    with pytest.raises(requests.Timeout):
        push.ExpoPushSender(session=http, sleep=lambda s: None).send(msgs(1))
    http = FakeHttp([FakeResp(400)])
    with pytest.raises(requests.HTTPError):
        push.ExpoPushSender(session=http, sleep=lambda s: None).send(msgs(1))
    assert len(http.calls) == 1


def test_sender_checks_batch_size_response_and_auth_header():
    s = push.ExpoPushSender(session=FakeHttp([]))
    with pytest.raises(ValueError):
        s.send(msgs(101))
    http = FakeHttp([FakeResp(200, {"data": []})])
    with pytest.raises(ValueError):
        push.ExpoPushSender(session=http).send(msgs(1))
    assert "Authorization" not in push.ExpoPushSender.from_env({}).headers
    s = push.ExpoPushSender.from_env({"EXPO_ACCESS_TOKEN": "secret"})
    assert s.headers["Authorization"] == "Bearer secret"


# --- run_tick --------------------------------------------------------------------------------


def test_run_tick_sends_logs_and_respects_cooldown(session):
    u = add_user(session, 1)
    sender = FakeSender()
    stats = push.run_tick(session, Predictor(9.0), sender, NOW)
    assert (stats["sent"], stats["errors"], stats["users"]) == (1, 0, 1)
    (m,) = sender.messages
    assert m["to"] == f"ExponentPushToken[user0001xxxxxxxxxxxx]" and m["channelId"] == "uv-alerts"
    assert m["data"] == {"kind": "uv_high", "source": "server"} and "ประมาณ" in m["body"]
    (entry,) = logs(session, u.id)
    assert (entry.type, entry.status, entry.uvi, entry.error) == ("high_uv", "sent", 9.0, None)
    assert entry.expo_ticket_id and entry.push_token_id and entry.title == m["title"]
    assert TOKEN not in entry.body and "ExponentPushToken" not in entry.body
    # 30 min later: still high, already alerting -> nothing; later UV drops -> safe_again
    assert push.run_tick(session, Predictor(9.0), sender, NOW + timedelta(minutes=30))["sent"] == 0
    later = NOW + timedelta(hours=1)
    assert push.run_tick(session, Predictor(3.0), sender, later)["sent"] == 1
    assert [x.type for x in logs(session, u.id)] == ["high_uv", "safe_again"]


def test_run_tick_skips_ineligible_users(session):
    add_user(session, 1, token=False)
    add_user(session, 2, active=False)
    add_user(session, 3, notify=False)
    add_user(session, 4, province=None)
    add_user(session, 5, province="Tokyo")
    ok = add_user(session, 6)
    sender = FakeSender()
    stats = push.run_tick(session, Predictor(9.0), sender, NOW)
    assert stats["sent"] == 1 and stats["skipped_no_province"] == 2
    assert [e.user_id for e in logs(session)] == [ok.id]


def test_province_null_not_sent_and_no_default_place(session):
    add_user(session, 1, province=None)
    pred, sender = Predictor(12.0), FakeSender()
    push.run_tick(session, pred, sender, NOW)
    assert pred.calls == [] and sender.batches == [] and logs(session) == []


def test_forecast_fetched_once_per_province(session):
    for n in range(3):
        add_user(session, n, province="ปทุมธานี")
    add_user(session, 9, province="เชียงใหม่")
    pred = Predictor(9.0)
    stats = push.run_tick(session, pred, FakeSender(), NOW)
    assert len(pred.calls) == 2 and len(set(pred.calls)) == 2
    assert stats["provinces"] == 2 and stats["sent"] == 4


def test_night_tick_sends_nothing(session):
    add_user(session, 1)
    sender = FakeSender()
    assert push.run_tick(session, Predictor(12.0, is_day=False), sender, NOW)["sent"] == 0
    assert sender.batches == []


def test_one_province_failing_does_not_stop_others(session):
    add_user(session, 1, province="ปทุมธานี")
    ok = add_user(session, 2, province="เชียงใหม่")
    bad = push.province_coords("ปทุมธานี")
    pred = Predictor(9.0, values={bad: requests.ConnectionError("open-meteo down")})
    stats = push.run_tick(session, pred, FakeSender(), NOW)
    assert stats["forecast_errors"] == 1 and stats["sent"] == 1
    assert [e.user_id for e in logs(session)] == [ok.id]


def test_network_error_logged_token_kept_and_retried_next_tick(session):
    u = add_user(session, 1)
    stats = push.run_tick(session, Predictor(9.0), FakeSender("raise"), NOW)
    assert (stats["sent"], stats["errors"]) == (0, 1)
    (entry,) = logs(session, u.id)
    assert entry.status == "error" and "ConnectionError" in entry.error
    assert session.scalars(select(PushToken)).one().active
    # errors do not count for the cooldown: the next tick sends
    assert (
        push.run_tick(session, Predictor(9.0), FakeSender(), NOW + timedelta(minutes=30))["sent"]
        == 1
    )


def test_device_not_registered_ticket_deactivates_token(session):
    u = add_user(session, 1)
    stats = push.run_tick(session, Predictor(9.0), FakeSender("not_registered"), NOW)
    assert stats["deactivated"] == 1 and stats["errors"] == 1
    (entry,) = logs(session, u.id)
    assert entry.status == "error" and entry.error.startswith("DeviceNotRegistered")
    assert "ExponentPushToken[" not in entry.error  # Expo's message quotes the token: scrubbed
    assert not session.scalars(select(PushToken)).one().active
    sender = FakeSender()
    push.run_tick(session, Predictor(9.0), sender, NOW + timedelta(minutes=30))
    assert sender.batches == []  # inactive token: nothing sent any more


def test_device_not_registered_receipt_deactivates_token(session):
    u = add_user(session, 1)
    push.run_tick(session, Predictor(9.0), FakeSender(), NOW)
    tid = logs(session, u.id)[0].expo_ticket_id
    receipt = {"status": "error", "message": "gone", "details": {"error": "DeviceNotRegistered"}}
    sender = FakeSender(receipts={tid: receipt})
    stats = push.run_tick(session, Predictor(9.0), sender, NOW + timedelta(minutes=30))
    assert sender.receipt_calls == [[tid]] and stats["deactivated"] == 1
    assert not session.scalars(select(PushToken)).one().active
    assert logs(session, u.id)[0].error.startswith("receipt: DeviceNotRegistered")


def test_batches_of_at_most_batch_size(session, monkeypatch):
    monkeypatch.setattr(push, "BATCH_SIZE", 2)
    for n in range(5):
        add_user(session, n)
    sender = FakeSender()
    assert push.run_tick(session, Predictor(9.0), sender, NOW)["sent"] == 5
    assert [len(b) for b in sender.batches] == [2, 2, 1]


def test_concurrent_tick_is_skipped(session):
    add_user(session, 1)
    sender = FakeSender()
    assert push._tick_lock.acquire(blocking=False)
    try:
        assert push.run_tick(session, Predictor(9.0), sender, NOW) == {"skipped": True}
    finally:
        push._tick_lock.release()
    assert sender.batches == []


def test_dry_run_writes_nothing(session, capsys):
    add_user(session, 1)
    stats = push.run_tick(session, Predictor(9.0), push.DryRunSender(), NOW, commit=False)
    assert stats["sent"] == 1 and "[dry-run]" in capsys.readouterr().out
    assert logs(session) == []


def test_deleting_user_cascades_tokens_and_logs(session):
    u = add_user(session, 1)
    push.run_tick(session, Predictor(9.0), FakeSender(), NOW)
    assert db.delete_user(session, u.id)
    assert session.scalars(select(PushToken)).all() == [] and logs(session) == []


def test_logs_never_hold_token_or_device_id(session, caplog):
    caplog.set_level(logging.INFO, logger="uvguard.push")
    u = add_user(session, 1)
    push.register_token(session, u, TOKEN, "ios")
    push.run_tick(session, Predictor(9.0), FakeSender(), NOW)
    push.run_tick(session, Predictor(9.0), FakeSender("not_registered"), NOW + timedelta(hours=4))
    assert "sent to user" in caplog.text
    assert "PushToken[" not in caplog.text and u.device_id not in caplog.text


# --- register_token + API --------------------------------------------------------------------


def test_register_token_moves_between_users(session):
    a, b = add_user(session, 1, token=False), add_user(session, 2, token=False)
    row = push.register_token(session, a, TOKEN, "android")
    row.active = False
    session.commit()
    row2 = push.register_token(session, b, TOKEN, "ios")
    assert row2.id == row.id and (row2.user_id, row2.platform, row2.active) == (b.id, "ios", True)
    with pytest.raises(ValueError):
        push.register_token(session, a, "nope", "android")
    with pytest.raises(ValueError):
        push.register_token(session, a, TOKEN, "web")


@pytest.fixture
def client(engine):
    main.app.state.bundle = fake_bundle()
    main.app.state.db_engine = engine
    main.app.state.db_fallback = False
    with TestClient(main.app) as c:
        yield c


def new_user(client, device=DEV):
    r = client.post(
        "/users", json={"skin_type": "III", "province": "ปทุมธานี"}, headers={"X-Device-Id": device}
    )
    assert r.status_code == 201
    return r.json()["id"]


def put_token(client, uid, body, device=DEV):
    return client.put(f"/users/{uid}/push-token", json=body, headers={"X-Device-Id": device})


def test_push_token_endpoint_ok_without_echo(client, engine):
    uid = new_user(client)
    r = put_token(client, uid, {"token": TOKEN, "platform": "android"})
    assert r.status_code == 200
    body = r.json()
    assert (body["registered"], body["platform"], body["active"]) == (True, "android", True)
    assert TOKEN not in r.text and DEV not in r.text
    with db.make_session_factory(engine)() as s:
        (row,) = s.scalars(select(PushToken)).all()
        assert (row.user_id, row.token) == (uid, TOKEN)
    assert put_token(client, uid, {"token": TOKEN, "platform": "android"}).status_code == 200


def test_push_token_endpoint_404_403(client):
    uid = new_user(client)
    body = {"token": TOKEN, "platform": "android"}
    assert put_token(client, 999, body).status_code == 404
    assert put_token(client, uid, body, device=OTHER).status_code == 403
    r = client.put(f"/users/{uid}/push-token", json=body)  # header missing
    assert r.status_code == 403


@pytest.mark.parametrize(
    "body",
    [
        {"token": "ExpoPushToken[abcdefgh]", "platform": "android"},
        {"token": "ExponentPushToken[" + "a" * 237 + "]", "platform": "android"},  # 256 chars
        {"token": "ExponentPushToken[abc def]", "platform": "android"},
        {"token": TOKEN, "platform": "web"},
        {"token": TOKEN},  # missing platform: the validation error must not echo the token
        {"token": TOKEN, "platform": "android", "extra": 1},
    ],
)
def test_push_token_endpoint_422_never_echoes_token(client, body):
    uid = new_user(client)
    r = put_token(client, uid, body)
    assert r.status_code == 422
    assert "PushToken[" not in r.text and "a" * 50 not in r.text


def test_push_token_moves_to_new_user_and_delete_cascades(client, engine):
    first = new_user(client, DEV)
    assert put_token(client, first, {"token": TOKEN, "platform": "android"}).status_code == 200
    second = new_user(client, OTHER)
    r = put_token(client, second, {"token": TOKEN, "platform": "android"}, device=OTHER)
    assert r.status_code == 200
    with db.make_session_factory(engine)() as s:
        assert s.scalars(select(PushToken.user_id)).all() == [second]
    assert client.delete(f"/users/{second}", headers={"X-Device-Id": OTHER}).status_code == 204
    with db.make_session_factory(engine)() as s:
        assert s.scalars(select(PushToken)).all() == []


def test_health_reports_push_scheduler(engine, monkeypatch):
    main.app.state.bundle = fake_bundle()
    main.app.state.db_engine = engine
    with TestClient(main.app) as c:  # conftest: PUSH_SCHEDULER=off
        assert c.get("/health").json()["push_scheduler"] is False
    monkeypatch.setenv("PUSH_SCHEDULER", "on")
    with TestClient(main.app) as c:
        assert c.get("/health").json()["push_scheduler"] is True
    assert main.app.state.push_scheduler is None  # stopped at shutdown
