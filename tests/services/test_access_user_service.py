# tests/services/test_access_user_service.py
import pytest
from datetime import datetime
from services.access_users_service import AccessUserService
from repositories.access_user_repo import AccessUserRepository


class MockDevice:
    """Mock de Device para tests"""

    def __init__(self, id_device, location):
        self.id_device = id_device
        self.location = location


class MockMapping:
    """Mock de DeviceUserMapping para tests"""

    def __init__(self, device):
        self.device = device


class MockUser:
    """Mock de AccessUser para tests"""

    def __init__(self, id, first_name, last_name, cedula, created_at, image_ref, mappings=None):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.cedula = cedula
        self.created_at = created_at
        self.image_ref = image_ref
        self._mappings = mappings or []


class MockAccessUserRepository:
    """Mock del repositorio para tests del servicio"""

    def __init__(self, users=None):
        self.users = users or []

    def get_by_id_with_devices(self, user_id):
        for user in self.users:
            if user.id == user_id:
                return user
        return None

    def get_all_with_devices(self):
        return self.users


@pytest.fixture
def mock_users():
    """Datos de prueba con estructura Peewee"""
    # Crear devices mock
    device1 = MockDevice(1, "Puerta Principal")
    device2 = MockDevice(2, "Puerta Trasera")

    # Crear mappings mock
    mapping1 = MockMapping(device1)
    mapping2 = MockMapping(device2)

    # Crear usuarios mock
    user1 = MockUser(
        id=1,
        first_name="Juan",
        last_name="Pérez",
        cedula="12345678",
        created_at=datetime(2024, 1, 1, 10, 0, 0),
        image_ref="user1.jpg",
        mappings=[mapping1, mapping2]
    )

    user2 = MockUser(
        id=2,
        first_name="María",
        last_name="González",
        cedula="87654321",
        created_at=datetime(2024, 1, 2, 11, 0, 0),
        image_ref="user2.jpg",
        mappings=[]
    )

    return [user1, user2]


def test_format_user_with_doors(mock_users):
    """Test formateo interno de usuario con puertas"""
    repo = MockAccessUserRepository([])
    service = AccessUserService(repo)

    user = mock_users[0]
    result = service._format_user_with_doors(user)

    assert result['id'] == 1
    assert result['first_name'] == 'Juan'
    assert result['cedula'] == '12345678'
    assert len(result['doors']) == 2
    assert result['doors'][0]['device_id'] == 1
    assert result['doors'][0]['location'] == 'Puerta Principal'
    assert isinstance(result['created_at'], str)


def test_get_user_by_id_success(mock_users):
    """Test obtener usuario por ID exitoso"""
    repo = MockAccessUserRepository(mock_users)
    service = AccessUserService(repo)

    result = service.get_user_by_id("1")

    assert result['id'] == 1
    assert result['first_name'] == 'Juan'
    assert len(result['doors']) == 2
    assert isinstance(result['created_at'], str)


def test_get_user_by_id_invalid_id():
    """Test con ID inválido"""
    repo = MockAccessUserRepository([])
    service = AccessUserService(repo)

    with pytest.raises(ValueError, match="ID de usuario inválido"):
        service.get_user_by_id("abc")


def test_get_user_by_id_not_found():
    """Test usuario no encontrado"""
    repo = MockAccessUserRepository([])
    service = AccessUserService(repo)

    with pytest.raises(LookupError, match="Usuario con ID 999 no encontrado"):
        service.get_user_by_id("999")


def test_get_all_users(mock_users):
    """Test obtener todos los usuarios"""
    repo = MockAccessUserRepository(mock_users)
    service = AccessUserService(repo)

    results = service.get_all_users()

    assert len(results) == 2
    assert results[0]['first_name'] == 'Juan'
    assert len(results[0]['doors']) == 2
    assert results[1]['first_name'] == 'María'
    assert len(results[1]['doors']) == 0
    # Verificar que created_at se convirtió a string
    assert all(isinstance(user['created_at'], str) for user in results)


def test_get_all_users_empty():
    """Test obtener usuarios cuando no hay ninguno"""
    repo = MockAccessUserRepository([])
    service = AccessUserService(repo)

    results = service.get_all_users()

    assert results == []
