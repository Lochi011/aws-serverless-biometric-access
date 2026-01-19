import json
import os

from peewee import OperationalError as PeeweeOperationalError
import jwt

from shared.models import db
from repositories.web_user_repo import WebUserRepository
from services.auth_service import AuthService


def lambda_handler(event, context):
    """
    Handler para login:
    1) Verifica que existan las vars de entorno críticas (BD y JWT).
    2) Abre conexión Peewee si está cerrada.
    3) Parsea JSON de event['body'], extrae 'email' y 'password'.
    4) Llama a AuthService.login(...) y maneja errores (400, 401).
    5) Devuelve token o error. Al final, cierra la conexión.
    """

    # 1) Validar variables de entorno
    missing_env = []
    for var in ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT"):
        if os.environ.get(var) is None:
            missing_env.append(var)
    if os.environ.get("JWT_SECRET") is None:
        missing_env.append("JWT_SECRET")

    if missing_env:
        missing_str = ", ".join(missing_env)
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": f"Missing environment variables: {missing_str}"})
        }

    # 2) Leer vars de JWT y preparar el servicio
    jwt_secret = os.environ["JWT_SECRET"]
    jwt_algorithm = os.environ.get("JWT_ALGORITHM", "HS256")
    service = AuthService(
        user_repo=WebUserRepository(),
        jwt_secret=jwt_secret,
        jwt_algorithm=jwt_algorithm
    )

    try:
        # 3) Abrir conexión Peewee si aún está cerrada
        if db.is_closed():
            db.connect()

        # 4) Parsear JSON del body
        body = json.loads(event.get("body", "{}"))
        email = body.get("email")
        password = body.get("password")

        # 5) Delegar la lógica de login al servicio
        try:
            token, user_info = service.login(email, password)
        except ValueError as ve:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": str(ve)})
            }
        except PermissionError as pe:
            return {
                "statusCode": 401,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": str(pe)})
            }

        # 6) Éxito
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "message": "Login successful",
                "token": token,
                "user": user_info
            })
        }

    except PeeweeOperationalError as pee:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": f"Database error: {str(pee)}"})
        }
    except jwt.PyJWTError as jpw:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": f"Error generating token: {str(jpw)}"})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": f"Internal error: {str(e)}"})
        }
    finally:
        # 7) Cerrar conexión Peewee si sigue abierta
        if not db.is_closed():
            db.close()
