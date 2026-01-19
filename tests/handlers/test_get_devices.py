# tests/handlers/test_get_devices.py
import json
import pytest
from unittest.mock import patch, MagicMock
import os

# Configurar variables de entorno antes de importar
os.environ["JWT_SECRET"] = "test_secret"

import handlers.get_devices as handler_module
from services.device_service import DeviceService


def make_event(device_id=None):
    """Helper para crear eventos de prueba"""
    event = {}
    if device_id:
        event['pathParameters'] = {'id': device_id}
    return event


@pytest.fixture
def mock_db():
    """Mock para la conexión de base de datos"""
    with patch.object(handler_module.db, 'is_closed', return_value=False):
        with patch.object(handler_module.db, 'connect'):
            with patch.object(handler_module.db, 'close'):
                yield


def test_get_all_devices_success(mock_db, monkeypatch):
    """Test GET /devices exitoso"""
    mock_devices = [
        {'id_device': 1, 'location': 'raspberry-tic2', 'status': 'active', 'last_sync': '2024-01-01 10:00:00'},
        {'id_device': 2, 'location': 'raspberry-lab1', 'status': 'inactive', 'last_sync': None}
    ]
    
    mock_service = MagicMock()
    mock_service.get_all_devices.return_value = mock_devices
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    event = make_event()
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert len(body) == 2
    assert body[0]['location'] == 'raspberry-tic2'
    
    mock_service.get_all_devices.assert_called_once()


def test_get_device_by_id_success(mock_db, monkeypatch):
    """Test GET /devices/{id} exitoso"""
    mock_device = {
        'id_device': 1,
        'location': 'raspberry-tic2',
        'status': 'active',
        'last_sync': '2024-01-01 10:00:00'
    }
    
    mock_service = MagicMock()
    mock_service.get_device_by_id.return_value = mock_device
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    event = make_event('1')
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['id_device'] == 1
    assert body['location'] == 'raspberry-tic2'
    
    mock_service.get_device_by_id.assert_called_once_with('1')


def test_get_device_by_id_invalid_id(mock_db, monkeypatch):
    """Test GET /devices/{id} con ID inválido"""
    mock_service = MagicMock()
    mock_service.get_device_by_id.side_effect = ValueError("ID de dispositivo inválido")
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    event = make_event('abc')
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert "ID de dispositivo inválido" in body['error']


def test_get_device_by_id_not_found(mock_db, monkeypatch):
    """Test GET /devices/{id} dispositivo no encontrado"""
    mock_service = MagicMock()
    mock_service.get_device_by_id.side_effect = LookupError("Dispositivo no encontrado")
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    event = make_event('999')
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 404
    body = json.loads(response['body'])
    assert body['error'] == "Device not found"


def test_internal_server_error(mock_db, monkeypatch):
    """Test error interno del servidor"""
    mock_service = MagicMock()
    mock_service.get_all_devices.side_effect = Exception("Database connection error")
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    event = make_event()
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 500
    body = json.loads(response['body'])
    assert body['error'] == "Internal server error"
    assert "Database connection error" in body['details']


def test_logging_functionality(mock_db, monkeypatch, caplog):
    """Test que los logs funcionan correctamente"""
    mock_service = MagicMock()
    mock_service.get_all_devices.return_value = []
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    event = make_event()
    with caplog.at_level('INFO'):
        response = handler_module.lambda_handler(event, None)
    
    # Verificar que se logueó el evento
    assert "Evento recibido:" in caplog.text
    assert "Obteniendo todos los dispositivos" in caplog.text