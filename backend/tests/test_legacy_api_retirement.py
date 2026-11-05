"""F01: retired routes stop before credentials, SQL, storage or providers."""
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.api_v1.api import api_router
from app.api.openapi.api import router as integration_router
from app.core.http_privacy import install_http_privacy
from app.core.security import get_api_key_user, get_current_user
from app.db.session import get_db
from app.models.api_key import APIKey
from app.services.api_key import APIKeyService
from tests.test_phase2_authorization import world


ROUTES = [
    ("GET", "/api/api-keys/"),
    ("POST", "/api/api-keys/"),
    ("PUT", "/api/api-keys/1"),
    ("DELETE", "/api/api-keys/1"),
    ("GET", "/openapi/knowledge/1/query?query=synthetic"),
]


@pytest.mark.parametrize("method,path", ROUTES)
@pytest.mark.parametrize("credential", [None, "synthetic-retired-key"])
def test_retired_endpoints_never_resolve_credentials_or_database(method, path, credential, monkeypatch):
    app = FastAPI()
    install_http_privacy(app)
    app.include_router(api_router, prefix="/api")
    app.include_router(integration_router, prefix="/openapi")
    touched = []

    def forbidden_dependency():
        touched.append(True)
        raise AssertionError("Retired routes must reject before auth or database access")

    app.dependency_overrides[get_db] = forbidden_dependency
    app.dependency_overrides[get_current_user] = forbidden_dependency
    lookup = MagicMock(side_effect=AssertionError("No legacy credential lookup"))
    monkeypatch.setattr(APIKeyService, "get_api_key_by_key", lookup)
    headers = {"X-API-Key": credential, "Authorization": "Bearer synthetic"} if credential else {}
    with TestClient(app) as client:
        response = client.request(method, path, headers=headers, json={"name": "synthetic"})
    assert response.status_code == 410
    assert response.headers["cache-control"] == "no-store"
    assert "Personal AI keys remain available in Profile" in response.json()["detail"]
    assert "synthetic-retired-key" not in response.text
    assert not touched
    lookup.assert_not_called()


def test_retired_auth_dependency_itself_fails_closed():
    with pytest.raises(HTTPException) as error:
        get_api_key_user()
    assert error.value.status_code == 410


def test_valid_stored_keys_cannot_read_or_mutate_and_records_survive(world):
    w = world
    before = [(r.id, r.key, r.name, r.is_active, r.last_used_at) for r in w.db.query(APIKey).order_by(APIKey.id)]
    for method, path in ROUTES:
        response = w.client.request(method, path, json={"name": "changed"},
                                    headers={**w.headers(w.alice), "X-API-Key": "phase2-alice"})
        assert response.status_code == 410
        assert all(row[1] not in response.text for row in before)
    w.db.expire_all()
    assert [(r.id, r.key, r.name, r.is_active, r.last_used_at) for r in w.db.query(APIKey).order_by(APIKey.id)] == before


def test_api_docs_hide_retired_surfaces_but_keep_personal_ai_settings(world):
    paths = world.app.openapi()["paths"]
    assert not any(path.startswith(("/api/api-keys", "/openapi/knowledge")) for path in paths)
    assert "/api/ai-settings" in paths
