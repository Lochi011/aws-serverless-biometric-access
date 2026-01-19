# services/access_log_service.py
from typing import List, Dict, Optional
from repositories.access_log_repo import AccessLogRepository


class AccessLogService:
    """Servicio para lógica de negocio de logs de acceso"""
    
    def __init__(self, access_log_repo: AccessLogRepository):
        self.access_log_repo = access_log_repo
    
    def _format_log(self, log) -> Dict:
        """
        Formatea un log para la respuesta, incluyendo datos de usuario y dispositivo.
        
        Args:
            log: Instancia de AccessLog con relaciones cargadas
            
        Returns:
            Dict con formato de respuesta
        """
        # Construir objeto user
        user_data = None
        if log.access_user_id is not None and hasattr(log, 'access_user') and log.access_user:
            # Usuario reconocido con datos
            user_data = {
                'first_name': log.access_user.first_name,
                'last_name': log.access_user.last_name,
                'image_ref': log.access_user.image_ref
            }
        else:
            # Usuario no reconocido o sin datos
            user_data = {
                'first_name': None,
                'last_name': None,
                'image_ref': None
            }
        
        # Obtener location del device
        device_location = None
        if hasattr(log, 'device') and log.device:
            device_location = log.device.location
        
        return {
            'id': str(log.id),  # Convertir UUID a string
            'access_user_id': log.access_user_id,  # Puede ser None
            'user': user_data,  # Siempre incluir objeto user aunque sea con nulls
            'device_id': log.device_id,
            'device_location': device_location,
            'event': log.event,
            'timestamp': log.timestamp.isoformat() if log.timestamp else None
        }
    
    def get_logs(
        self, 
        user_id: Optional[str] = None, 
        device_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Obtiene logs con filtros opcionales.
        
        Args:
            user_id: ID del usuario para filtrar (string desde query params)
            device_id: ID del dispositivo para filtrar (string desde query params)
            
        Returns:
            Lista de logs formateados
            
        Raises:
            ValueError: Si los parámetros no son válidos
        """
        # Validar y convertir user_id si existe
        user_id_int = None
        if user_id:
            try:
                user_id_int = int(user_id)
            except (ValueError, TypeError):
                raise ValueError("user_id debe ser un número válido")
        
        # device_id ya es string, no necesita conversión
        
        # Obtener logs con filtros
        logs = self.access_log_repo.get_logs_with_filters(
            user_id=user_id_int,
            device_id=device_id,
            limit=100
        )
        
        # Formatear y retornar
        return [self._format_log(log) for log in logs]
    
    def get_logs_count(
        self,
        user_id: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> int:
        """
        Obtiene el conteo de logs según filtros.
        
        Args:
            user_id: ID del usuario para filtrar
            device_id: ID del dispositivo para filtrar
            
        Returns:
            Número de logs
        """
        user_id_int = None
        if user_id:
            try:
                user_id_int = int(user_id)
            except (ValueError, TypeError):
                raise ValueError("user_id debe ser un número válido")
        
        return self.access_log_repo.count_by_filters(
            user_id=user_id_int,
            device_id=device_id
        )