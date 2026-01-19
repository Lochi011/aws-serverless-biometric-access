from typing import List, Dict, Optional
from repositories.device_repo import DeviceRepository


class DeviceService:
    """Servicio para lógica de negocio de dispositivos"""
    
    def __init__(self, device_repo: DeviceRepository):
        self.device_repo = device_repo
    
    def _format_device(self, device) -> Dict:
        """
        Formatea un dispositivo para la respuesta.
        
        Args:
            device: Instancia de Device
            
        Returns:
            Dict con formato de respuesta
        """
        return {
            'id_device': device.id_device,  # Ya es string en la BD
            'location': device.location,
            'status': device.status,
            'last_sync': str(device.last_sync) if device.last_sync else None
        }
    
    def get_device_by_id(self, device_id: str) -> Dict:
        """
        Obtiene un dispositivo por ID.
        
        Args:
            device_id: ID del dispositivo (string desde path parameter)
            
        Returns:
            Dict con datos del dispositivo
            
        Raises:
            ValueError: Si el device_id está vacío
            LookupError: Si el dispositivo no existe
        """
        # Validar que device_id no esté vacío
        if not device_id:
            raise ValueError("ID de dispositivo requerido")
        
        # Buscar dispositivo (ya es string, no necesita conversión)
        device = self.device_repo.get_by_id(device_id)
        
        if not device:
            raise LookupError(f"Dispositivo con ID {device_id} no encontrado")
        
        return self._format_device(device)
    
    def get_all_devices(self) -> List[Dict]:
        """
        Obtiene todos los dispositivos.
        
        Returns:
            Lista de diccionarios con datos de dispositivos
        """
        devices = self.device_repo.get_all()
        
        return [self._format_device(device) for device in devices]
    
    def get_device_by_location(self, location: str) -> Optional[Dict]:
        """
        Obtiene un dispositivo por ubicación.
        
        Args:
            location: Ubicación/nombre del dispositivo
            
        Returns:
            Dict con datos del dispositivo o None si no existe
        """
        device = self.device_repo.get_by_location(location)
        
        if device:
            return self._format_device(device)
        return None