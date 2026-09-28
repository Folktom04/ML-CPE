"""The conftest guard: tests can never create an engine for the main (non-test) database."""

import os

import pytest
from src import db
from tests.conftest import assert_test_database


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://u:p@localhost:5432/uvguard",
        "postgresql+psycopg://u:p@localhost:5432/production",
        "postgresql+psycopg://u:p@localhost:5432",  # no database name
    ],
)
def test_main_database_is_refused(url):
    with pytest.raises(RuntimeError, match="only use a \*test\* database"):
        db.make_engine(url)


def test_test_databases_and_sqlite_are_allowed():
    assert_test_database("postgresql+psycopg://u:p@localhost:5432/uvguard_test")
    assert_test_database("sqlite://")
    db.make_engine("sqlite://").dispose()


def test_database_url_from_env_is_removed_and_default_engine_guarded(monkeypatch):
    assert "DATABASE_URL" not in os.environ  # removed for every test by the autouse fixture
    # even if something (e.g. load_dotenv) puts the main URL back, make_engine() refuses it
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/uvguard")
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    with pytest.raises(RuntimeError):
        db.make_engine()
