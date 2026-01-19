# handlers/get_access_users.py
import json
import logging
from shared.models import db
from services.access_users_service import AccessUserService
from repositories.access_user_repo import AccessUserRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Inicializar servicio
_service = AccessUserService(AccessUserRepository())


def lambda_handler(event, context):
    """
    Handler para GET /access_users y GET /access_users/{id}
    """
    try:
        # Conectar a la BD si está cerrada
        if db.is_closed():
            db.connect()
        
        # Extraer path parameter si existe
        user_id = event.get('pathParameters', {}).get('id')
        
        if user_id:
            # GET /access_users/{id}
            logger.info(f"Obteniendo usuario con ID: {user_id}")
            result = _service.get_user_by_id(user_id)
            
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(result)
            }
        else:
            # GET /access_users
            logger.info("Obteniendo todos los usuarios")
            result = _service.get_all_users()
            
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
            "body": json.dumps({"message": str(ve)})
        }
    
    except LookupError as le:
        logger.error(f"Recurso no encontrado: {le}")
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "Usuario no encontrado"})
        }
    
    except Exception as e:
        logger.exception("Error interno del servidor")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "Error interno del servidor"})
        }
    
    finally:
        # Cerrar conexión
        if not db.is_closed():
            db.close()