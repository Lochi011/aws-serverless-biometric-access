import pytest
import json
import time
import boto3
import os
from services.access_users_service import AccessUserService
from repositories.access_user_repo import AccessUserRepository
from shared.models import db, AccessUser, Device, DeviceUserMapping

# Configurar variables de entorno
# Reemplazar con tu endpoint real
os.environ["IOT_ENDPOINT"] = "a11c3004sdvacu-ats.iot.us-east-1.amazonaws.com"


@pytest.fixture
def setup_db():
    """Crea las tablas necesarias para los tests"""
    db.connect()
    db.create_tables([AccessUser, Device, DeviceUserMapping])
    yield
    db.drop_tables([AccessUser, Device, DeviceUserMapping])
    db.close()


@pytest.fixture
def test_user(setup_db):
    """Crea un usuario de prueba con acceso a un dispositivo"""
    # Crear dispositivo
    device = Device.create(
        id_device="test-device-1",
        location="RaspberryPi-Test"
    )

    # Crear usuario
    user = AccessUser.create(
        id=999,  # ID específico para tests
        first_name="Test",
        last_name="User",
        cedula="99999999"
    )

    # Crear mapping
    DeviceUserMapping.create(
        access_user_id=user.id,
        device_id=device.id_device
    )

    return {
        'user': user,
        'device': device
    }


def test_delete_user_notification(test_user):
    """Test de integración: verifica que se recibe la notificación IoT al eliminar usuario"""
    # Crear cliente IoT
    iot = boto3.client(
        "iot-data",
        endpoint_url=f"https://{os.environ['IOT_ENDPOINT']}"
    )

    # Crear cliente IoT Test Client
    iot_test = boto3.client('iot')

    # Suscribirse al topic
    topic = "access/users/delete/#"
    subscription = iot_test.subscribe(
        topic=topic,
        qos=1
    )

    try:
        # Esperar un momento para asegurar la suscripción
        time.sleep(2)

        # Eliminar el usuario
        service = AccessUserService(AccessUserRepository())
        result = service.delete_user("999")

        # Esperar un momento para recibir el mensaje
        time.sleep(2)

        # Verificar que el usuario fue eliminado
        assert result['message'] == "User and image deleted successfully"
        assert result['user_id'] == "999"
        assert "RaspberryPi-Test" in result['raspis_notified']

        # Obtener mensajes recibidos
        messages = iot_test.get_messages(
            subscriptionArn=subscription['subscriptionArn']
        )

        # Verificar que recibimos el mensaje correcto
        assert len(messages['messages']) > 0

        # El último mensaje debería ser el de eliminación
        last_message = messages['messages'][-1]
        assert last_message['topic'] == "access/users/delete/RaspberryPi-Test"

        payload = json.loads(last_message['payload'])
        assert payload['cedula'] == "99999999"

    finally:
        # Limpiar suscripción
        iot_test.unsubscribe(
            subscriptionArn=subscription['subscriptionArn']
        )
