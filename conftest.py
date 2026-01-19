# conftest.py
import boto3
import os
import pytest
from unittest.mock import MagicMock

# ESTO SE EJECUTA al arrancar pytest, antes de importar cualquier handler
os.environ.setdefault("JWT_SECRET", "testsecret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("AWS_IOT_ENDPOINT", "localhost")


@pytest.fixture(autouse=True)
def stub_iot(monkeypatch):
    """Devuelve un mock para boto3.client('iot') e 'iot-data' durante todos los tests."""
    if not hasattr(boto3, "client_orig"):
        boto3.client_orig = boto3.client  # guarda referencia real

    def fake_client(service_name, *args, **kwargs):
        if service_name in ("iot", "iot-data"):
            m = MagicMock(name=f"boto3.{service_name}.mock")
            # Métodos mínimos que usan los tests
            m.subscribe.return_value = {
                "subscriptionArn": "arn:aws:iot:local:test"}
            m.publish.return_value = {}
            return m
        return boto3.client_orig(service_name, *args, **kwargs)

    monkeypatch.setattr(boto3, "client", fake_client)


@pytest.fixture
def mock_db(setup_db):
    """Simple proxy: reutiliza la BD en memoria inicializada por setup_db."""
    return setup_db


@pytest.fixture(autouse=True)
def set_db_env_vars(monkeypatch):
    """
    Fixture que se aplica a todos los tests:
    1) Define las vars de BD para que Peewee use SQLite en memoria.
    2) Define las vars de JWT para que handlers/authorizer.py no falle al importarse.
    """
    monkeypatch.setenv("DB_NAME", ":memory:")
    monkeypatch.setenv("DB_USER", "")
    monkeypatch.setenv("DB_PASSWORD", "")
    monkeypatch.setenv("DB_HOST", "")
    monkeypatch.setenv("DB_PORT", "5432")

    yield
    # No es necesario limpiar: pytest revierte monkeypatch automáticamente.
