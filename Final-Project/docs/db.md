# UV Guard database (day 17)

The schema is defined with SQLAlchemy 2.0 in `source_code/src/db.py`. The Alembic migration is `source_code/migrations/versions/0001_initial_schema.py`, and `alembic.ini` sits in `Final-Project/`.

- **Target: PostgreSQL** (`DATABASE_URL` in `.env`, driver `psycopg` 3).
- **SQLite is a fallback only.** It is used only when `DATABASE_URL` is not set. The API then logs a clear `WARNING ... SQLite FALLBACK`, and `GET /health` reports `db_backend: "sqlite"` and `db_fallback: true`. If PostgreSQL is configured but down, the API does **not** switch to SQLite, because that would split the data. `/health` shows `db_ok: false` instead.
- **All time columns are `DateTime(timezone=True)`** (`timestamptz` on PostgreSQL) through the `UTCDateTime` type. Naive datetimes are rejected. Aware values in any zone are stored as UTC and always read back as **UTC-aware**, on SQLite too. Convert to Asia/Bangkok only for display.

## Tables

```
users 1 ──< push_tokens            (ON DELETE CASCADE)
users 1 ──< measurements           (ON DELETE CASCADE, user_id may be NULL = anonymous call)
users 1 ──< notifications_log      (ON DELETE CASCADE)
push_tokens 1 ──< notifications_log (ON DELETE SET NULL: the log row stays, token link removed)
```

| Table | Columns (main) | Notes |
|---|---|---|
| `users` | `id`, `device_id` (unique), `skin_type` I–VI, `province`, `notify_enabled` (true), `alert_threshold` (8), `safe_threshold` (6), `alert_burn_minutes` (30), `created_at`, `updated_at` | CHECK: skin type I–VI; 1 ≤ alert ≤ 20; 0 ≤ safe < alert (hysteresis 8 / 6); 5 ≤ burn minutes ≤ 240 |
| `push_tokens` | `user_id`, `token` (unique), `platform` ios/android/web, `active`, `created_at`, `last_seen_at` | Expo push token |
| `measurements` | `user_id`, `measured_at`, `lat`, `lon` (rounded to 0.01°), `source` api/phone_lux/sky_image/field, `uvi`, `uvi_lo`, `uvi_hi`, `uva_wm2`, `uvb_wm2`, `cmf`, `interval_adjusted`, `data_imputed`, `lux`, `sky_class`, `sky_confidence` (0–1), `cloud_fraction_rb` (0–1), `openmeteo_uvi`, `model_version`, `created_at` | index `(user_id, measured_at)`, `(source, measured_at)` |
| `notifications_log` | `user_id`, `push_token_id`, `type` high_uv/safe_again/burn_time, `sent_at`, `uvi`, `title`, `body`, `status` sent/error, `expo_ticket_id`, `error` | index `(user_id, type, sent_at)` for the 3-hour cooldown; `(sent_at)` for purging |

`openmeteo_uvi` is stored next to our estimate for the field validation (phone estimate vs Open-Meteo at the same time and place). `interval_adjusted` and `data_imputed` copy the `/predict` flags (day 16).

## Running migrations

From `Final-Project/` (PowerShell):

```powershell
.venv\Scripts\alembic.exe upgrade head     # create / update the schema
.venv\Scripts\alembic.exe current          # -> 0001 (head)
.venv\Scripts\alembic.exe check            # models and migrations agree
.venv\Scripts\alembic.exe upgrade head --sql > docs\schema_postgres.sql   # DDL without a DB
.venv\Scripts\alembic.exe downgrade base   # drop everything (development only)
```

The migration file does not import `src.db` on purpose, so later model changes never rewrite history. A schema change gets a new revision (`alembic revision --autogenerate -m "..."`), and you review it before committing. `test_db.py` checks that the migration and the models match exactly (`compare_metadata`).

## Tests

