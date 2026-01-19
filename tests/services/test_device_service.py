# tests/services/test_device_service.py
import pytest
from datetime import datetime
from services.device_service import DeviceService
from repositories.device_repo import DeviceRepository


class MockDevice:
    """Mock de Device para tests"""

    def __init__(self, id_device, location, status, last_sync=None):
        self.id_device = id_device  # String
        self.location = location
        self.status = status
        self.last_sync = last_sync


class MockDeviceRepository:
    """Mock del repositorio para tests del servicio"""

    def __init__(self, devices=None):
        self.devices = devices or []

    def get_by_id(self, device_id):
        # Convertir a string para comparación
        device_id_str = str(device_id)
        for device in self.devices:
            if device.id_device == device_id_str:
                return device
        return None

    def get_all(self):
        return self.devices

    def get_by_location(self, location):
        for device in self.devices:
            if device.location == location:
                return device
        return None


@pytest.fixture
def mock_devices():
    """Datos de prueba"""
    return [
        MockDevice("1", "raspberry-tic2", "active",
                   datetime(2024, 1, 1, 10, 0, 0)),
        MockDevice("2", "raspberry-lab1", "inactive", None),
        MockDevice("3", "raspberry-entrance", "active",
                   datetime(2024, 1, 2, 15, 30, 0))
    ]


def test_format_device():
    """Test formateo interno de dispositivo"""
    repo = MockDeviceRepository([])
    service = DeviceService(repo)

    device = MockDevice("1", "test-device", "active",
                        datetime(2024, 1, 1, 10, 0, 0))
    result = service._format_device(device)

    assert result['id_device'] == "1"  # Ya es string
    assert result['location'] == "test-device"
    assert result['status'] == "active"
    assert result['last_sync'] == "2024-01-01 10:00:00"


def test_format_device_no_sync():
    """Test formateo de dispositivo sin última sincronización"""
    repo = MockDeviceRepository([])
    service = DeviceService(repo)

    device = MockDevice("1", "test-device", "inactive", None)
    result = service._format_device(device)

    assert result['last_sync'] is None


def test_get_device_by_id_success(mock_devices):
    """Test obtener dispositivo por ID exitoso"""
    repo = MockDeviceRepository(mock_devices)
    service = DeviceService(repo)

    result = service.get_device_by_id("1")

    assert result['id_device'] == "1"
    assert result['location'] == "raspberry-tic2"
    assert result['status'] == "active"
    assert isinstance(result['last_sync'], str)


def test_get_device_by_id_empty():
    """Test con ID vacío"""
    repo = MockDeviceRepository([])
    service = DeviceService(repo)

    with pytest.raises(ValueError, match="ID de dispositivo requerido"):
        service.get_device_by_id("")


def test_get_device_by_id_not_found():
    """Test dispositivo no encontrado"""
    repo = MockDeviceRepository([])
    service = DeviceService(repo)

    with pytest.raises(LookupError, match="Dispositivo con ID 999 no encontrado"):
        service.get_device_by_id("999")


def test_get_all_devices(mock_devices):
    """Test obtener todos los dispositivos"""
    repo = MockDeviceRepository(mock_devices)
    service = DeviceService(repo)

    results = service.get_all_devices()

    assert len(results) == 3
    assert results[0]['location'] == "raspberry-tic2"
    assert results[1]['location'] == "raspberry-lab1"
    assert results[2]['location'] == "raspberry-entrance"

    # Verificar formato de respuesta
    for device in results:
        assert 'id_device' in device
        assert 'location' in device
        assert 'status' in device
        assert 'last_sync' in device


def test_get_all_devices_empty():
    """Test obtener dispositivos cuando no hay ninguno"""
    repo = MockDeviceRepository([])
    service = DeviceService(repo)

    results = service.get_all_devices()

    assert results == []


def test_get_device_by_location_success(mock_devices):
    """Test obtener dispositivo por ubicación exitoso"""
    repo = MockDeviceRepository(mock_devices)
    service = DeviceService(repo)

    result = service.get_device_by_location("raspberry-lab1")

    assert result is not None
    assert result['id_device'] == "2"
    assert result['location'] == "raspberry-lab1"
    assert result['status'] == "inactive"
    assert result['last_sync'] is None


def test_get_device_by_location_not_found(mock_devices):
    """Test obtener dispositivo por ubicación inexistente"""
    repo = MockDeviceRepository(mock_devices)
    service = DeviceService(repo)

    result = service.get_device_by_location("nonexistent")

    assert result is None
