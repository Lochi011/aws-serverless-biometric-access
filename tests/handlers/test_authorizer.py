# tests/handlers/test_authorizer.py

import os
import pytest
import handlers.authorizer as auth_module
from services.authorizer_service import AuthorizerService


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    """
    Asegura que, al importar handlers.authorizer, existan las variables de entorno.
    """
    monkeypatch.setenv("JWT_SECRET", "testsecret")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")


def make_event(token_value, route_arn="arn:aws:execute-api:region:acctid:restApiId/stage/GET/resource"):
    """
    Construye un event mínimo que API Gateway envía al custom authorizer.
    """
    return {
        "headers": {"authorization": f"Bearer {token_value}"},
        "routeArn": route_arn
    }


def test_handler_devuelve_true_cuando_token_valido(monkeypatch):
    # 1) Creamos una instancia ficticia de AuthorizerService
    fake_service = AuthorizerService(
        secret="irrelevant", algorithm="irrelevant")
    # 2) Parcheamos el atributo global 'service' del módulo handlers.authorizer
    monkeypatch.setattr(auth_module, "service", fake_service)
    # 3) Hacemos que is_token_valid devuelva True
    monkeypatch.setattr(fake_service, "is_token_valid", lambda t: True)

    event = make_event("token_que_ignora_el_fake")
    response = auth_module.lambda_handler(event, context={})
    assert response == {"isAuthorized": True}


def test_handler_devuelve_false_cuando_token_invalido(monkeypatch):
    fake_service = AuthorizerService(
        secret="irrelevant", algorithm="irrelevant")
    monkeypatch.setattr(auth_module, "service", fake_service)
    monkeypatch.setattr(fake_service, "is_token_valid", lambda t: False)

    event = make_event("token_erroneo")
    response = auth_module.lambda_handler(event, context={})
    assert response == {"isAuthorized": False}


def test_handler_devuelve_false_si_no_hay_header(monkeypatch):
    fake_service = AuthorizerService(
        secret="irrelevant", algorithm="irrelevant")
    monkeypatch.setattr(auth_module, "service", fake_service)
    monkeypatch.setattr(fake_service, "is_token_valid", lambda t: True)

    # 1) Caso sin el header 'authorization'
    event_sin_header = {"headers": {}, "routeArn": "arn:test"}
    resp1 = auth_module.lambda_handler(event_sin_header, context={})
    assert resp1 == {"isAuthorized": False}

    # 2) Caso con header mal formado (no "Bearer <token>")
    event_mal_formato = {"headers": {
        "authorization": "MalFormato abc"}, "routeArn": "arn:test"}
    resp2 = auth_module.lambda_handler(event_mal_formato, context={})
    assert resp2 == {"isAuthorized": False}
