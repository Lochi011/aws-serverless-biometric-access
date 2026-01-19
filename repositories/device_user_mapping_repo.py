# repositories/device_user_mapping_repo.py
from typing import List, Tuple
from peewee import IntegrityError
from shared.models import DeviceUserMapping, Device, AccessUser, db


class DeviceUserMappingRepository:
    """Repositorio para operaciones con DeviceUserMapping usando Peewee ORM"""
    
    def add_device_access(self, user_id: int, device_id: str) -> bool:
        """
        Agrega acceso de un usuario a un dispositivo.
        
        Args:
            user_id: ID del usuario
            device_id: ID del dispositivo (string)
            
        Returns:
            True si se agregó, False si ya existía
        """
        try:
            DeviceUserMapping.create(
                access_user_id=user_id,
                device_id=device_id
            )
            return True
        except IntegrityError:
            # Ya existe el mapping (ON CONFLICT DO NOTHING)
            return False
    
    def remove_device_access(self, user_id: int, device_id: str) -> int:
        """
        Elimina acceso de un usuario a un dispositivo.
        
        Args:
            user_id: ID del usuario
            device_id: ID del dispositivo (string)
            
        Returns:
            Número de registros eliminados (0 o 1)
        """
        deleted = (DeviceUserMapping
                  .delete()
                  .where(
                      (DeviceUserMapping.access_user_id == user_id) &
                      (DeviceUserMapping.device_id == device_id)
                  )
                  .execute())
        return deleted
    
    def get_user_devices(self, user_id: int) -> List[Device]:
        """
        Obtiene todos los dispositivos a los que tiene acceso un usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Lista de dispositivos
        """
        devices = (Device
                  .select()
                  .join(DeviceUserMapping, on=(Device.id_device == DeviceUserMapping.device_id))
                  .where(DeviceUserMapping.access_user_id == user_id))
        
        return list(devices)
    
    def bulk_update_user_devices(
        self, 
        user_id: int, 
        devices_to_add: List[Tuple[str, str]], 
        devices_to_remove: List[Tuple[str, str]]
    ) -> Tuple[List[str], List[str]]:
        """
        Actualiza múltiples accesos de dispositivos en una transacción.
        
        Args:
            user_id: ID del usuario
            devices_to_add: Lista de tuplas (device_id, device_name)
            devices_to_remove: Lista de tuplas (device_id, device_name)
            
        Returns:
            Tupla con (dispositivos agregados, dispositivos eliminados)
        """
        added = []
        removed = []
        
        with db.atomic():
            # Eliminar accesos
            for device_id, device_name in devices_to_remove:
                count = self.remove_device_access(user_id, device_id)
                if count > 0:
                    removed.append(device_name)
            
            # Agregar accesos
            for device_id, device_name in devices_to_add:
                if self.add_device_access(user_id, device_id):
                    added.append(device_name)
        
        return added, removed