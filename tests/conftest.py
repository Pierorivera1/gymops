"""
pytest configuration and shared fixtures.

All tests use an in-memory SQLite database to avoid touching the
real ~/.gymops/gymops.db file on the developer's machine.
"""

import pytest
from gymops.db import init_db


@pytest.fixture
def db(tmp_path):
    """
    Return a path to a temporary SQLite database for testing.

    Each test function that receives this fixture gets a fresh,
    fully initialized database at a unique temp path.
    """
    db_path = tmp_path / "test_gymops.db"
    init_db(db_path=db_path)
    return db_path
