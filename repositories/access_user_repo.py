# repositories/access_user_repo.py
from typing import List, Optional
from peewee import prefetch, DoesNotExist
from shared.models import AccessUser, Device, DeviceUserMapping
import boto3
import os
from urllib.parse import urlparse
from peewee import fn
from shared.models import db, AccessLog, DeviceUserMapping


class AccessUserRepository:
    """Repositorio para operaciones con AccessUser usando Peewee ORM"""

    def exists(self, cedula: str) -> bool:
        """Verifica si existe un usuario por cédula"""
        return AccessUser.select().where(AccessUser.cedula == cedula).exists()

    def create(self, **kwargs) -> AccessUser:
        """Crea un nuevo usuario"""
        return AccessUser.create(**kwargs)

    def get_by_cedula(self, cedula: str) -> AccessUser:
        """Obtiene un usuario por cédula"""
        return AccessUser.get(AccessUser.cedula == cedula)

    def get_id_by_cedula(self, cedula: str) -> Optional[int]:
        """
        Devuelve el ID del usuario con la cédula dada,
        o None si no existe.
        """
        row = (
            AccessUser
            .select(AccessUser.id)
            .where(AccessUser.cedula == cedula)
            .first()
        )
        return row.id if row else None

    def get_by_id(self, user_id: int) -> Optional[AccessUser]:
        """Obtiene un usuario por ID"""
        try:
            return AccessUser.get_by_id(user_id)
        except DoesNotExist:
            return None

    def exists_rfid(self, rfid: str) -> bool:
        """Devuelve True si ya hay un usuario con ese RFID."""
        return AccessUser.select().where(AccessUser.rfid == rfid).exists()

    def get_by_id_with_devices(self, user_id: int) -> Optional[AccessUser]:
        """
        Obtiene un usuario por ID con sus dispositivos asociados.
        """
        try:
            user = AccessUser.get_by_id(user_id)

            # Obtener mappings con join manual
            mappings = list(
                DeviceUserMapping
                .select(DeviceUserMapping, Device)
                .join(Device, on=(DeviceUserMapping.device_id == Device.id_device))
                .where(DeviceUserMapping.access_user_id == user_id)
            )

            # Crear estructura similar a la esperada por el servicio
            user._mappings = []
            for mapping in mappings:
                # Crear un objeto mock que tenga la estructura esperada
                class MappingWithDevice:
                    def __init__(self, device):
                        self.device = device

                user._mappings.append(MappingWithDevice(mapping.device))

            return user

        except DoesNotExist:
            return None

    def get_all_with_devices(self) -> List[AccessUser]:
        """
        Obtiene todos los usuarios con sus dispositivos asociados.
        """
        # Obtener todos los usuarios
        users = list(AccessUser.select().order_by(AccessUser.id))

        if not users:
            return []

        # Obtener IDs de usuarios
        user_ids = [u.id for u in users]

        # Obtener todos los mappings con devices en una sola consulta
        mappings = list(
            DeviceUserMapping
            .select(DeviceUserMapping, Device)
            .join(Device, on=(DeviceUserMapping.device_id == Device.id_device))
            .where(DeviceUserMapping.access_user_id.in_(user_ids))
        )

        # Crear diccionario para agrupar devices por usuario
        user_devices = {}
        for mapping in mappings:
            if mapping.access_user_id not in user_devices:
                user_devices[mapping.access_user_id] = []

            # Crear objeto mock con estructura esperada
            class MappingWithDevice:
                def __init__(self, device):
                    self.device = device

            user_devices[mapping.access_user_id].append(
                MappingWithDevice(mapping.device))

        # Asignar devices a cada usuario
        for user in users:
            user._mappings = user_devices.get(user.id, [])

        return users

    def get_user_with_image(self, user_id: int):
        """
        Obtiene un usuario con su cédula e imagen.

        Returns:
            AccessUser o None
        """
        try:
            return AccessUser.select().where(AccessUser.id == user_id).get()
        except DoesNotExist:
            return None

    def get_user_devices_locations(self, user_id: int) -> List[str]:
        """
        Obtiene las ubicaciones de los dispositivos asociados a un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            Lista de nombres/ubicaciones de dispositivos
        """
        # Join manual especificando la condición exacta
        mappings = (DeviceUserMapping
                    .select(DeviceUserMapping, Device)
                    .join(Device, on=(DeviceUserMapping.device_id == Device.id_device))
                    .where(DeviceUserMapping.access_user_id == user_id))

        return [mapping.device.location for mapping in mappings]

    def delete_user_and_related_data(self, user_id: int) -> bool:
        """
        Elimina un usuario y todos sus datos relacionados en una transacción.

        Args:
            user_id: ID del usuario a eliminar

        Returns:
            True si se eliminó correctamente, False si no existe

        Raises:
            Exception: Si hay error en la transacción
        """
        with db.atomic() as transaction:
            try:
                # Verificar que el usuario existe
                user = AccessUser.get_by_id(user_id)

                # Eliminar logs de acceso
                AccessLog.delete().where(AccessLog.access_user_id == user_id).execute()

                # Eliminar mappings de dispositivos
                DeviceUserMapping.delete().where(
                    DeviceUserMapping.access_user_id == user_id).execute()

                # Eliminar el usuario
                user.delete_instance()

                return True

            except DoesNotExist:
                transaction.rollback()
                return False
            except Exception as e:
                transaction.rollback()
                raise e
