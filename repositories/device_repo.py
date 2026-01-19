from typing import List, Optional, Union
from peewee import DoesNotExist
from shared.models import Device


class DeviceRepository:
    """Repositorio para operaciones con Device usando Peewee ORM"""
    
    def exists(self, location: str) -> bool:
        """Verifica si existe un dispositivo por ubicación"""
        return Device.select().where(Device.location == location).exists()
    
    def create(self, **kwargs) -> Device:
        """Crea un nuevo dispositivo"""
        return Device.create(**kwargs)
    
    def get_by_location(self, location: str) -> Optional[Device]:
        """Obtiene un dispositivo por ubicación"""
        try:
            return Device.get(Device.location == location)
        except DoesNotExist:
            return None
    
    def get_id_by_location(self, location: str) -> Optional[str]:
        """
        Obtiene el ID de un dispositivo por ubicación.
        Mantiene compatibilidad con código existente.
        Nota: Devuelve string porque id_device es VARCHAR en la BD.
        """
        device = self.get_by_location(location)
        return device.id_device if device else None
    
    def get_by_id(self, device_id: Union[int, str]) -> Optional[Device]:
        """
        Obtiene un dispositivo por ID.
        Acepta int o string porque id_device es VARCHAR en la BD.
        """
        try:
            # Convertir a string para la comparación
            return Device.get(Device.id_device == str(device_id))
        except DoesNotExist:
            return None
    
    def get_all(self) -> List[Device]:
        """Obtiene todos los dispositivos ordenados por ID"""
        return list(Device.select().order_by(Device.id_device))
    
    def update_status(self, device_id: Union[int, str], status: str) -> bool:
        """
        Actualiza el estado de un dispositivo.
        
        Args:
            device_id: ID del dispositivo (int o string)
            status: Nuevo estado
            
        Returns:
            True si se actualizó, False si no existe
        """
        updated = (Device
                  .update(status=status)
                  .where(Device.id_device == str(device_id))
                  .execute())
        return updated > 0
    
    def update_last_sync(self, device_id: Union[int, str], timestamp) -> bool:
        """
        Actualiza la última sincronización de un dispositivo.
        
        Args:
            device_id: ID del dispositivo (int o string)
            timestamp: Timestamp de la última sincronización
            
        Returns:
            True si se actualizó, False si no existe
        """
        updated = (Device
                  .update(last_sync=timestamp)
                  .where(Device.id_device == str(device_id))
                  .execute())
        return updated > 0