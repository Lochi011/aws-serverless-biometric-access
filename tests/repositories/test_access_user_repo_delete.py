# tests/repositories/test_access_user_repo_delete.py
import pytest
from datetime import datetime
from shared.models import db, AccessUser, Device, DeviceUserMapping, AccessLog
from repositories.access_user_repo import AccessUserRepository
import uuid


@pytest.fixture
def setup_db():
    """Crea las tablas necesarias para los tests"""
    db.connect()
    db.create_tables([AccessUser, Device, DeviceUserMapping, AccessLog])
    yield
    db.drop_tables([AccessUser, Device, DeviceUserMapping, AccessLog])
    db.close()


@pytest.fixture
def user_with_relations(setup_db):
    """Crea un usuario con todas sus relaciones"""
    # Crear usuario
    user = AccessUser.create(
        id=1,
        first_name="Juan",
        last_name="Pérez",
        cedula="12345678",
        created_at=datetime.now(),
        image_ref="https://bucket.s3.amazonaws.com/users/1/photo.jpg"
    )
    
    # Crear dispositivos (con id_device como string)
    device1 = Device.create(id_device="1", location="RaspberryPi-001")
    device2 = Device.create(id_device="2", location="RaspberryPi-002")
    
    # Crear mappings sin columna id
    DeviceUserMapping.create(access_user_id=user.id, device_id=device1.id_device)
    DeviceUserMapping.create(access_user_id=user.id, device_id=device2.id_device)
    
    # Crear logs
    AccessLog.create(
        id=uuid.uuid4(),
        access_user=user,
        device=device1,
        event="entry",
        timestamp=datetime.now()
    )
    
    return {
        'user': user,
        'devices': [device1, device2],
        'logs_count': 1,
        'mappings_count': 2
    }


def test_get_user_with_image(user_with_relations):
    """Test obtener usuario con imagen"""
    repo = AccessUserRepository()
    
    user = repo.get_user_with_image(1)
    
    assert user is not None
    assert user.cedula == "12345678"
    assert user.image_ref == "https://bucket.s3.amazonaws.com/users/1/photo.jpg"


def test_get_user_with_image_not_found(setup_db):
    """Test obtener usuario inexistente"""
    repo = AccessUserRepository()
    
    user = repo.get_user_with_image(999)
    
    assert user is None


def test_get_user_devices_locations(user_with_relations):
    """Test obtener ubicaciones de dispositivos del usuario"""
    repo = AccessUserRepository()
    
    locations = repo.get_user_devices_locations(1)
    
    assert len(locations) == 2
    assert "RaspberryPi-001" in locations
    assert "RaspberryPi-002" in locations


def test_get_user_devices_locations_empty(setup_db):
    """Test obtener dispositivos de usuario sin mappings"""
    user = AccessUser.create(
        id=2,
        first_name="María",
        last_name="González",
        cedula="87654321"
    )
    
    repo = AccessUserRepository()
    locations = repo.get_user_devices_locations(2)
    
    assert locations == []


def test_delete_user_and_related_data_success(user_with_relations):
    """Test eliminación exitosa de usuario y datos relacionados"""
    repo = AccessUserRepository()
    
    # Verificar datos antes de eliminar
    assert AccessUser.select().count() == 1
    assert AccessLog.select().count() == 1
    assert DeviceUserMapping.select().count() == 2
    
    # Eliminar usuario
    result = repo.delete_user_and_related_data(1)
    
    assert result is True
    
    # Verificar que todo fue eliminado
    assert AccessUser.select().count() == 0
    assert AccessLog.select().count() == 0
    assert DeviceUserMapping.select().count() == 0
    
    # Verificar que los dispositivos NO fueron eliminados
    assert Device.select().count() == 2


def test_delete_user_and_related_data_not_found(setup_db):
    """Test eliminar usuario inexistente"""
    repo = AccessUserRepository()
    
    result = repo.delete_user_and_related_data(999)
    
    assert result is False


def test_delete_user_transaction_rollback(user_with_relations, monkeypatch):
    """Test rollback de transacción en caso de error"""
    repo = AccessUserRepository()
    
    # Simular error durante la eliminación
    def mock_delete(*args, **kwargs):
        raise Exception("Error simulado")
    
    monkeypatch.setattr(AccessUser, "delete_instance", mock_delete)
    
    # Intentar eliminar
    with pytest.raises(Exception, match="Error simulado"):
        repo.delete_user_and_related_data(1)
    
    # Verificar que nada fue eliminado (rollback)
    assert AccessUser.select().count() == 1
    assert AccessLog.select().count() == 1
    assert DeviceUserMapping.select().count() == 2