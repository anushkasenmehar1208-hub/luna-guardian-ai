import pytest

from app import core


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "DATABASE_URL", "")
    monkeypatch.setattr(core, "DB_PATH", str(tmp_path / "luna-test.db"))
    yield
