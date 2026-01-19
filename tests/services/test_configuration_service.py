# tests/services/test_configuration_service.py
import pytest
from services.configuration_service import ConfigurationService
from repositories.configuration_repo import ConfigurationRepository


class MockConfiguration:
    """Mock de Configuration"""
    def __init__(self, id_config, name_config, value, description=None):
        self.id_config = id_config
        self.name_config = name_config
        self.value = value
        self.description = description
        self.device_id = None  # Siempre None porque son configuraciones globales


class MockConfigurationRepository:
    """Mock del repositorio para configuraciones globales"""
    def __init__(self, configs=None):
        self.configs = configs or []
        self.updated_values = {}  # Para trackear actualizaciones
        self.existing_configs = {c.name_config: c.value for c in self.configs}  # Configuraciones existentes
        self.should_fail = False  # Para simular fallos
    
    def get_multiple_by_names(self, names, device_id=None):
        """Obtiene configuraciones por nombres (ignora device_id porque son globales)"""
        return [c for c in self.configs if c.name_config in names]
    
    def get_all_global_configs(self):
        """Obtiene todas las configuraciones (todas son globales)"""
        return self.configs
    
    def update_value(self, name, value, device_id=None):
        """
        Actualiza el valor de una configuración.
        Ignora device_id porque son configuraciones globales.
        """
        if self.should_fail:
            return False
        
        if name in self.existing_configs:
            self.updated_values[name] = value
            return True
        return False


@pytest.fixture
def mock_configs():
    """Fixture con configuraciones de prueba"""
    return [
        MockConfiguration(1, "max_denied_attempts", "50", "Umbral global"),
        MockConfiguration(2, "window_seconds", "90", "Ventana de tiempo"),
        MockConfiguration(3, "other_config", "test", "Otra configuración"),
        MockConfiguration(4, "invalid_number", "not_a_number", "Número inválido")
    ]


def test_get_alert_parameters_success(mock_configs):
    """Test obtener parámetros de alerta exitoso"""
    repo = MockConfigurationRepository(mock_configs)
    service = ConfigurationService(repo)
    
    result = service.get_alert_parameters()
    
    assert result['max_denied_attempts'] == 50
    assert result['window_seconds'] == 90


def test_get_alert_parameters_missing_config(mock_configs):
    """Test cuando falta alguna configuración"""
    # Solo incluir max_denied_attempts
    partial_configs = [mock_configs[0]]
    repo = MockConfigurationRepository(partial_configs)
    service = ConfigurationService(repo)
    
    result = service.get_alert_parameters()
    
    assert result['max_denied_attempts'] == 50
    assert result['window_seconds'] is None


def test_get_alert_parameters_empty():
    """Test cuando no hay configuraciones"""
    repo = MockConfigurationRepository([])
    service = ConfigurationService(repo)
    
    result = service.get_alert_parameters()
    
    assert result['max_denied_attempts'] is None
    assert result['window_seconds'] is None


def test_get_alert_parameters_non_numeric_value():
    """Test cuando el valor no es numérico"""
    configs = [
        MockConfiguration(1, "max_denied_attempts", "not_a_number"),
        MockConfiguration(2, "window_seconds", "90")
    ]
    repo = MockConfigurationRepository(configs)
    service = ConfigurationService(repo)
    
    result = service.get_alert_parameters()
    
    assert result['max_denied_attempts'] == "not_a_number"  # Se mantiene como string
    assert result['window_seconds'] == 90


def test_get_all_configurations(mock_configs):
    """Test obtener todas las configuraciones"""
    repo = MockConfigurationRepository(mock_configs)
    service = ConfigurationService(repo)
    
    result = service.get_all_configurations()
    
    assert len(result) == 4
    assert result['max_denied_attempts']['value'] == 50
    assert result['max_denied_attempts']['description'] == "Umbral global"
    assert result['window_seconds']['value'] == 90
    assert result['other_config']['value'] == "test"
    assert result['invalid_number']['value'] == "not_a_number"  # No se pudo convertir


