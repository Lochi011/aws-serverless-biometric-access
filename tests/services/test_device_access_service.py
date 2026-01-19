# tests/services/test_device_access_service.py
import pytest
from unittest.mock import MagicMock, patch, call
from services.device_access_service import DeviceAccessService


class MockUser:
    def __init__(self, id, first_name, last_name, cedula, rfid=None, image_ref=None, face_embedding=None):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.cedula = cedula
        self.rfid = rfid
        self.image_ref = image_ref
        self.face_embedding = face_embedding


class MockDevice:
    def __init__(self, id_device, location):
        self.id_device = id_device
        self.location = location


@pytest.fixture
def mock_repositories():
    """Mock de los repositorios"""
    user_repo = MagicMock()
    device_repo = MagicMock()
    mapping_repo = MagicMock()
    
    return user_repo, device_repo, mapping_repo


@pytest.fixture
def mock_iot_client():
    """Mock del cliente IoT"""
    with patch('boto3.client') as mock_boto:
        mock_iot = MagicMock()
        mock_boto.return_value = mock_iot
        yield mock_iot


def test_update_user_device_access_success(mock_repositories, mock_iot_client, monkeypatch):
    """Test actualización exitosa de accesos"""
    monkeypatch.setenv("IOT_ENDPOINT", "test.iot.amazonaws.com")
    
    user_repo, device_repo, mapping_repo = mock_repositories
    
    # Configurar mocks
    user = MockUser(1, "Juan", "Pérez", "12345678", "RFID123", "https://bucket/user.jpg", "[0.1,0.2]")
    user_repo.get_by_id.return_value = user
    
    device1 = MockDevice("1", "raspberry-tic2")
    device2 = MockDevice("2", "raspberry-lab1")
    device3 = MockDevice("3", "FCEE")
    
    def get_by_location_side_effect(location):
        devices = {
            "raspberry-tic2": device1,
            "raspberry-lab1": device2,
            "FCEE": device3
        }
        return devices.get(location)
    
    device_repo.get_by_location.side_effect = get_by_location_side_effect
    
    mapping_repo.bulk_update_user_devices.return_value = (
        ["raspberry-tic2"],  # agregados
        ["FCEE"]            # eliminados
    )
    
    # Crear servicio
    service = DeviceAccessService(user_repo, device_repo, mapping_repo)
    service.iot = mock_iot_client
    
    # Ejecutar
    result = service.update_user_device_access(
        "1",
        ["raspberry-tic2"],
        ["FCEE"]
    )
    
    # Verificar llamadas
    user_repo.get_by_id.assert_called_once_with(1)
    device_repo.get_by_location.assert_any_call("raspberry-tic2")
    device_repo.get_by_location.assert_any_call("FCEE")
    
    mapping_repo.bulk_update_user_devices.assert_called_once_with(
        1,
        [("1", "raspberry-tic2")],
        [("3", "FCEE")]
    )
    
    # Verificar notificaciones IoT
    assert mock_iot_client.publish.call_count == 2
    
    # Verificar notificación de eliminar
    delete_call = mock_iot_client.publish.call_args_list[0]
    assert delete_call[1]['topic'] == "access/users/delete/FCEE"
    assert '"cedula": "12345678"' in delete_call[1]['payload']
    
    # Verificar notificación de agregar
    add_call = mock_iot_client.publish.call_args_list[1]
    assert add_call[1]['topic'] == "access/users/new/raspberry-tic2"
    assert '"cedula": "12345678"' in add_call[1]['payload']
    assert '"first_name": "Juan"' in add_call[1]['payload']
    
    # Verificar resultado
    assert result['message'] == "User device access updated"
    assert result['added'] == ["raspberry-tic2"]
    assert result['removed'] == ["FCEE"]


def test_update_user_device_access_invalid_user_id(mock_repositories, mock_iot_client):
    """Test con ID de usuario inválido"""
    user_repo, device_repo, mapping_repo = mock_repositories
    
    service = DeviceAccessService(user_repo, device_repo, mapping_repo)
    
    with pytest.raises(ValueError, match="ID de usuario inválido"):
        service.update_user_device_access("abc", [], [])


def test_update_user_device_access_user_not_found(mock_repositories, mock_iot_client):
    """Test con usuario no encontrado"""
    user_repo, device_repo, mapping_repo = mock_repositories
    user_repo.get_by_id.return_value = None
    
    service = DeviceAccessService(user_repo, device_repo, mapping_repo)
    
    with pytest.raises(LookupError, match="Usuario con ID 999 no encontrado"):
        service.update_user_device_access("999", [], [])


def test_update_user_device_access_invalid_lists(mock_repositories, mock_iot_client):
    """Test con listas inválidas"""
    user_repo, device_repo, mapping_repo = mock_repositories
    
    service = DeviceAccessService(user_repo, device_repo, mapping_repo)
    
    with pytest.raises(ValueError, match="addDevices y removeDevices deben ser listas"):
        service.update_user_device_access("1", "not-a-list", [])


def test_update_user_device_access_device_not_found(mock_repositories, mock_iot_client, monkeypatch):
    """Test cuando algunos dispositivos no existen"""
    monkeypatch.setenv("IOT_ENDPOINT", "test.iot.amazonaws.com")
    
    user_repo, device_repo, mapping_repo = mock_repositories
    
    user = MockUser(1, "Juan", "Pérez", "12345678")
    user_repo.get_by_id.return_value = user
    
    # Solo device1 existe
    device1 = MockDevice("1", "raspberry-tic2")
    device_repo.get_by_location.side_effect = lambda loc: device1 if loc == "raspberry-tic2" else None
    
    mapping_repo.bulk_update_user_devices.return_value = (["raspberry-tic2"], [])
    
    service = DeviceAccessService(user_repo, device_repo, mapping_repo)
    service.iot = mock_iot_client
    
    # Ejecutar con dispositivos que no existen
    result = service.update_user_device_access(
        "1",
        ["raspberry-tic2", "device-inexistente"],
        ["otro-inexistente"]
    )
    
    # Solo debe procesar el dispositivo que existe
    mapping_repo.bulk_update_user_devices.assert_called_once_with(
        1,
        [("1", "raspberry-tic2")],
        []
    )
    
    assert result['added'] == ["raspberry-tic2"]
    assert result['removed'] == []


def test_update_user_device_access_no_changes(mock_repositories, mock_iot_client, monkeypatch):
    """Test cuando no hay cambios que hacer"""
    monkeypatch.setenv("IOT_ENDPOINT", "test.iot.amazonaws.com")
    
    user_repo, device_repo, mapping_repo = mock_repositories
    
    user = MockUser(1, "Juan", "Pérez", "12345678")
    user_repo.get_by_id.return_value = user
    
    device_repo.get_by_location.return_value = None  # No encuentra ningún dispositivo
    mapping_repo.bulk_update_user_devices.return_value = ([], [])
    
    service = DeviceAccessService(user_repo, device_repo, mapping_repo)
    service.iot = mock_iot_client
    
    result = service.update_user_device_access("1", ["inexistente"], ["otro-inexistente"])
    
    # No debe haber notificaciones IoT
    mock_iot_client.publish.assert_not_called()
    
    assert result['added'] == []
    assert result['removed'] == []