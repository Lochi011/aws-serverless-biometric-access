# handlers/get_alert_parameters.py
import json
import logging
from shared.models import db
from services.configuration_service import ConfigurationService
from repositories.configuration_repo import ConfigurationRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Inicializar servicio
_service = ConfigurationService(ConfigurationRepository())


def lambda_handler(event, context):
    """
    Handler para GET /configurations
    """
    try:
        # Conectar a la BD si está cerrada
        if db.is_closed():
            db.connect()
        
        logger.info("Obteniendo parámetros de alerta")
        
        # Por ahora no se usa device_id, pero está preparado para futuro
        # device_id = event.get('queryStringParameters', {}).get('device_id') if event.get('queryStringParameters') else None
        
        # Obtener parámetros de alerta
        alert_params = _service.get_alert_parameters()
        
        logger.info(f"Parámetros obtenidos: {alert_params}")
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(alert_params)
        }
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        logger.exception("Error completo:")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
    
    finally:
        # Cerrar conexión
        if not db.is_closed():
            db.close()