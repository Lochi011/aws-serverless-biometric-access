# handlers/delete_access_user.py
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
    Handler para DELETE /access_users/delete/{id}
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

        logger.info(f"Eliminando usuario con ID: {user_id}")

        # Ejecutar eliminación
        result = _service.delete_user(user_id)

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
