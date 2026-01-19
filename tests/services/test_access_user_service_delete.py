# tests/services/test_access_user_service_delete.py
import pytest
from unittest.mock import MagicMock, patch, call
from services.access_users_service import AccessUserService
from repositories.access_user_repo import AccessUserRepository


class MockUser:
    """Mock de AccessUser"""

    def __init__(self, id, cedula, image_ref=None):
        self.id = id
        self.cedula = cedula
        self.image_ref = image_ref


@pytest.fixture
def mock_aws_clients():
    """Mock de clientes AWS"""
    with patch('boto3.client') as mock_boto:
        mock_s3 = MagicMock()
        mock_iot = MagicMock()

        def client_side_effect(service_name, **kwargs):
            if service_name == 's3':
                return mock_s3
            elif service_name == 'iot-data':
                return mock_iot
            return MagicMock()

        mock_boto.side_effect = client_side_effect

        yield {
            's3': mock_s3,
            'iot': mock_iot
        }


@pytest.fixture
def mock_repository():
    """Mock del repositorio"""
    repo = MagicMock(spec=AccessUserRepository)
    return repo


def test_delete_user_success(mock_repository, mock_aws_clients, monkeypatch):
    """Test eliminación exitosa de usuario"""
    # Configurar entorno
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    monkeypatch.setenv("IOT_ENDPOINT", "test.iot.amazonaws.com")

    # Configurar mocks
    mock_user = MockUser(
        1, "12345678", "https://bucket.s3.amazonaws.com/users/1/photo.jpg")
    mock_repository.get_user_with_image.return_value = mock_user
    mock_repository.get_user_devices_locations.return_value = [
        "RaspberryPi-001", "RaspberryPi-002"]
    mock_repository.delete_user_and_related_data.return_value = True

    # Crear servicio y ejecutar
    service = AccessUserService(mock_repository)
    service.s3 = mock_aws_clients['s3']
    service.iot = mock_aws_clients['iot']

    result = service.delete_user("1")

    # Verificar llamadas
    mock_repository.get_user_with_image.assert_called_once_with(1)
    mock_repository.get_user_devices_locations.assert_called_once_with(1)
    mock_repository.delete_user_and_related_data.assert_called_once_with(1)

    # Verificar eliminación de S3
    mock_aws_clients['s3'].delete_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="users/1/photo.jpg"
    )

    # Verificar notificaciones IoT
    assert mock_aws_clients['iot'].publish.call_count == 2
    calls = mock_aws_clients['iot'].publish.call_args_list
    assert calls[0][1]['topic'] == "access/users/delete/RaspberryPi-001"
    assert calls[1][1]['topic'] == "access/users/delete/RaspberryPi-002"

    # Verificar resultado
    assert result['message'] == "User and image deleted successfully"
    assert result['user_id'] == "1"
    assert result['raspis_notified'] == ["RaspberryPi-001", "RaspberryPi-002"]


def test_delete_user_invalid_id(mock_repository, mock_aws_clients):
    """Test con ID inválido"""
    service = AccessUserService(mock_repository)

    with pytest.raises(ValueError, match="ID de usuario inválido"):
        service.delete_user("abc")


def test_delete_user_not_found(mock_repository, mock_aws_clients):
    """Test usuario no encontrado"""
    mock_repository.get_user_with_image.return_value = None

    service = AccessUserService(mock_repository)

    with pytest.raises(LookupError, match="Usuario con ID 999 no encontrado"):
        service.delete_user("999")


def test_delete_user_without_image(mock_repository, mock_aws_clients, monkeypatch):
    """Test eliminar usuario sin imagen"""
    monkeypatch.setenv("S3_BUCKET", "test-bucket")

    # Usuario sin imagen
    mock_user = MockUser(1, "12345678", None)
    mock_repository.get_user_with_image.return_value = mock_user
    mock_repository.get_user_devices_locations.return_value = []
    mock_repository.delete_user_and_related_data.return_value = True

    service = AccessUserService(mock_repository)
    service.s3 = mock_aws_clients['s3']

    result = service.delete_user("1")

    # No debe intentar eliminar de S3
    mock_aws_clients['s3'].delete_object.assert_not_called()

    assert result['message'] == "User and image deleted successfully"


def test_delete_user_s3_error_continues(mock_repository, mock_aws_clients, monkeypatch):
    """Test que la eliminación continúa aunque falle S3"""
    monkeypatch.setenv("S3_BUCKET", "test-bucket")

    # Configurar mocks
    mock_user = MockUser(
        1, "12345678", "https://bucket.s3.amazonaws.com/users/1/photo.jpg")
    mock_repository.get_user_with_image.return_value = mock_user
    mock_repository.get_user_devices_locations.return_value = []
    mock_repository.delete_user_and_related_data.return_value = True

    # S3 lanza excepción
    mock_aws_clients['s3'].delete_object.side_effect = Exception("S3 Error")

    service = AccessUserService(mock_repository)
    service.s3 = mock_aws_clients['s3']

    # No debe lanzar excepción
    result = service.delete_user("1")

    assert result['message'] == "User and image deleted successfully"
    mock_repository.delete_user_and_related_data.assert_called_once()


def test_delete_user_iot_error_continues(mock_repository, mock_aws_clients, monkeypatch):
    """Test que la eliminación continúa aunque falle IoT"""
    monkeypatch.setenv("IOT_ENDPOINT", "test.iot.amazonaws.com")

    # Configurar mocks
    mock_user = MockUser(1, "12345678", None)
    mock_repository.get_user_with_image.return_value = mock_user
    mock_repository.get_user_devices_locations.return_value = [
        "RaspberryPi-001"]
    mock_repository.delete_user_and_related_data.return_value = True

    # IoT lanza excepción
    mock_aws_clients['iot'].publish.side_effect = Exception("IoT Error")

    service = AccessUserService(mock_repository)
    service.iot = mock_aws_clients['iot']

    # No debe lanzar excepción
    result = service.delete_user("1")

    assert result['message'] == "User and image deleted successfully"
