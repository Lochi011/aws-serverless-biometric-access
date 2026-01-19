# handlers/get_devices.py
import json
import logging
from shared.models import db
from services.device_service import DeviceService
from repositories.device_repo import DeviceRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Inicializar servicio
_service = DeviceService(DeviceRepository())


def lambda_handler(event, context):
    """
    Handler para GET /devices y GET /devices/{id}
    """
    logger.info("Evento recibido: %s", json.dumps(event))
    
    try:
        # Conectar a la BD si está cerrada
        if db.is_closed():
            db.connect()
        
        # Extraer device_id del path si existe
        device_id = event.get('pathParameters', {}).get('id')
        
        if device_id:
            # GET /devices/{id}
            logger.info(f"Obteniendo dispositivo con ID: {device_id}")
            result = _service.get_device_by_id(device_id)
            
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(result)
            }
        else:
            # GET /devices
            logger.info("Obteniendo todos los dispositivos")
            result = _service.get_all_devices()
            
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(result)
            }
    
    except ValueError as ve:
        logger.error(f"Error de validación: {ve}")
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(ve)})
        }
    
    except LookupError as le:
        logger.error(f"Dispositivo no encontrado: {le}")
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Device not found"})
        }
    
    except Exception as e:
        logger.error(f"Error en la Lambda: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "Internal server error",
                "details": str(e)
            })
        }
    
    finally:
        # Cerrar conexión
        if not db.is_closed():
            db.close()