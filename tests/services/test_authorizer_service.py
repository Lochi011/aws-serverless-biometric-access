# tests/services/test_authorizer_service.py

import pytest
import jwt
from datetime import datetime, timedelta

from services.authorizer_service import AuthorizerService


@pytest.fixture
def secret_and_algo():
    # Definimos un secret y algoritmo fijos para pruebas
    return {"secret": "testsecret", "algorithm": "HS256"}


def generate_token(secret, algorithm, extra_claims=None):
    """
    Genera un JWT válido para pruebas (expira en 1 hora).
    extra_claims puede ser un dict para agregar más campos al payload.
    """
    payload = {
        "sub": "user123",
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, secret, algorithm=algorithm)


def test_is_token_valid_retorna_true_para_token_valido(secret_and_algo):
    svc = AuthorizerService(
        secret=secret_and_algo["secret"],
        algorithm=secret_and_algo["algorithm"]
    )
    token = generate_token(
        secret_and_algo["secret"], secret_and_algo["algorithm"])
    assert svc.is_token_valid(token) is True


def test_is_token_valid_retorna_false_para_token_invalido(secret_and_algo):
    svc = AuthorizerService(
        secret=secret_and_algo["secret"],
        algorithm=secret_and_algo["algorithm"]
    )
    token_malformado = "no.es.un.token.valido"
    assert svc.is_token_valid(token_malformado) is False


def test_is_token_valid_retorna_false_si_secret_no_coincide(secret_and_algo):
    # Generamos un token con un secret diferente al que usa el servicio
    token_con_otro_secret = generate_token("otrosecret", "HS256")

    svc = AuthorizerService(
        secret=secret_and_algo["secret"],  # "testsecret"
        algorithm=secret_and_algo["algorithm"]
    )
    assert svc.is_token_valid(token_con_otro_secret) is False