def test_get_all_configurations_with_float():
    """Test conversión de valores float"""
    configs = [
        MockConfiguration(1, "threshold", "3.14"),
        MockConfiguration(2, "percentage", "99.9")
    ]
    repo = MockConfigurationRepository(configs)
    service = ConfigurationService(repo)
    
    result = service.get_all_configurations()
    
    assert result['threshold']['value'] == 3.14
    assert result['percentage']['value'] == 99.9


def test_update_alert_parameters_success():
    """Test actualización exitosa de parámetros"""
    # Configurar repo con configuraciones existentes
    configs = [
        MockConfiguration(1, "max_denied_attempts", "50"),
        MockConfiguration(2, "window_seconds", "90")
    ]
    repo = MockConfigurationRepository(configs)
    service = ConfigurationService(repo)
    
    result = service.update_alert_parameters(10, 300)
    
    assert result['message'] == "Alert parameters updated successfully."
    assert result['updated']['max_denied_attempts'] == 10
    assert result['updated']['window_seconds'] == 300
    
    # Verificar que se actualizaron en el repo
    assert repo.updated_values['max_denied_attempts'] == "10"
    assert repo.updated_values['window_seconds'] == "300"


def test_update_alert_parameters_missing_params():
    """Test con parámetros faltantes"""
    repo = MockConfigurationRepository()
    service = ConfigurationService(repo)
    
    with pytest.raises(ValueError, match="Both max_denied_attempts and window_seconds are required"):
        service.update_alert_parameters(None, 300)
    
    with pytest.raises(ValueError, match="Both max_denied_attempts and window_seconds are required"):
        service.update_alert_parameters(10, None)


def test_update_alert_parameters_invalid_types():
    """Test con tipos inválidos"""
    repo = MockConfigurationRepository()
    service = ConfigurationService(repo)
    
    with pytest.raises(ValueError, match="Parameters must be valid integers"):
        service.update_alert_parameters("not_a_number", 300)
    
    with pytest.raises(ValueError, match="Parameters must be valid integers"):
        service.update_alert_parameters(10, "invalid")


def test_update_alert_parameters_config_not_found():
    """Test cuando las configuraciones no existen"""
    repo = MockConfigurationRepository([])  # Repo vacío
    repo.should_fail = True  # Simular fallo
    service = ConfigurationService(repo)
    
    with pytest.raises(LookupError, match="No configurations were found to update"):
        service.update_alert_parameters(10, 300)


def test_update_alert_parameters_partial_update():
    """Test cuando solo se actualiza una configuración"""
    # Solo incluir una configuración
    configs = [MockConfiguration(1, "max_denied_attempts", "50")]
    repo = MockConfigurationRepository(configs)
    service = ConfigurationService(repo)
    
    with pytest.raises(Exception, match="Only partial update was successful"):
        service.update_alert_parameters(10, 300)


def test_update_alert_parameters_string_numbers():
    """Test con números como strings (deben convertirse)"""
    configs = [
        MockConfiguration(1, "max_denied_attempts", "50"),
        MockConfiguration(2, "window_seconds", "90")
    ]
    repo = MockConfigurationRepository(configs)
    service = ConfigurationService(repo)
    
    result = service.update_alert_parameters("15", "600")
    
    assert result['updated']['max_denied_attempts'] == 15
    assert result['updated']['window_seconds'] == 600


def test_validate_and_update_configurations_success():
    """Test actualización genérica de configuraciones"""
    configs = [
        MockConfiguration(1, "config1", "value1"),
        MockConfiguration(2, "config2", "value2")
    ]
    repo = MockConfigurationRepository(configs)
    service = ConfigurationService(repo)
    
    result = service.validate_and_update_configurations({
        "config1": "new_value1",
        "config2": "new_value2"
    })
    
    assert result['message'] == "Configurations updated"
    assert result['updated']['config1'] == "new_value1"
    assert result['updated']['config2'] == "new_value2"
    assert result['errors'] is None


def test_validate_and_update_configurations_partial():
    """Test actualización parcial con errores"""
    configs = [MockConfiguration(1, "config1", "value1")]
    repo = MockConfigurationRepository(configs)
    service = ConfigurationService(repo)
    
    result = service.validate_and_update_configurations({
        "config1": "new_value1",
        "config_not_exists": "value"
    })
    
    assert result['updated']['config1'] == "new_value1"
    assert result['errors']['config_not_exists'] == "Configuration not found"