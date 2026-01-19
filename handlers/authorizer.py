import os
from services.authorizer_service import AuthorizerService

# ←— Lectura de variables de entorno a nivel módulo (solo se ejecuta al importar el archivo)
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")

# ←— Instancia única del servicio, inyectando las variables desde entorno
service = AuthorizerService(secret=JWT_SECRET, algorithm=JWT_ALGORITHM)


def generate_policy(is_allowed, route_arn):
    """
    Genera la respuesta que espera API Gateway Custom Authorizer:
    { "isAuthorized": True } o { "isAuthorized": False }.
    """
    return {"isAuthorized": is_allowed}


def lambda_handler(event, context):
    """
    Handler para el custom authorizer. Espera un header:
        "authorization": "Bearer <token>"
    Si el token es válido según AuthorizerService, devuelve isAuthorized=True.
    """
    auth_header = event.get("headers", {}).get("authorization", "")
    parts = auth_header.split()

    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = parts[1]
        if service.is_token_valid(token):
            return generate_policy(True, event["routeArn"])

    return generate_policy(False, event["routeArn"])