`source_code/tests/test_db.py` runs every test on a temporary SQLite file. **If `TEST_DATABASE_URL` is set** (in the environment or `.env`), every test also runs on that PostgreSQL database. The database name must contain `test`, because the tests drop and recreate all tables. Without it, the PostgreSQL cases show as *skipped*.

**Tested on a real PostgreSQL 18.6 server (2026-09-27):** `alembic upgrade head` → `0001 (head)`, all 7 time columns are `timestamptz`, and `pytest` gives 221 passed, 0 skipped (the 23 `[postgresql]` cases pass). No behaviour differed from SQLite. The install steps below name version 16; 18 works the same way (service `postgresql-x64-18`, `bin` under `PostgreSQL8`).

## Installing PostgreSQL 16 on Windows (do this by hand)

1. Install PostgreSQL 16 with **one** of these:
   - `winget install --id PostgreSQL.PostgreSQL.16` (PowerShell), or
   - the EDB installer from https://www.enterprisedb.com/downloads/postgres-postgresql-downloads (PostgreSQL 16.x, Windows x86-64).

   In the installer, select *PostgreSQL Server* and *Command Line Tools* (pgAdmin is optional, Stack Builder is not needed). Keep port **5432**, set a password for the `postgres` superuser, and keep the default locale.
2. Check that the service is running: `Get-Service postgresql-x64-16` → `Running`.
3. Add the tools to `PATH` for this session:
   `$env:Path += ";C:\Program Files\PostgreSQL\16\bin"`
4. Create an app role and two databases (you will be asked for the `postgres` password):
   ```powershell
   psql -U postgres -h localhost -c "CREATE ROLE uvguard LOGIN PASSWORD 'choose-a-password';"
   psql -U postgres -h localhost -c "CREATE DATABASE uvguard OWNER uvguard ENCODING 'UTF8';"
   psql -U postgres -h localhost -c "CREATE DATABASE uvguard_test OWNER uvguard ENCODING 'UTF8';"
   ```
5. Put the URLs in `.env` (never commit it). URL-encode special characters in the password (`@` → `%40`, `#` → `%23`):
   ```
   DATABASE_URL=postgresql+psycopg://uvguard:choose-a-password@localhost:5432/uvguard
   TEST_DATABASE_URL=postgresql+psycopg://uvguard:choose-a-password@localhost:5432/uvguard_test
   ```
6. Create the schema: `.venv\Scripts\alembic.exe upgrade head`, then `alembic current` should print `0001 (head)`.
7. Run the tests on PostgreSQL: `.venv\Scripts\python.exe -m pytest -q -rs source_code/tests/test_db.py`. The `[postgresql]` cases must pass and not be skipped.
8. Start the API and open `/health`. It should show `db_backend: "postgresql"`, `db_fallback: false`, `db_ok: true`.

## Privacy and PDPA (พ.ร.บ. คุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562)

**What is stored**
- An anonymous `device_id`: a random ID generated by the app. It is not the IMEI, phone number or advertising ID.
- Fitzpatrick skin type I–VI. This is skin/health-related information, so it is treated like sensitive data (PDPA section 26). It is sent to the server only after **explicit consent**: since day 19 the Settings screen has an opt-in switch (off by default) that states the purpose, which is computing burn time and warnings only. Until then the quiz result and all settings stay on the phone. Turning the switch off withdraws consent and deletes the server record (`DELETE /users/{id}`). Since day 21 the onboarding asks the same question (step 4, same text, also off by default).
- Province (day 21): the Thai name of the province the user picked, or of the provincial capital nearest to the phone's GPS fix. It is sent only with consent (the consent text says so: "ส่งแค่ชื่อจังหวัด ไม่ส่งพิกัด GPS"). **GPS coordinates are never sent to `/users` or stored on the phone**; `/predict` receives them rounded to 0.01° only to compute the UV and does not store them. Notification settings and the Expo push token are stored too.
- Measurements: time, location **rounded to 0.01° (about 1 km)**, the UV estimates and flags, phone lux, and the sky class, confidence and red/blue cloud fraction derived from a photo.
- A log of every notification sent (type, time, UVI, text, delivery status).

