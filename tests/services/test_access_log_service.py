# tests/services/test_access_log_service.py
import pytest
from datetime import datetime, timezone
import uuid
from services.access_log_service import AccessLogService
from repositories.access_log_repo import AccessLogRepository


class MockUser:
    def __init__(self, id, first_name, last_name, image_ref):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.image_ref = image_ref


class MockDevice:
    def __init__(self, id_device, location):
        self.id_device = id_device
        self.location = location


class MockLog:
    def __init__(self, id, access_user_id, device_id, event, timestamp, user=None, device=None):
        self.id = id
        self.access_user_id = access_user_id
        self.device_id = device_id
        self.event = event
        self.timestamp = timestamp
        self.access_user = user
        self.device = device


class MockAccessLogRepository:
    def __init__(self, logs=None):
        self.logs = logs or []
    
    def get_logs_with_filters(self, user_id=None, device_id=None, limit=100):
        filtered = self.logs
        
        if user_id is not None:
            filtered = [log for log in filtered if log.access_user_id == user_id]
        
        if device_id is not None:
            filtered = [log for log in filtered if log.device_id == device_id]
        
        return filtered[:limit]
    
    def count_by_filters(self, user_id=None, device_id=None):
        filtered = self.logs
        
        if user_id is not None:
            filtered = [log for log in filtered if log.access_user_id == user_id]
        
        if device_id is not None:
            filtered = [log for log in filtered if log.device_id == device_id]
        
        return len(filtered)


@pytest.fixture
def mock_logs():
    """Datos de prueba"""
    user1 = MockUser(66, "Santiago", "Lozano", "https://bucket.s3.amazonaws.com/user1.jpg")
    user2 = MockUser(67, "María", "García", "https://bucket.s3.amazonaws.com/user2.jpg")
    
    device1 = MockDevice("1", "raspberry-tic2")
    device2 = MockDevice("2", "raspberry-lab1")
    
    return [
        MockLog(
            uuid.uuid4(),
            66,
            "1",
            "accepted",
            datetime(2024, 1, 10, 12, 0, 0, tzinfo=timezone.utc),
            user1,
            device1
        ),
        MockLog(
            uuid.uuid4(),
            66,
            "2",
            "denied",
            datetime(2024, 1, 9, 10, 0, 0, tzinfo=timezone.utc),
            user1,
            device2
        ),
        MockLog(
            uuid.uuid4(),
            67,
            "1",
            "accepted",
            datetime(2024, 1, 8, 15, 30, 0, tzinfo=timezone.utc),
            user2,
            device1
        ),
        MockLog(
            uuid.uuid4(),
            None,  # Usuario no reconocido
            "1",
            "denied",
            datetime(2024, 1, 7, 9, 0, 0, tzinfo=timezone.utc),
            None,  # Sin datos de usuario
            device1
        )
    ]


def test_format_log():
    """Test formateo de log"""
    repo = MockAccessLogRepository([])
    service = AccessLogService(repo)
    
    user = MockUser(1, "Test", "User", "https://bucket.s3.amazonaws.com/test.jpg")
    device = MockDevice("test-1", "test-location")
    log = MockLog(
        uuid.uuid4(),
        1,
        "test-1",
        "accepted",
        datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        user,
        device
    )
    
    result = service._format_log(log)
    
    assert isinstance(result['id'], str)
    assert result['access_user_id'] == 1
    assert result['user']['first_name'] == "Test"
    assert result['device_id'] == "test-1"
    assert result['device_location'] == "test-location"
    assert result['event'] == "accepted"
    assert "2024-01-01T10:00:00" in result['timestamp']


def test_format_log_null_user():
    """Test formateo de log con usuario no reconocido (null)"""
    repo = MockAccessLogRepository([])
    service = AccessLogService(repo)
    
    device = MockDevice("test-1", "test-location")
    log = MockLog(
        uuid.uuid4(),
        None,  # access_user_id null
        "test-1",
        "denied",
        datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        None,  # Sin usuario
        device
    )
    
    result = service._format_log(log)
    
    assert result['access_user_id'] is None
    assert result['user'] is not None  # Siempre debe incluir objeto user
    assert result['user']['first_name'] is None
    assert result['user']['last_name'] is None
    assert result['user']['image_ref'] is None
    assert result['device_location'] == "test-location"
    assert result['event'] == "denied"


def test_get_logs_no_filters(mock_logs):
    """Test obtener logs sin filtros"""
    repo = MockAccessLogRepository(mock_logs)
    service = AccessLogService(repo)
    
    results = service.get_logs()
    
    assert len(results) == 4  # Incluyendo usuario no reconocido
    assert all('id' in log for log in results)
    assert all('user' in log for log in results)
    assert all('device_location' in log for log in results)
    
    # Verificar el log con usuario no reconocido
    null_user_log = next(log for log in results if log['access_user_id'] is None)
    assert null_user_log['user']['first_name'] is None
    assert null_user_log['user']['last_name'] is None
    assert null_user_log['user']['image_ref'] is None
    assert null_user_log['event'] == 'denied'


def test_get_logs_filter_by_user(mock_logs):
    """Test filtrar logs por usuario"""
    repo = MockAccessLogRepository(mock_logs)
    service = AccessLogService(repo)
    
    results = service.get_logs(user_id="66")
    
    assert len(results) == 2
    assert all(log['access_user_id'] == 66 for log in results)
    assert all(log['user']['first_name'] == "Santiago" for log in results)


def test_get_logs_filter_by_device(mock_logs):
    """Test filtrar logs por dispositivo"""
    repo = MockAccessLogRepository(mock_logs)
    service = AccessLogService(repo)
    
    results = service.get_logs(device_id="1")
    
    assert len(results) == 3
    assert all(log['device_id'] == "1" for log in results)
    assert all(log['device_location'] == "raspberry-tic2" for log in results)


def test_get_logs_multiple_filters(mock_logs):
    """Test filtrar logs por múltiples criterios"""
    repo = MockAccessLogRepository(mock_logs)
    service = AccessLogService(repo)
    
    results = service.get_logs(user_id="66", device_id="1")
    
    assert len(results) == 1
    assert results[0]['access_user_id'] == 66
    assert results[0]['device_id'] == "1"


def test_get_logs_invalid_user_id():
    """Test con user_id inválido"""
    repo = MockAccessLogRepository([])
    service = AccessLogService(repo)
    
    with pytest.raises(ValueError, match="user_id debe ser un número válido"):
        service.get_logs(user_id="abc")


def test_get_logs_count(mock_logs):
    """Test contar logs"""
    repo = MockAccessLogRepository(mock_logs)
    service = AccessLogService(repo)
    
    # Sin filtros
    count = service.get_logs_count()
    assert count == 4
    
    # Con filtro de usuario
    count = service.get_logs_count(user_id="66")
    assert count == 2
    
    # Con múltiples filtros
    count = service.get_logs_count(user_id="66", device_id="1")
    assert count == 1