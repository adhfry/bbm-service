import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.routers.admin import get_cache


class StubCache:
    def __init__(self, removed: int = 3):
        self._removed = removed
        self.cleared = False

    def clear(self) -> int:
        self.cleared = True
        return self._removed


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _override_settings(token: str = "secret-token"):
    app.dependency_overrides[get_settings] = lambda: Settings(backend_internal_token=token)


def test_cache_clear_rejects_missing_token():
    _override_settings()
    client = TestClient(app)
    response = client.post("/admin/cache/clear")
    assert response.status_code == 401


def test_cache_clear_rejects_wrong_token():
    _override_settings()
    client = TestClient(app)
    response = client.post("/admin/cache/clear", headers={"X-Internal-Token": "wrong"})
    assert response.status_code == 401


def test_cache_clear_succeeds_with_correct_token():
    _override_settings()
    stub = StubCache(removed=5)
    app.dependency_overrides[get_cache] = lambda: stub

    client = TestClient(app)
    response = client.post("/admin/cache/clear", headers={"X-Internal-Token": "secret-token"})

    assert response.status_code == 200
    assert response.json() == {"removed": 5}
    assert stub.cleared is True
