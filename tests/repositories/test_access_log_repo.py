# tests/repositories/test_access_log_repo.py
import pytest
from datetime import datetime, timezone
import uuid
from shared.models import db, AccessLog, AccessUser, Device
from repositories.access_log_repo import AccessLogRepository


@pytest.fixture
def setup_db():
    """Crea las tablas necesarias para los tests"""
    db.connect()
    db.create_tables([AccessUser, Device, AccessLog])
    yield
    db.drop_tables([AccessUser, Device, AccessLog])
    db.close()


@pytest.fixture
def sample_data(setup_db):
    """Crea datos de prueba"""
    # Crear usuarios
    user1 = AccessUser.create(
        id=66,
        first_name="Santiago",
        last_name="Lozano",
        cedula="12345678",
        image_ref="https://tic2-bucket-caras.s3.amazonaws.com/access_users/user1.jpg"
    )
    user2 = AccessUser.create(
        id=67,
        first_name="María",
        last_name="García",
        cedula="87654321",
        image_ref="https://tic2-bucket-caras.s3.amazonaws.com/access_users/user2.jpg"
    )
    
    # Crear dispositivos
    device1 = Device.create(id_device="1", location="raspberry-tic2", status="active")
    device2 = Device.create(id_device="2", location="raspberry-lab1", status="active")
    
    # Crear logs
    now = datetime.now(timezone.utc)
    log1 = AccessLog.create(
        id=uuid.uuid4(),
        access_user_id=user1.id,
        device_id=device1.id_device,
        event="accepted",
        timestamp=now
    )
    log2 = AccessLog.create(
        id=uuid.uuid4(),
        access_user_id=user1.id,
        device_id=device2.id_device,
        event="denied",
        timestamp=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    )
    log3 = AccessLog.create(
        id=uuid.uuid4(),
        access_user_id=user2.id,
        device_id=device1.id_device,
        event="accepted",
        timestamp=datetime(2024, 1, 2, 15, 30, 0, tzinfo=timezone.utc)
    )
    # Log de usuario no reconocido
    log4 = AccessLog.create(
        id=uuid.uuid4(),
        access_user_id=None,  # Usuario no reconocido
        device_id=device1.id_device,
        event="denied",
        timestamp=datetime(2024, 1, 3, 9, 0, 0, tzinfo=timezone.utc)
    )
    
    return {
        'users': [user1, user2],
        'devices': [device1, device2],
        'logs': [log1, log2, log3, log4]
    }


def test_create_log(setup_db):
    """Test crear nuevo log"""
    # Crear usuario y dispositivo primero
    user = AccessUser.create(id=1, first_name="Test", last_name="User", cedula="11111111")
    device = Device.create(id_device="test-1", location="test-device")
    
    repo = AccessLogRepository()
    
    log = repo.create(
        access_user_id=user.id,
        device_id=device.id_device,
        event="accepted",
        timestamp=datetime.now(timezone.utc)
    )
    
    assert log.id is not None
    assert log.access_user_id == user.id
    assert log.device_id == device.id_device
    assert log.event == "accepted"


def test_get_logs_no_filters(sample_data):
    """Test obtener todos los logs sin filtros"""
    repo = AccessLogRepository()
    
    logs = repo.get_logs_with_filters()
    
    assert len(logs) == 4  # Incluyendo el log sin usuario
    # Verificar que vienen ordenados por timestamp DESC
    assert logs[0].event == "accepted"  # El más reciente
    assert logs[3].event == "denied"    # El más antiguo (usuario no reconocido)


def test_get_logs_filter_by_user(sample_data):
    """Test filtrar logs por usuario"""
    repo = AccessLogRepository()
    
    logs = repo.get_logs_with_filters(user_id=66)
    
    assert len(logs) == 2
    for log in logs:
        assert log.access_user_id == 66
        # Verificar que se cargó la info del usuario
        assert log.access_user.first_name == "Santiago"


def test_get_logs_filter_by_device(sample_data):
    """Test filtrar logs por dispositivo"""
    repo = AccessLogRepository()
    
    logs = repo.get_logs_with_filters(device_id="1")
    
    assert len(logs) == 3
    for log in logs:
        assert log.device_id == "1"
        # Verificar que se cargó la info del dispositivo
        assert log.device.location == "raspberry-tic2"


def test_get_logs_multiple_filters(sample_data):
    """Test filtrar logs por usuario y dispositivo"""
    repo = AccessLogRepository()
    
    logs = repo.get_logs_with_filters(user_id=66, device_id="1")
    
    assert len(logs) == 1
    assert logs[0].access_user_id == 66
    assert logs[0].device_id == "1"
    assert logs[0].event == "accepted"


def test_get_logs_with_limit(sample_data):
    """Test límite de resultados"""
    repo = AccessLogRepository()
    
    logs = repo.get_logs_with_filters(limit=2)
    
    assert len(logs) == 2


def test_get_logs_with_null_user(sample_data):
    """Test obtener logs de usuarios no reconocidos"""
    repo = AccessLogRepository()
    
    # Obtener todos los logs
    logs = repo.get_logs_with_filters()
    
    # Buscar el log sin usuario
    null_user_logs = [log for log in logs if log.access_user_id is None]
    
    assert len(null_user_logs) == 1
    assert null_user_logs[0].access_user_id is None
    assert null_user_logs[0].event == "denied"
    # No debe tener relación con usuario
    assert not hasattr(null_user_logs[0], 'access_user') or null_user_logs[0].access_user is None