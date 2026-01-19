# tests/repositories/test_configuration_repo.py
import pytest
from shared.models import db, Configuration
from repositories.configuration_repo import ConfigurationRepository


@pytest.fixture
def setup_db():
    """Crea las tablas necesarias para los tests"""
    db.connect()
    db.create_tables([Configuration])
    yield
    db.drop_tables([Configuration])
    db.close()


@pytest.fixture
def sample_configs(setup_db):
    """Crea configuraciones de prueba"""
    # Configuraciones globales (device_id = null)
    config1 = Configuration.create(
        id_config=1,
        name_config="max_denied_attempts",
        value="50",
        description="Umbral global de denies",
        device_id=None
    )
    config2 = Configuration.create(
        id_config=2,
        name_config="window_seconds",
        value="90",
        description="Ventana en segundos (10 min)",
        device_id=None
    )
    config3 = Configuration.create(
        id_config=3,
        name_config="other_config",
        value="test_value",
        description="Otra configuración",
        device_id=None
    )
    # Configuración específica de dispositivo (para futuro)
    config4 = Configuration.create(
        id_config=4,
        name_config="max_denied_attempts",
        value="30",
        description="Límite para dispositivo específico",
        device_id="device-1"
    )
    
    return [config1, config2, config3, config4]


def test_get_by_name_global(sample_configs):
    """Test obtener configuración global por nombre"""
    repo = ConfigurationRepository()
    
    config = repo.get_by_name("max_denied_attempts")
    
    assert config is not None
    assert config.value == "50"
    assert config.device_id is None


def test_get_by_name_not_found(sample_configs):
    """Test obtener configuración inexistente"""
    repo = ConfigurationRepository()
    
    config = repo.get_by_name("non_existent_config")
    
    assert config is None


def test_get_by_name_with_device(sample_configs):
    """Test obtener configuración específica de dispositivo"""
    repo = ConfigurationRepository()
    
    # Configuración específica del dispositivo
    config = repo.get_by_name("max_denied_attempts", device_id="device-1")
    
    assert config is not None
    assert config.value == "30"
    assert config.device_id == "device-1"


def test_get_multiple_by_names(sample_configs):
    """Test obtener múltiples configuraciones"""
    repo = ConfigurationRepository()
    
    configs = repo.get_multiple_by_names(["max_denied_attempts", "window_seconds"])
    
    assert len(configs) == 2
    config_dict = {c.name_config: c.value for c in configs}
    assert config_dict["max_denied_attempts"] == "50"
    assert config_dict["window_seconds"] == "90"


def test_get_multiple_by_names_partial(sample_configs):
    """Test obtener configuraciones cuando algunas no existen"""
    repo = ConfigurationRepository()
    
    configs = repo.get_multiple_by_names(
        ["max_denied_attempts", "non_existent", "window_seconds"]
    )
    
    assert len(configs) == 2  # Solo las que existen


def test_get_all_global_configs(sample_configs):
    """Test obtener todas las configuraciones globales"""
    repo = ConfigurationRepository()
    
    configs = repo.get_all_global_configs()
    
    # Solo las 3 configuraciones globales (no la específica del dispositivo)
    assert len(configs) == 3
    names = [c.name_config for c in configs]
    assert "max_denied_attempts" in names
    assert "window_seconds" in names
    assert "other_config" in names


def test_get_value(sample_configs):
    """Test obtener valor directo de una configuración"""
    repo = ConfigurationRepository()
    
    value = repo.get_value("window_seconds")
    
    assert value == "90"


def test_get_value_not_found(sample_configs):
    """Test obtener valor de configuración inexistente"""
    repo = ConfigurationRepository()
    
    value = repo.get_value("non_existent")
    
    assert value is None


def test_update_value(sample_configs):
    """Test actualizar valor de configuración"""
    repo = ConfigurationRepository()
    
    updated = repo.update_value("max_denied_attempts", "100")
    
    assert updated is True
    
    # Verificar que se actualizó
    config = repo.get_by_name("max_denied_attempts")
    assert config.value == "100"


def test_update_value_not_found(sample_configs):
    """Test actualizar configuración inexistente"""
    repo = ConfigurationRepository()
    
    updated = repo.update_value("non_existent", "value")
    
    assert updated is False