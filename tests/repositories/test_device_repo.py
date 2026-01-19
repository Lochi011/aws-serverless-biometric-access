# tests/repositories/test_device_repo.py
import pytest
from datetime import datetime
from shared.models import db, Device
from repositories.device_repo import DeviceRepository


@pytest.fixture
def setup_db():
    """Crea las tablas necesarias para los tests"""
    db.connect()
    db.create_tables([Device])
    yield
    db.drop_tables([Device])
    db.close()


@pytest.fixture
def sample_devices(setup_db):
    """Crea dispositivos de prueba"""
    device1 = Device.create(
        id_device="1",  # String en lugar de int
        location="raspberry-tic2",
        status="active",
        last_sync=datetime(2024, 1, 1, 10, 0, 0)
    )
    device2 = Device.create(
        id_device="2",
        location="raspberry-lab1",
        status="inactive",
        last_sync=None
    )
    device3 = Device.create(
        id_device="3",
        location="raspberry-entrance",
        status="active",
        last_sync=datetime(2024, 1, 2, 15, 30, 0)
    )
    
    return [device1, device2, device3]


def test_get_by_id_success(sample_devices):
    """Test obtener dispositivo por ID exitoso"""
    repo = DeviceRepository()
    
    # Probar con string
    device = repo.get_by_id("1")
    
    assert device is not None
    assert device.id_device == "1"
    assert device.location == "raspberry-tic2"
    assert device.status == "active"
    
    # Probar con int (debe convertirse a string internamente)
    device2 = repo.get_by_id(2)
    assert device2 is not None
    assert device2.id_device == "2"


def test_get_by_id_not_found(setup_db):
    """Test obtener dispositivo inexistente"""
    repo = DeviceRepository()
    
    device = repo.get_by_id(999)
    
    assert device is None


def test_get_all(sample_devices):
    """Test obtener todos los dispositivos"""
    repo = DeviceRepository()
    
    devices = repo.get_all()
    
    assert len(devices) == 3
    # Verificar que están ordenados por ID
    assert devices[0].id_device == "1"
    assert devices[1].id_device == "2"
    assert devices[2].id_device == "3"


def test_get_all_empty(setup_db):
    """Test obtener dispositivos cuando no hay ninguno"""
    repo = DeviceRepository()
    
    devices = repo.get_all()
    
    assert devices == []


def test_exists(sample_devices):
    """Test verificar si existe dispositivo por ubicación"""
    repo = DeviceRepository()
    
    assert repo.exists("raspberry-tic2") is True
    assert repo.exists("raspberry-nonexistent") is False


def test_get_by_location(sample_devices):
    """Test obtener dispositivo por ubicación"""
    repo = DeviceRepository()
    
    device = repo.get_by_location("raspberry-lab1")
    
    assert device is not None
    assert device.id_device == "2"
    assert device.status == "inactive"
    assert device.last_sync is None


def test_get_id_by_location(sample_devices):
    """Test obtener ID por ubicación (compatibilidad)"""
    repo = DeviceRepository()
    
    device_id = repo.get_id_by_location("raspberry-entrance")
    
    assert device_id == "3"  # Ahora devuelve string


def test_get_id_by_location_not_found(setup_db):
    """Test obtener ID por ubicación inexistente"""
    repo = DeviceRepository()
    
    device_id = repo.get_id_by_location("nonexistent")
    
    assert device_id is None


def test_create(setup_db):
    """Test crear nuevo dispositivo"""
    repo = DeviceRepository()
    
    device = repo.create(
        id_device="10",  # String
        location="raspberry-new",
        status="pending"
    )
    
    assert device.id_device == "10"
    assert device.location == "raspberry-new"
    assert device.status == "pending"
    
    # Verificar que se guardó
    saved = repo.get_by_id("10")
    assert saved is not None


def test_update_status(sample_devices):
    """Test actualizar estado de dispositivo"""
    repo = DeviceRepository()
    
    # Probar con string
    result = repo.update_status("1", "inactive")
    
    assert result is True
    
    # Verificar que se actualizó
    device = repo.get_by_id("1")
    assert device.status == "inactive"


def test_update_status_not_found(setup_db):
    """Test actualizar estado de dispositivo inexistente"""
    repo = DeviceRepository()
    
    result = repo.update_status("999", "active")
    
    assert result is False


def test_update_last_sync(sample_devices):
    """Test actualizar última sincronización"""
    repo = DeviceRepository()
    new_sync = datetime(2024, 2, 1, 12, 0, 0)
    
    result = repo.update_last_sync("2", new_sync)
    
    assert result is True
    
    # Verificar que se actualizó
    device = repo.get_by_id("2")
    assert device.last_sync == new_sync