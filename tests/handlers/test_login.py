# tests/handlers/test_login.py

import json
import pytest

import handlers.login as login_module
from services.auth_service import AuthService


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    """
    Define las vars de entorno antes de importar handlers.login:
    - JWT_SECRET y JWT_ALGORITHM para que no fallen en import.
    - DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT vienen de conftest.py.
    """
    monkeypatch.setenv("JWT_SECRET", "testsecret")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")


def make_event(body_dict):
    """
    Crea el 'event' que Lambda recibe, con body JSON serializado.
    """
    return {"body": json.dumps(body_dict)}


def test_handler_returns_400_if_missing_fields():
    # No parcheamos AuthService.login: falla antes de llamar a login, porque email/password están vacíos.
    event = make_event({"email": "", "password": ""})
    resp = login_module.lambda_handler(event, None)

    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "Email and password are required" in body["error"]


def test_handler_returns_500_if_missing_env(monkeypatch):
    # Eliminamos JWT_SECRET para forzar el error de vars faltantes
    monkeypatch.delenv("JWT_SECRET", raising=False)
    event = make_event({"email": "a@b.com", "password": "pass"})
    resp = login_module.lambda_handler(event, None)

    assert resp["statusCode"] == 500
    body = json.loads(resp["body"])
    assert "Missing environment variables" in body["error"]


def test_handler_returns_401_if_invalid_credentials(monkeypatch):
    # Parcheamos AuthService.login para que lance PermissionError
    monkeypatch.setattr(AuthService, "login", lambda self, e, p: (
        _ for _ in ()).throw(PermissionError("Invalid credentials")))

    event = make_event({"email": "foo@bar.com", "password": "wrong"})
    resp = login_module.lambda_handler(event, None)

    assert resp["statusCode"] == 401
    body = json.loads(resp["body"])
    assert "Invalid credentials" in body["error"]


def test_handler_returns_200_on_success(monkeypatch):
    # Parcheamos AuthService.login para que devuelva token y user_info
    monkeypatch.setattr(AuthService, "login", lambda self, e, p: (
        "mytoken123", {"id": 7, "email": "foo@bar.com", "name": "Foo Bar"}))

    event = make_event({"email": "foo@bar.com", "password": "correct"})
    resp = login_module.lambda_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["message"] == "Login successful"
    assert body["token"] == "mytoken123"
    assert body["user"]["email"] == "foo@bar.com"


def test_handler_returns_500_on_unexpected_error(monkeypatch):
    # Parcheamos AuthService.login para que arroje una excepción genérica
    monkeypatch.setattr(AuthService, "login", lambda self, e, p: (
        _ for _ in ()).throw(Exception("Something went wrong")))

    event = make_event({"email": "foo@bar.com", "password": "pass"})
    resp = login_module.lambda_handler(event, None)

    assert resp["statusCode"] == 500
    body = json.loads(resp["body"])
    assert "Internal error" in body["error"]
