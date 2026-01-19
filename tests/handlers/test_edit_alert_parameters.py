# tests/handlers/test_edit_alert_parameters.py
import json
import pytest
from unittest.mock import patch, MagicMock
import os

# Configurar variables de entorno antes de importar
os.environ["JWT_SECRET"] = "test_secret"

import handlers.edit_alert_parameters as handler_module
from services.configuration_service import ConfigurationService


def make_event(body=None):
    """Helper para crear eventos de prueba"""
    event = {}
    if body is not None:
        event['body'] = json.dumps(body) if isinstance(body, dict) else body
    return event


@pytest.fixture
def mock_db():
    """Mock para la conexión de base de datos"""
    with patch.object(handler_module.db, 'is_closed', return_value=False):
        with patch.object(handler_module.db, 'connect'):
            with patch.object(handler_module.db, 'close'):
                yield


def test_update_alert_parameters_success(mock_db, monkeypatch):
    """Test actualización exitosa"""
    mock_service = MagicMock()
    mock_service.update_alert_parameters.return_value = {
        "message": "Alert parameters updated successfully.",
        "updated": {
            "max_denied_attempts": 10,
            "window_seconds": 300
        }
    }
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    body = {
        "max_denied_attempts": 10,
        "window_seconds": 300
    }
    event = make_event(body)
    
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 200
    body_resp = json.loads(response['body'])
    assert body_resp['message'] == "Alert parameters updated successfully."
    
    mock_service.update_alert_parameters.assert_called_once_with(10, 300)


def test_update_alert_parameters_invalid_json(mock_db):
    """Test con JSON inválido"""
    event = make_event("invalid json {")
    
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['error'] == "Invalid JSON in request body"


def test_update_alert_parameters_missing_field(mock_db, monkeypatch):
    """Test con campo faltante"""
    mock_service = MagicMock()
    mock_service.update_alert_parameters.side_effect = ValueError(
        "Both max_denied_attempts and window_seconds are required."
    )
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    body = {"max_denied_attempts": 10}  # Falta window_seconds
    event = make_event(body)
    
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 400
    body_resp = json.loads(response['body'])
    assert "required" in body_resp['error']


def test_update_alert_parameters_invalid_value(mock_db, monkeypatch):
    """Test con valores inválidos"""
    mock_service = MagicMock()
    mock_service.update_alert_parameters.side_effect = ValueError(
        "max_denied_attempts must be at least 1"
    )
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    body = {
        "max_denied_attempts": 0,
        "window_seconds": 300
    }
    event = make_event(body)
    
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 400
    body_resp = json.loads(response['body'])
    assert "must be at least 1" in body_resp['error']


def test_update_alert_parameters_config_not_found(mock_db, monkeypatch):
    """Test cuando las configuraciones no existen"""
    mock_service = MagicMock()
    mock_service.update_alert_parameters.side_effect = LookupError(
        "No configurations were found to update"
    )
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    body = {
        "max_denied_attempts": 10,
        "window_seconds": 300
    }
    event = make_event(body)
    
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 404
    body_resp = json.loads(response['body'])
    assert "No configurations were found" in body_resp['error']


def test_update_alert_parameters_internal_error(mock_db, monkeypatch):
    """Test error interno del servidor"""
    mock_service = MagicMock()
    mock_service.update_alert_parameters.side_effect = Exception("Database error")
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    body = {
        "max_denied_attempts": 10,
        "window_seconds": 300
    }
    event = make_event(body)
    
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 500
    body_resp = json.loads(response['body'])
    assert "Database error" in body_resp['error']


def test_update_alert_parameters_empty_body(mock_db, monkeypatch):
    """Test con body vacío"""
    mock_service = MagicMock()
    mock_service.update_alert_parameters.side_effect = ValueError(
        "Both max_denied_attempts and window_seconds are required."
    )
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    event = make_event({})
    
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 400


def test_update_alert_parameters_string_numbers(mock_db, monkeypatch):
    """Test con números como strings"""
    mock_service = MagicMock()
    mock_service.update_alert_parameters.return_value = {
        "message": "Alert parameters updated successfully.",
        "updated": {
            "max_denied_attempts": 15,
            "window_seconds": 600
        }
    }
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    body = {
        "max_denied_attempts": "15",
        "window_seconds": "600"
    }
    event = make_event(body)
    
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 200
    
    # El servicio debe recibir los valores tal como vienen
    mock_service.update_alert_parameters.assert_called_once_with("15", "600")


def test_update_alert_parameters_extreme_values(mock_db, monkeypatch):
    """Test con valores extremos pero válidos"""
    mock_service = MagicMock()
    mock_service.update_alert_parameters.return_value = {
        "message": "Alert parameters updated successfully.",
        "updated": {
            "max_denied_attempts": 1000,
            "window_seconds": 86400
        }
    }
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    body = {
        "max_denied_attempts": 1000,  # Máximo permitido
        "window_seconds": 86400       # 24 horas
    }
    event = make_event(body)
    
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 200
    body_resp = json.loads(response['body'])
    assert body_resp['message'] == "Alert parameters updated successfully."