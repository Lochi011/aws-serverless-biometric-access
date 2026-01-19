import json
import uuid
import logging
import urllib.parse
from db import get_db_connection

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        logger.info("Evento recibido: %s", json.dumps(event))

        # Get location from path parameters
        path_parameters = event.get('pathParameters', {})
        location = path_parameters.get('location')
        
        if location:
            # Decode the URL-encoded location
            location = urllib.parse.unquote(location)
        else:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Falta el parámetro 'location' en la URL"})
            }

        conn = get_db_connection()
        cur = conn.cursor()

        # Verificar que no exista una raspi con la misma location
        cur.execute("SELECT 1 FROM devices WHERE location = %s", (location,))
        if cur.fetchone():
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Ya existe un dispositivo con location '{location}'"})
            }

        # Generar nuevo id que no exista
        while True:
            new_id = str(uuid.uuid4())
            cur.execute("SELECT 1 FROM devices WHERE id_device = %s", (new_id,))
            if not cur.fetchone():
                break

        # Insertar nuevo dispositivo
        cur.execute("""
            INSERT INTO devices (id_device, location, status, last_sync)
            VALUES (%s, %s, %s, %s)
        """, (new_id, location, 'active', None))

        conn.commit()
        cur.close()
        conn.close()

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Dispositivo creado exitosamente",
                "id_device": new_id,
                "location": location,
                "status": "active",
                "last_sync": None
            })
        }

    except Exception as e:
        logger.error("Error al agregar dispositivo: %s", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
