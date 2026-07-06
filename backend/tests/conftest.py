import pytest

from app.database.engine import DB_PATH
from app.database.seed import seed_database


@pytest.fixture(scope="session", autouse=True)
def _ensure_seeded_db():
    """Guarantee the synthetic SQLite DB exists for any DB-backed test."""
    if not DB_PATH.exists():
        seed_database()
    yield
