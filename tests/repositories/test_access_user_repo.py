# tests/repositories/test_access_user_repo.py
import pytest
from datetime import datetime
from shared.models import db, AccessUser, Device, DeviceUserMapping
from repositories.access_user_repo import AccessUserRepository


@pytest.fixture
def setup_db():
    """Crea las tablas necesarias para los tests"""
    db.connect()
    db.create_tables([AccessUser, Device, DeviceUserMapping])
    yield
    db.drop_tables([AccessUser, Device, DeviceUserMapping])
    db.close()


@pytest.fixture
def sample_data(setup_db):
    """Crea datos de prueba"""
    # Crear usuarios
    user1 = AccessUser.create(
        id=1,
        first_name="Juan",
        last_name="Pérez",
        cedula="12345678",
        created_at=datetime.now(),
        image_ref="user1.jpg"
    )
    user2 = AccessUser.create(
        id=2,
        first_name="María",
        last_name="González",
        cedula="87654321",
        created_at=datetime.now(),
        image_ref="user2.jpg"
    )
    
    # Crear dispositivos (con id_device como string)
    device1 = Device.create(id_device="1", location="Puerta Principal")
    device2 = Device.create(id_device="2", location="Puerta Trasera")
    
    # Crear mappings sin especificar id
    DeviceUserMapping.create(access_user_id=user1.id, device_id=device1.id_device)
    DeviceUserMapping.create(access_user_id=user1.id, device_id=device2.id_device)
    DeviceUserMapping.create(access_user_id=user2.id, device_id=device1.id_device)
    
    return {
        'users': [user1, user2],
        'devices': [device1, device2]
    }


def test_get_by_id_with_devices(sample_data):
    """Test obtener usuario por ID con dispositivos"""
    repo = AccessUserRepository()
    
    user = repo.get_by_id_with_devices(1)
    
    assert user is not None
    assert user.id == 1
    assert user.first_name == "Juan"
    assert user.cedula == "12345678"
    assert hasattr(user, '_mappings')
    assert len(user._mappings) == 2
    # Verificar que los devices están cargados
    locations = [m.device.location for m in user._mappings]
    assert "Puerta Principal" in locations
    assert "Puerta Trasera" in locations


def test_get_by_id_with_devices_not_found(setup_db):
    """Test obtener usuario inexistente"""
    repo = AccessUserRepository()
    
    user = repo.get_by_id_with_devices(999)
    
    assert user is None


def test_get_all_with_devices(sample_data):
    """Test obtener todos los usuarios con dispositivos"""
    repo = AccessUserRepository()
    
    users = repo.get_all_with_devices()
    
    assert len(users) == 2
    
    # Verificar primer usuario
    user1 = users[0]
    assert user1.first_name == "Juan"
    assert hasattr(user1, '_mappings')
    assert len(user1._mappings) == 2
    
    # Verificar segundo usuario
    user2 = users[1]
    assert user2.first_name == "María"
    assert hasattr(user2, '_mappings')
    assert len(user2._mappings) == 1
    assert user2._mappings[0].device.location == "Puerta Principal"


def test_get_all_with_devices_empty_db(setup_db):
    """Test obtener usuarios cuando no hay datos"""
    repo = AccessUserRepository()
    
    users = repo.get_all_with_devices()
    
    assert users == []


def test_exists(sample_data):
    """Test verificar si existe usuario por cédula"""
    repo = AccessUserRepository()
    
    assert repo.exists("12345678") is True
    assert repo.exists("99999999") is False


def test_get_by_cedula(sample_data):
    """Test obtener usuario por cédula"""
    repo = AccessUserRepository()
    
    user = repo.get_by_cedula("12345678")
    
    assert user.first_name == "Juan"
    assert user.last_name == "Pérez"