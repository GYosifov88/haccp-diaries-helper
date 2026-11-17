import pytest

from haccp.config import get_settings


@pytest.fixture(autouse=True)
def isolated_pending_db(tmp_path, monkeypatch):
    """Keep tests off the real ./data/haccp.db so pending entries never leak between tests."""
    monkeypatch.setattr(get_settings(), "sqlite_path", str(tmp_path / "haccp.db"))