**What is NOT stored**
- Name, e-mail, phone number, account passwords.
- Exact GPS coordinates (rounded before writing, `round_coord`).
- **Sky photos**: `/sky-image` processes them in memory only (day 16 test `test_sky_image_result_and_nothing_stored`). Only the derived class and fraction may be stored.
- IP addresses are not stored in the database. For deployment, turn off or rotate the uvicorn access log, because it contains client IPs.

**How long it is kept**

| Data | Retention |
|---|---|
| `measurements` with `source` api / phone_lux / sky_image | **90 days**, then deleted by `purge_old_rows(days=90)` |
| `notifications_log` | **90 days** (needed only for the 3-hour cooldown and debugging) |
| `measurements` with `source='field'` | kept for the project's field validation until the report is submitted. After that, they are deleted or exported without `user_id`/`device_id` for the report. `purge_old_rows` never deletes them by age. |
| `users`, `push_tokens` | until the user deletes their data or the project ends |

`purge_old_rows` is a helper for now. It will be scheduled to run daily with the APScheduler notification job (Phase 5).

**How data is deleted**
- `delete_user(session, user_id)` deletes the user. **The database** (`ON DELETE CASCADE`) then deletes their push tokens, notification log and measurements, including `field` rows. This also works for a plain `DELETE FROM users` (tested with both the ORM and raw SQL). On SQLite this needs `PRAGMA foreign_keys=ON`, which `make_engine` sets.
- **Day 19:** `DELETE /users/{id}` (needs the matching `X-Device-Id`) calls `delete_user`. The app's Settings screen has "ลบข้อมูลของฉัน" with a confirmation step: it deletes the server record first, then clears everything stored on the phone. If the server cannot be reached, the phone data is kept so the user can retry (otherwise the server record could no longer be deleted by anyone). If the server says the user is already gone (404), the phone is cleared. Tested on SQLite and PostgreSQL (`tests/test_users.py`).

**Why `measurements` uses CASCADE, not SET NULL**
A series of (time, ~1 km location) rows from one device is itself personal data, because it shows where a person lives and works, even without a `user_id`. SET NULL would keep that trail after the user asked for deletion, so the rows could still be re-identified and the deletion would be incomplete. The only reason to keep rows would be the field validation. That data is exported for the report without identifiers (see retention), so the database does not need to keep it after a user leaves. Rows that already have `user_id = NULL` (anonymous API calls) are not linked to anyone and are removed by the 90-day purge.

**Security**
- `DATABASE_URL` lives only in `.env` (git-ignored). The app role `uvguard` owns only its own databases, and PostgreSQL listens on `localhost` only.
- **Device id and database errors (day 19).** The engine uses `hide_parameters=True`, so SQLAlchemy errors never show bound values. On a constraint violation, though, **PostgreSQL's own error text names the value**, e.g. `DETAIL: Key (device_id)=(…) already exists` (found by the day-19 PostgreSQL tests; SQLite does not do this). So the API never returns or logs exception text: an `IntegrityError` becomes **409** `"conflict with existing data"`, any other database error becomes **503** `"database unavailable"`, and only the error class is logged (`tests/test_users.py`).
- **PostgreSQL server log.** The database server writes that same `DETAIL` line (with the device id) into its own log, outside the app's control. To keep it out, set in `postgresql.conf` (or `ALTER SYSTEM SET …` then `SELECT pg_reload_conf();`):
  ```
  log_error_verbosity = terse          # drops DETAIL, HINT, QUERY and CONTEXT lines
  log_min_error_statement = panic      # does not log the failing SQL statement either
  ```
  and keep the server log short-lived (rotation, e.g. `log_rotation_age = 1d` with `log_truncate_on_rotation = on`). These are only written down here; the development machine's configuration was not changed.
- UV values are estimates for education and warning, not a medical diagnosis. The API disclaimer is unchanged.
