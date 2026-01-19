# handlers/edit_allowed_devices.py
import json
import logging
from shared.models import db
from services.device_access_service import DeviceAccessService
from repositories.access_user_repo import AccessUserRepository
from repositories.device_repo import DeviceRepository
from repositories.device_user_mapping_repo import DeviceUserMappingRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Inicializar servicio
_service = DeviceAccessService(
    AccessUserRepository(),
    DeviceRepository(),
    DeviceUserMappingRepository()
)


def lambda_handler(event, context):
    """
    Handler para PUT /edit-user-allowed-devices/{id}
    """
    try:
        # Conectar a la BD si está cerrada
        if db.is_closed():
            db.connect()
        
        # Extraer user_id del path
        user_id = event.get('pathParameters', {}).get('id')
        
        if not user_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "User ID is required"})
            }
        
        # Parsear body
        body = event.get('body', event)
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Invalid JSON in request body"})
                }
        
        # Extraer listas de dispositivos
        add_devices = body.get('addDevices', [])
        remove_devices = body.get('removeDevices', [])
        
        logger.info(f"Actualizando accesos para usuario {user_id}: "
                   f"agregar={add_devices}, eliminar={remove_devices}")
        
        # Ejecutar actualización
        result = _service.update_user_device_access(
            user_id,
            add_devices,
            remove_devices
        )
        
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
        logger.error(f"Usuario no encontrado: {le}")
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "User not found"})
        }
    
    except Exception as e:
        logger.exception("Error interno del servidor")
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