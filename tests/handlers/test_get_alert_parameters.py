# tests/handlers/test_get_alert_parameters.py
import json
import pytest
from unittest.mock import patch, MagicMock
import os

# Configurar variables de entorno antes de importar
os.environ["JWT_SECRET"] = "test_secret"

import handlers.get_alert_parameters as handler_module
from services.configuration_service import ConfigurationService


def make_event(query_params=None):
    """Helper para crear eventos de prueba"""
    event = {}
    if query_params:
        event['queryStringParameters'] = query_params
    return event


@pytest.fixture
def mock_db():
    """Mock para la conexión de base de datos"""
    with patch.object(handler_module.db, 'is_closed', return_value=False):
        with patch.object(handler_module.db, 'connect'):
            with patch.object(handler_module.db, 'close'):
                yield


def test_get_alert_parameters_success(mock_db, monkeypatch):
    """Test obtener parámetros exitosamente"""
    mock_service = MagicMock()
    mock_service.get_alert_parameters.return_value = {
        'max_denied_attempts': 50,
        'window_seconds': 90
    }
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    event = make_event()
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['max_denied_attempts'] == 50
    assert body['window_seconds'] == 90
    
    mock_service.get_alert_parameters.assert_called_once_with()


def test_get_alert_parameters_null_values(mock_db, monkeypatch):
    """Test cuando algunos valores son null"""
    mock_service = MagicMock()
    mock_service.get_alert_parameters.return_value = {
        'max_denied_attempts': 50,
        'window_seconds': None
    }
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    event = make_event()
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['max_denied_attempts'] == 50
    assert body['window_seconds'] is None


def test_get_alert_parameters_all_null(mock_db, monkeypatch):
    """Test cuando todos los valores son null"""
    mock_service = MagicMock()
    mock_service.get_alert_parameters.return_value = {
        'max_denied_attempts': None,
        'window_seconds': None
    }
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    event = make_event()
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['max_denied_attempts'] is None
    assert body['window_seconds'] is None


def test_get_alert_parameters_internal_error(mock_db, monkeypatch):
    """Test error interno del servidor"""
    mock_service = MagicMock()
    mock_service.get_alert_parameters.side_effect = Exception("Database error")
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    event = make_event()
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 500
    body = json.loads(response['body'])
    assert "Database error" in body['error']


def test_get_alert_parameters_with_future_device_id(mock_db, monkeypatch):
    """Test preparado para futuro uso con device_id (actualmente no usado)"""
    mock_service = MagicMock()
    mock_service.get_alert_parameters.return_value = {
        'max_denied_attempts': 30,
        'window_seconds': 60
    }
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    # En el futuro, podría recibir device_id como query parameter
    event = make_event({'device_id': 'raspberry-1'})
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['max_denied_attempts'] == 30
    
    # Por ahora no se usa device_id
    mock_service.get_alert_parameters.assert_called_once_with()