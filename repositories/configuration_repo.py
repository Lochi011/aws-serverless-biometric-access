# repositories/configuration_repo.py
from typing import Dict, List, Optional
from peewee import DoesNotExist
from shared.models import Configuration


class ConfigurationRepository:
    """Repositorio para operaciones con Configuration usando Peewee ORM"""
    
    def get_by_name(self, name: str, device_id: Optional[str] = None) -> Optional[Configuration]:
        """
        Obtiene una configuración por nombre.
        
        Args:
            name: Nombre de la configuración
            device_id: ID del dispositivo (opcional, para futuro uso)
            
        Returns:
            Configuration o None si no existe
        """
        try:
            query = Configuration.select().where(Configuration.name_config == name)
            
            # Para futuro: filtrar por device_id
            if device_id is not None:
                query = query.where(Configuration.device_id == device_id)
            else:
                # Por ahora, solo configuraciones globales (device_id es null)
                query = query.where(Configuration.device_id.is_null())
            
            return query.get()
        except DoesNotExist:
            return None
    
    def get_multiple_by_names(
        self, 
        names: List[str], 
        device_id: Optional[str] = None
    ) -> List[Configuration]:
        """
        Obtiene múltiples configuraciones por sus nombres.
        
        Args:
            names: Lista de nombres de configuración
            device_id: ID del dispositivo (opcional, para futuro uso)
            
        Returns:
            Lista de Configuration
        """
        query = Configuration.select().where(Configuration.name_config.in_(names))
        
        if device_id is not None:
            query = query.where(Configuration.device_id == device_id)
        else:
            # Por ahora, solo configuraciones globales
            query = query.where(Configuration.device_id.is_null())
        
        return list(query)
    
    def get_all_global_configs(self) -> List[Configuration]:
        """
        Obtiene todas las configuraciones globales.
        
        Returns:
            Lista de configuraciones donde device_id es null
        """
        return list(
            Configuration
            .select()
            .where(Configuration.device_id.is_null())
            .order_by(Configuration.name_config)
        )
    
    def get_value(self, name: str, device_id: Optional[str] = None) -> Optional[str]:
        """
        Obtiene el valor de una configuración específica.
        
        Args:
            name: Nombre de la configuración
            device_id: ID del dispositivo (opcional)
            
        Returns:
            Valor como string o None si no existe
        """
        config = self.get_by_name(name, device_id)
        return config.value if config else None
    
    def update_value(
        self, 
        name: str, 
        value: str, 
        device_id: Optional[str] = None
    ) -> bool:
        """
        Actualiza el valor de una configuración.
        
        Args:
            name: Nombre de la configuración
            value: Nuevo valor
            device_id: ID del dispositivo (opcional)
            
        Returns:
            True si se actualizó, False si no existe
        """
        query = Configuration.update(value=value).where(
            Configuration.name_config == name
        )
        
        if device_id is not None:
            query = query.where(Configuration.device_id == device_id)
        else:
            query = query.where(Configuration.device_id.is_null())
        
        updated = query.execute()
        return updated > 0