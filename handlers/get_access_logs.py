# handlers/get_access_logs.py
import json
import logging
from shared.models import db
from services.access_log_service import AccessLogService
from repositories.access_log_repo import AccessLogRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Inicializar servicio
_service = AccessLogService(AccessLogRepository())


def lambda_handler(event, context):
    """
    Handler para GET /access_logs con filtros opcionales
    """
    try:
        # Conectar a la BD si está cerrada
        if db.is_closed():
            db.connect()
        
        # Extraer query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        user_id = query_params.get('user_id')
        device_id = query_params.get('device_id')
        
        logger.info(f"Obteniendo logs con filtros: user_id={user_id}, device_id={device_id}")
        
        # Obtener logs
        logs = _service.get_logs(user_id=user_id, device_id=device_id)
        
        logger.info(f"Se encontraron {len(logs)} logs")
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(logs)
        }
    
    except ValueError as ve:
        logger.error(f"Error de validación: {ve}")
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(ve)})
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