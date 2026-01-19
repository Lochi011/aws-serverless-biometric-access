import os
import json
from handler import lambda_handler


# Define las variables de entorno necesarias para la prueba
os.environ['DB_HOST'] = "tic2db.cg9wwgawg424.us-east-1.rds.amazonaws.com"
os.environ['DB_NAME'] = "postgres"
os.environ['DB_USER'] = "postgres"
os.environ['DB_PASS'] = "postgres"
os.environ['DB_PORT'] = "5432"
os.environ['JWT_SECRET'] = "mi_clave_secreta"

# Crea un evento de prueba que simule la petición de API Gateway
event = {
    "body": json.dumps({
        "email": "juan@example.com",
        "password": "1234"
    })
}

# Contexto vacío (puedes agregar datos si lo necesitas)
context = {}

# Invoca la función Lambda
response = lambda_handler(event, context)
print("Response:", response)
