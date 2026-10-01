"""Shared pytest guard: no test may touch the main database.

``tests/test_db.py`` loads ``.env`` at import (for ``TEST_DATABASE_URL``), which also puts the
main ``DATABASE_URL`` into the environment for the whole session, and ``db.database_url()`` loads
``.env`` again on every call. So removing the variable is not enough: every engine created through
``src.db`` is checked, and a PostgreSQL URL whose database name does not contain "test" fails the
test at once (SQLite is always allowed).
"""

from typing import Any

import pytest
from sqlalchemy.engine import make_url
from src import db

_real_create_engine = db.create_engine


def assert_test_database(url: Any) -> None:
    """Raise unless ``url`` is SQLite or a database whose name contains "test".

    Args:
        url: SQLAlchemy URL (string or ``URL``).
    """
    u = make_url(url)
    if u.get_backend_name() == "sqlite":
        return
    if "test" not in (u.database or "").lower():
        raise RuntimeError(
            f"tests may only use a *test* database, got {u.get_backend_name()} "
            f"database {u.database!r}"
        )


@pytest.fixture(autouse=True)
def never_main_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drop ``DATABASE_URL``, turn the push scheduler off and guard every ``src.db`` engine."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("PUSH_SCHEDULER", "off")  # day 23: no background push job in tests

    def guarded(url: Any, *args: Any, **kwargs: Any) -> Any:
        """``create_engine`` that refuses non-test PostgreSQL databases."""
        assert_test_database(url)
        return _real_create_engine(url, *args, **kwargs)

    monkeypatch.setattr(db, "create_engine", guarded)
