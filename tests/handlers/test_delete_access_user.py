# tests/handlers/test_delete_access_user.py
from services.access_users_service import AccessUserService
import handlers.delete_access_user as handler_module
import json
import pytest
from unittest.mock import patch, MagicMock
import os

# Configurar variables de entorno antes de importar


def make_event(user_id=None):
    """Helper para crear eventos de prueba"""
    event = {}
    if user_id:
        event['pathParameters'] = {'id': user_id}
    return event


@pytest.fixture
def mock_db():
    """Mock para la conexión de base de datos"""
    with patch.object(handler_module.db, 'is_closed', return_value=False):
        with patch.object(handler_module.db, 'connect'):
            with patch.object(handler_module.db, 'close'):
                yield


def test_delete_user_success(mock_db, monkeypatch):
    """Test DELETE exitoso"""
    mock_service = MagicMock()
    mock_service.delete_user.return_value = {
        "message": "User and image deleted successfully",
        "user_id": "1",
        "raspis_notified": ["RaspberryPi-001"]
    }
    monkeypatch.setattr(handler_module, '_service', mock_service)

    event = make_event('1')
    response = handler_module.lambda_handler(event, None)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['message'] == "User and image deleted successfully"
    assert body['user_id'] == "1"
    assert body['raspis_notified'] == ["RaspberryPi-001"]

    mock_service.delete_user.assert_called_once_with('1')


def test_delete_user_missing_id(mock_db):
    """Test sin ID de usuario"""
    event = make_event()  # Sin ID
    response = handler_module.lambda_handler(event, None)

    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['error'] == "User ID is required"


def test_delete_user_invalid_id(mock_db, monkeypatch):
    """Test con ID inválido"""
    mock_service = MagicMock()
    mock_service.delete_user.side_effect = ValueError("ID de usuario inválido")
    monkeypatch.setattr(handler_module, '_service', mock_service)

    event = make_event('abc')
    response = handler_module.lambda_handler(event, None)

    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert "ID de usuario inválido" in body['error']


def test_delete_user_not_found(mock_db, monkeypatch):
    """Test usuario no encontrado"""
    mock_service = MagicMock()
    mock_service.delete_user.side_effect = LookupError("Usuario no encontrado")
    monkeypatch.setattr(handler_module, '_service', mock_service)

    event = make_event('999')
    response = handler_module.lambda_handler(event, None)

    assert response['statusCode'] == 404
    body = json.loads(response['body'])
    assert body['error'] == "User not found"


def test_delete_user_internal_error(mock_db, monkeypatch):
    """Test error interno"""
    mock_service = MagicMock()
    mock_service.delete_user.side_effect = Exception("Database error")
    monkeypatch.setattr(handler_module, '_service', mock_service)

    event = make_event('1')
    response = handler_module.lambda_handler(event, None)

    assert response['statusCode'] == 500
    body = json.loads(response['body'])
    assert body['error'] == "Internal server error"
    assert "Database error" in body['details']
