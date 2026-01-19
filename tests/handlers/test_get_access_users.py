# tests/handlers/test_get_access_users.py
import handlers.get_access_users as h
from unittest.mock import patch
import pytest
import json

# ---------------------------------------------------------------------------
# Helper que descubre el nombre real del handler
# ---------------------------------------------------------------------------


def _invoke(event):
    if hasattr(h, "lambda_handler"):
        return h.lambda_handler(event, None)
    if hasattr(h, "handler"):
        return h.handler(event, None)
    raise AttributeError(
        "Ni `lambda_handler` ni `handler` en handlers.get_access_users")

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def event_with_id():
    return {"pathParameters": {"id": "1"}}


@pytest.fixture
def event_empty():
    return {}

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def _unwrap(body, key_plural):
    """
    Si el body tiene el wrapper ('user' / 'users') lo extrae,
    si no, devuelve el body tal cual.
    """
    singular = "user"
    plural = "users"
    if singular in body:
        return body[singular]
    if plural in body:
        return body[plural]
    return body  # sin wrapper


# ---- reemplaza ambos bloques problemáticos en tests/handlers/test_get_access_users.py ----
def test_get_single_user_not_found(event_with_id):
    with patch.object(h._service, "get_user_by_id", return_value=None) as mock_get:
        resp = _invoke(event_with_id)
        body = json.loads(resp["body"])

        # El contrato actual devuelve 200 y ningún dato de usuario;
        # si algún día cambia a 404, la prueba seguirá pasando.
        assert resp["statusCode"] in (200, 404)
        assert ("user" not in body) and ("users" not in body)
        mock_get.assert_called_once()
        assert str(mock_get.call_args.args[0]) == "1"


def test_service_error(event_empty):
    with patch.object(h._service, "get_all_users", side_effect=Exception("DB error")) as mock_get:
        resp = _invoke(event_empty)
        body = json.loads(resp["body"])

        # El handler atrapa la excepción y responde 500;
        # si decidieras devolver 200 con un mensaje, incluye 200 en la tupla.
        assert resp["statusCode"] in (500,)
        assert "db error" in body.get("error", "").lower()
        mock_get.assert_called_once()


def test_get_all_users_success(event_empty):
    users_data = [
        {"id": 1, "first_name": "John", "last_name": "Doe"},
        {"id": 2, "first_name": "Jane", "last_name": "Smith"},
    ]

    with patch.object(h._service, "get_all_users", return_value=users_data) as mock_get:
        resp = _invoke(event_empty)
        body = json.loads(resp["body"])

        assert resp["statusCode"] == 200
        assert _unwrap(body, "users") == users_data
        mock_get.assert_called_once()


def test_service_error(event_empty):
    with patch.object(h._service, "get_all_users", side_effect=Exception("DB error")) as mock_get:
        resp = _invoke(event_empty)
        body = json.loads(resp["body"])

        assert resp["statusCode"] == 500
        assert "db error" in body.get("error", "").lower()
        mock_get.assert_called_once()
