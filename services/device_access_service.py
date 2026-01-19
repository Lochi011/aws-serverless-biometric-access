# services/device_access_service.py
import json
import boto3
import os
import logging
from typing import List, Dict, Tuple
from repositories.access_user_repo import AccessUserRepository
from repositories.device_repo import DeviceRepository
from repositories.device_user_mapping_repo import DeviceUserMappingRepository
from shared.models import AccessUser
logger = logging.getLogger()


class DeviceAccessService:
    """Servicio para gestionar acceso de usuarios a dispositivos"""

    def __init__(
        self,
        user_repo: AccessUserRepository,
        device_repo: DeviceRepository,
        mapping_repo: DeviceUserMappingRepository
    ):
        self.user_repo = user_repo
        self.device_repo = device_repo
        self.mapping_repo = mapping_repo

        # Cliente IoT
        self.iot = boto3.client(
            "iot-data",
            endpoint_url=f"https://{os.environ.get('IOT_ENDPOINT', '')}"
        )

    def _get_user_info_for_iot(self, user: AccessUser) -> Dict:
        """
        Prepara la información del usuario para enviar por IoT.

        Args:
            user: Instancia de AccessUser

        Returns:
            Dict con información del usuario
        """
        return {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "cedula": user.cedula,
            "rfid": user.rfid,
            "image_ref": user.image_ref,
            "face_embedding": user.face_embedding
        }

    def _notify_add_user(self, user_info: Dict, device_locations: List[str]) -> None:
        """
        Notifica a las Raspberry Pi que agreguen un usuario.

        Args:
            user_info: Información del usuario
            device_locations: Lista de ubicaciones de dispositivos
        """
        for location in device_locations:
            try:
                topic = f"access/users/new/{location}"
                payload = json.dumps(user_info)

                self.iot.publish(
                    topic=topic,
                    qos=1,
                    payload=payload
                )
                logger.info(f"Notificación de agregar enviada a {location}")

            except Exception as e:
                logger.error(f"Error notificando agregar a {location}: {e}")

    def _notify_remove_user(self, cedula: str, device_locations: List[str]) -> None:
        """
        Notifica a las Raspberry Pi que eliminen un usuario.

        Args:
            cedula: Cédula del usuario a eliminar
            device_locations: Lista de ubicaciones de dispositivos
        """
        for location in device_locations:
            try:
                topic = f"access/users/delete/{location}"
                payload = json.dumps({"cedula": cedula})

                self.iot.publish(
                    topic=topic,
                    qos=1,
                    payload=payload
                )
                logger.info(f"Notificación de eliminar enviada a {location}")

            except Exception as e:
                logger.error(f"Error notificando eliminar a {location}: {e}")

    def update_user_device_access(
        self,
        user_id: str,
        add_devices: List[str],
        remove_devices: List[str]
    ) -> Dict:
        """
        Actualiza los dispositivos a los que tiene acceso un usuario.

        Args:
            user_id: ID del usuario (string desde path parameter)
            add_devices: Lista de nombres de dispositivos a agregar
            remove_devices: Lista de nombres de dispositivos a eliminar

        Returns:
            Dict con dispositivos agregados y eliminados

        Raises:
            ValueError: Si los parámetros son inválidos
            LookupError: Si el usuario no existe
        """
        # Validar user_id
        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            raise ValueError("ID de usuario inválido")

        # Validar que las listas sean listas
        if not isinstance(add_devices, list) or not isinstance(remove_devices, list):
            raise ValueError("addDevices y removeDevices deben ser listas")

        # Obtener usuario
        user = self.user_repo.get_by_id(user_id_int)
        if not user:
            raise LookupError(f"Usuario con ID {user_id} no encontrado")

        # Preparar dispositivos para agregar
        devices_to_add = []
        for device_name in add_devices:
            device = self.device_repo.get_by_location(device_name)
            if device:
                devices_to_add.append((device.id_device, device_name))
            else:
                logger.warning(f"Dispositivo '{device_name}' no encontrado")

        # Preparar dispositivos para eliminar
        devices_to_remove = []
        for device_name in remove_devices:
            device = self.device_repo.get_by_location(device_name)
            if device:
                devices_to_remove.append((device.id_device, device_name))
            else:
                logger.warning(f"Dispositivo '{device_name}' no encontrado")

        # Actualizar mappings
        added, removed = self.mapping_repo.bulk_update_user_devices(
            user_id_int,
            devices_to_add,
            devices_to_remove
        )

        # Notificar a las Raspberry Pi
        if removed:
            self._notify_remove_user(user.cedula, removed)

        if added:
            user_info = self._get_user_info_for_iot(user)
            self._notify_add_user(user_info, added)

        return {
            "message": "User device access updated",
            "added": added,
            "removed": removed
        }
