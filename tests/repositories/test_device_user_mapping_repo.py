import pytest
from shared.models import db, AccessUser, Device, DeviceUserMapping
from repositories.device_user_mapping_repo import DeviceUserMappingRepository


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
        rfid="RFID123",
        image_ref="https://bucket.s3.amazonaws.com/user1.jpg",
        face_embedding="[0.1, 0.2, 0.3]"
    )
    user2 = AccessUser.create(
        id=2,
        first_name="María",
        last_name="García",
        cedula="87654321"
    )
    
    # Crear dispositivos
    device1 = Device.create(id_device="1", location="raspberry-tic2")
    device2 = Device.create(id_device="2", location="raspberry-lab1")
    device3 = Device.create(id_device="3", location="FCEE")
    
    # Crear algunos mappings existentes
    DeviceUserMapping.create(access_user_id=user1.id, device_id=device1.id_device)
    
    return {
        'users': [user1, user2],
        'devices': [device1, device2, device3]
    }


def test_add_device_access_success(sample_data):
    """Test agregar acceso exitosamente"""
    repo = DeviceUserMappingRepository()
    user = sample_data['users'][1]  # María
    device = sample_data['devices'][1]  # raspberry-lab1
    
    result = repo.add_device_access(user.id, device.id_device)
    
    assert result is True
    # Verificar que se creó el mapping
    mapping = DeviceUserMapping.get(
        (DeviceUserMapping.access_user_id == user.id) &
        (DeviceUserMapping.device_id == device.id_device)
    )
    assert mapping is not None


def test_add_device_access_duplicate(sample_data):
    """Test agregar acceso que ya existe"""
    repo = DeviceUserMappingRepository()
    user = sample_data['users'][0]  # Juan
    device = sample_data['devices'][0]  # raspberry-tic2 (ya tiene acceso)
    
    result = repo.add_device_access(user.id, device.id_device)
    
    assert result is False  # No se agregó porque ya existía


def test_remove_device_access_success(sample_data):
    """Test eliminar acceso exitosamente"""
    repo = DeviceUserMappingRepository()
    user = sample_data['users'][0]  # Juan
    device = sample_data['devices'][0]  # raspberry-tic2
    
    deleted = repo.remove_device_access(user.id, device.id_device)
    
    assert deleted == 1
    # Verificar que se eliminó el mapping
    mapping_exists = DeviceUserMapping.select().where(
        (DeviceUserMapping.access_user_id == user.id) &
        (DeviceUserMapping.device_id == device.id_device)
    ).exists()
    assert not mapping_exists


def test_remove_device_access_not_found(sample_data):
    """Test eliminar acceso que no existe"""
    repo = DeviceUserMappingRepository()
    user = sample_data['users'][1]  # María
    device = sample_data['devices'][0]  # raspberry-tic2
    
    deleted = repo.remove_device_access(user.id, device.id_device)
    
    assert deleted == 0


def test_get_user_devices(sample_data):
    """Test obtener dispositivos de un usuario"""
    repo = DeviceUserMappingRepository()
    user = sample_data['users'][0]  # Juan
    
    devices = repo.get_user_devices(user.id)
    
    assert len(devices) == 1
    assert devices[0].id_device == "1"
    assert devices[0].location == "raspberry-tic2"


def test_get_user_devices_empty(sample_data):
    """Test obtener dispositivos de usuario sin accesos"""
    repo = DeviceUserMappingRepository()
    user = sample_data['users'][1]  # María
    
    devices = repo.get_user_devices(user.id)
    
    assert len(devices) == 0


def test_bulk_update_user_devices(sample_data):
    """Test actualización masiva de accesos"""
    repo = DeviceUserMappingRepository()
    user = sample_data['users'][0]  # Juan
    
    # Preparar datos para actualización
    devices_to_add = [
        ("2", "raspberry-lab1"),
        ("3", "FCEE")
    ]
    devices_to_remove = [
        ("1", "raspberry-tic2")  # Eliminar acceso existente
    ]
    
    added, removed = repo.bulk_update_user_devices(
        user.id,
        devices_to_add,
        devices_to_remove
    )
    
    # Verificar resultados
    assert len(added) == 2
    assert "raspberry-lab1" in added
    assert "FCEE" in added
    assert len(removed) == 1
    assert "raspberry-tic2" in removed
    
    # Verificar estado final en la BD
    final_devices = repo.get_user_devices(user.id)
    assert len(final_devices) == 2
    device_ids = {d.id_device for d in final_devices}
    assert "2" in device_ids
    assert "3" in device_ids
    assert "1" not in device_ids


def test_bulk_update_user_devices_transaction_rollback(sample_data, monkeypatch):
    """Test rollback de transacción en caso de error"""
    repo = DeviceUserMappingRepository()
    user = sample_data['users'][0]  # Juan
    
    # Simular error durante la actualización
    def mock_add(*args, **kwargs):
        raise Exception("Error simulado")
    
    monkeypatch.setattr(repo, "add_device_access", mock_add)
    
    # Intentar actualización que fallará
    with pytest.raises(Exception, match="Error simulado"):
        repo.bulk_update_user_devices(
            user.id,
            [("2", "raspberry-lab1")],
            [("1", "raspberry-tic2")]
        )
    
    # Verificar que no se realizaron cambios (rollback)
    devices = repo.get_user_devices(user.id)
    assert len(devices) == 1
    assert devices[0].id_device == "1"
