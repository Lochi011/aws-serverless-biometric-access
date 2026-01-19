# handlers/edit_alert_parameters.py
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
    Handler para PUT /configurations/update
    """
    try:
        # Conectar a la BD si está cerrada
        if db.is_closed():
            db.connect()
        
        # Parsear body
        body = event.get('body', '{}')
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Invalid JSON in request body"})
                }
        
        # Extraer parámetros
        max_attempts = body.get('max_denied_attempts')
        window_seconds = body.get('window_seconds')
        
        logger.info(f"Actualizando parámetros de alerta: "
                   f"max_denied_attempts={max_attempts}, "
                   f"window_seconds={window_seconds}")
        
        # Actualizar parámetros
        result = _service.update_alert_parameters(max_attempts, window_seconds)
        
        logger.info(f"Parámetros actualizados exitosamente: {result['updated']}")
        
        # Devolver solo el mensaje para mantener compatibilidad
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": result["message"]})
        }
    
    except ValueError as ve:
        logger.error(f"Error de validación: {ve}")
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(ve)})
        }
    
    except LookupError as le:
        logger.error(f"Configuraciones no encontradas: {le}")
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(le)})
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