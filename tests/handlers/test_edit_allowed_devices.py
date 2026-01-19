# tests/handlers/test_edit_allowed_devices.py
import json
import pytest
from unittest.mock import patch, MagicMock
import os

# Configurar variables de entorno antes de importar
os.environ["JWT_SECRET"] = "test_secret"
os.environ["IOT_ENDPOINT"] = "test.iot.amazonaws.com"

import handlers.edit_allowed_devices as handler_module
from services.device_access_service import DeviceAccessService


def make_event(user_id=None, body=None):
    """Helper para crear eventos de prueba"""
    event = {}
    
    if user_id:
        event['pathParameters'] = {'id': user_id}
    
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


def test_update_devices_success(mock_db, monkeypatch):
    """Test actualización exitosa"""
    mock_service = MagicMock()
    mock_service.update_user_device_access.return_value = {
        "message": "User device access updated",
        "added": ["raspberry-tic2"],
        "removed": ["FCEE"]
    }
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    body = {
        "addDevices": ["raspberry-tic2"],
        "removeDevices": ["FCEE"]
    }
    event = make_event('1', body)
    
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 200
    body_resp = json.loads(response['body'])
    assert body_resp['added'] == ["raspberry-tic2"]
    assert body_resp['removed'] == ["FCEE"]
    
    mock_service.update_user_device_access.assert_called_once_with(
        '1',
        ["raspberry-tic2"],
        ["FCEE"]
    )