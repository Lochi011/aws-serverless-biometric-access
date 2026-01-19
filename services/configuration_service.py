# services/configuration_service.py
from typing import Dict, Optional, Any
from repositories.configuration_repo import ConfigurationRepository


class ConfigurationService:
    """Servicio para lógica de negocio de configuraciones"""
    
    def __init__(self, config_repo: ConfigurationRepository):
        self.config_repo = config_repo
    
    def get_alert_parameters(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene los parámetros de alerta.
        
        Args:
            device_id: ID del dispositivo (opcional, para futuro uso)
            
        Returns:
            Dict con los parámetros de alerta
        """
        # Nombres de las configuraciones que necesitamos
        config_names = ['max_denied_attempts', 'window_seconds']
        
        # Obtener las configuraciones
        configs = self.config_repo.get_multiple_by_names(config_names, device_id)
        
        # Convertir a diccionario con conversión de tipos
        result = {}
        for config in configs:
            try:
                # Intentar convertir a entero
                result[config.name_config] = int(config.value)
            except (ValueError, TypeError):
                # Si no se puede convertir, dejar como string
                result[config.name_config] = config.value
        
        # Asegurar que todas las claves estén presentes (None si no existen)
        return {
            'max_denied_attempts': result.get('max_denied_attempts', None),
            'window_seconds': result.get('window_seconds', None)
        }
    
    def get_all_configurations(self, device_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Obtiene todas las configuraciones disponibles.
        
        Args:
            device_id: ID del dispositivo (opcional)
            
        Returns:
            Dict con todas las configuraciones y sus metadatos
        """
        if device_id:
            # Para futuro: obtener configuraciones específicas del dispositivo
            configs = self.config_repo.get_multiple_by_names([], device_id)
        else:
            # Configuraciones globales
            configs = self.config_repo.get_all_global_configs()
        
        result = {}
        for config in configs:
            # Intentar convertir el valor al tipo apropiado
            try:
                value = int(config.value)
            except ValueError:
                try:
                    value = float(config.value)
                except ValueError:
                    value = config.value  # Mantener como string
            
            result[config.name_config] = {
                'value': value,
                'description': config.description,
                'device_id': config.device_id
            }
        
        return result
    
    def update_alert_parameters(
        self,
        max_denied_attempts: int,
        window_seconds: int,
        device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Actualiza los parámetros de alerta.
        
        Args:
            max_denied_attempts: Número máximo de intentos denegados
            window_seconds: Ventana de tiempo en segundos
            device_id: ID del dispositivo (opcional, para futuro uso)
            
        Returns:
            Dict con el resultado de la operación
            
        Raises:
            ValueError: Si los parámetros no son válidos
        """
        # Validaciones básicas
        if max_denied_attempts is None or window_seconds is None:
            raise ValueError("Both max_denied_attempts and window_seconds are required.")
        
        # Validar tipos
        try:
            max_attempts_int = int(max_denied_attempts)
            window_seconds_int = int(window_seconds)
        except (ValueError, TypeError):
            raise ValueError("Parameters must be valid integers")
        
        # Validar rangos razonables
        if max_attempts_int < 1:
            raise ValueError("max_denied_attempts must be at least 1")
        
        if max_attempts_int > 1000:
            raise ValueError("max_denied_attempts cannot exceed 1000")
        
        if window_seconds_int < 30:
            raise ValueError("window_seconds must be at least 30 seconds")
        
        if window_seconds_int > 86400:  # 24 horas
            raise ValueError("window_seconds cannot exceed 86400 (24 hours)")
        
        # Actualizar ambos valores
        updated_count = 0
        
        # Actualizar max_denied_attempts
        if self.config_repo.update_value(
            "max_denied_attempts", 
            str(max_attempts_int), 
            device_id
        ):
            updated_count += 1
        
        # Actualizar window_seconds
        if self.config_repo.update_value(
            "window_seconds", 
            str(window_seconds_int), 
            device_id
        ):
            updated_count += 1
        
        if updated_count == 0:
            raise LookupError("No configurations were found to update")
        
        if updated_count < 2:
            # Solo se actualizó uno, puede ser un problema
            raise Exception("Only partial update was successful")
        
        return {
            "message": "Alert parameters updated successfully.",
            "updated": {
                "max_denied_attempts": max_attempts_int,
                "window_seconds": window_seconds_int
            }
        }
    
    def validate_and_update_configurations(
        self,
        configurations: Dict[str, Any],
        device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Valida y actualiza múltiples configuraciones.
        Método genérico para futuras extensiones.
        
        Args:
            configurations: Dict con nombre_config: valor
            device_id: ID del dispositivo (opcional)
            
        Returns:
            Dict con resultados de la actualización
        """
        updated = {}
        errors = {}
        
        for config_name, value in configurations.items():
            try:
                # Aquí se pueden agregar validaciones específicas por configuración
                if self.config_repo.update_value(config_name, str(value), device_id):
                    updated[config_name] = value
                else:
                    errors[config_name] = "Configuration not found"
            except Exception as e:
                errors[config_name] = str(e)
        
        if errors and not updated:
            raise ValueError(f"Failed to update configurations: {errors}")
        
        return {
            "message": "Configurations updated",
            "updated": updated,
            "errors": errors if errors else None
        }