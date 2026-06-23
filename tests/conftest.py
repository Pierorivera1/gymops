"""
pytest configuration and shared fixtures.

All tests use an in-memory or temporary SQLite database to avoid touching the
real ~/.gymops/gymops.db file on the developer's machine.
"""

import os
import pytest
from gymops.db import init_db


@pytest.fixture(autouse=True)
def test_db_env(tmp_path, monkeypatch):
    """
    Automatically set GYMOPS_DB_PATH to a temporary database file for each test,
    ensuring that no test (including CLI runner tests) writes to the real database.
    """
    db_path = tmp_path / "test_gymops.db"
    monkeypatch.setenv("GYMOPS_DB_PATH", str(db_path))
    init_db(db_path=db_path)
    return db_path


@pytest.fixture
def db_path(test_db_env):
    """
    Return a path to a temporary SQLite database for testing.

    Each test function that receives this fixture gets a fresh,
    fully initialized database at a unique temp path.
    """
    return test_db_env
