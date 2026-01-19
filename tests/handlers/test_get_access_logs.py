# tests/handlers/test_get_access_logs.py
import json
import pytest
from unittest.mock import patch, MagicMock
import os

# Configurar variables de entorno antes de importar
os.environ["JWT_SECRET"] = "test_secret"

import handlers.get_access_logs as handler_module
from services.access_log_service import AccessLogService


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


def test_get_logs_no_filters(mock_db, monkeypatch):
    """Test GET /access_logs sin filtros"""
    mock_logs = [
        {
            'id': '1de83408-20d3-4925-a65c-2628269efa95',
            'access_user_id': 66,
            'user': {
                'first_name': 'Santiago',
                'last_name': 'Lozano',
                'image_ref': 'https://bucket.s3.amazonaws.com/user.jpg'
            },
            'device_id': '1',
            'device_location': 'raspberry-tic2',
            'event': 'accepted',
            'timestamp': '2024-01-01T10:00:00+00:00'
        }
    ]
    
    mock_service = MagicMock()
    mock_service.get_logs.return_value = mock_logs
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    event = make_event()
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert len(body) == 1
    assert body[0]['access_user_id'] == 66
    
    mock_service.get_logs.assert_called_once_with(user_id=None, device_id=None)


def test_get_logs_with_filters(mock_db, monkeypatch):
    """Test GET /access_logs con filtros"""
    mock_logs = [
        {
            'id': '1de83408-20d3-4925-a65c-2628269efa95',
            'access_user_id': 66,
            'user': {'first_name': 'Santiago', 'last_name': 'Lozano', 'image_ref': None},
            'device_id': '1',
            'device_location': 'raspberry-tic2',
            'event': 'accepted',
            'timestamp': '2024-01-01T10:00:00+00:00'
        }
    ]
    
    mock_service = MagicMock()
    mock_service.get_logs.return_value = mock_logs
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    event = make_event({'user_id': '66', 'device_id': '1'})
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert len(body) == 1
    
    mock_service.get_logs.assert_called_once_with(user_id='66', device_id='1')


def test_get_logs_empty_result(mock_db, monkeypatch):
    """Test GET /access_logs sin resultados"""
    mock_service = MagicMock()
    mock_service.get_logs.return_value = []
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    event = make_event({'user_id': '999'})
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body == []


def test_get_logs_invalid_user_id(mock_db, monkeypatch):
    """Test GET /access_logs con user_id inválido"""
    mock_service = MagicMock()
    mock_service.get_logs.side_effect = ValueError("user_id debe ser un número válido")
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    event = make_event({'user_id': 'abc'})
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert "user_id debe ser un número válido" in body['error']


def test_get_logs_internal_error(mock_db, monkeypatch):
    """Test error interno del servidor"""
    mock_service = MagicMock()
    mock_service.get_logs.side_effect = Exception("Database error")
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    event = make_event()
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 500
    body = json.loads(response['body'])
    assert "Database error" in body['error']


def test_get_logs_null_query_params(mock_db, monkeypatch):
    """Test con queryStringParameters null"""
    mock_service = MagicMock()
    mock_service.get_logs.return_value = []
    monkeypatch.setattr(handler_module, '_service', mock_service)
    
    event = {'queryStringParameters': None}  # API Gateway puede enviar null
    response = handler_module.lambda_handler(event, None)
    
    assert response['statusCode'] == 200
    mock_service.get_logs.assert_called_once_with(user_id=None, device_id=None)