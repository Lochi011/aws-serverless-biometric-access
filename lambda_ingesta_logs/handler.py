import json
import os
import boto3
import logging
from datetime import datetime
from db import get_db_connection

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# inicializa cliente de EventBridge al nivel de módulo
EVENT_BUS = os.environ.get('EVENT_BUS_NAME', 'default')
eb = boto3.client('events')


def lambda_handler(event, context):
    try:
        logger.info("Evento recibido: %s", json.dumps(event))
        payload = event  # Evento viene directo desde IoT Core

        # ──────────────────────────────
        # 1. Extraer campos
        # ──────────────────────────────
        payload = event                      # mensaje IoT Core
        uuid = payload["uuid"]
        raw_id = payload.get("access_user_id", "")      # puede venir ""
        device_name = payload["device_name"]
        event_type = payload["event"]
        timestamp = payload["timestamp"]

        # Validar event_type
        if event_type not in ['accepted', 'denied']:
            raise ValueError(
                f"Tipo de evento inválido: {event_type}. Debe ser 'accepted' o 'denied'.")

        # Validar timestamp
        try:
            # Esto lanza excepción si la fecha es inválida
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except Exception:
            raise ValueError(
                f"Formato de fecha inválido: {timestamp}. Debe ser ISO 8601.")

        # Convertir "UNKNOWN" en cadena vacía → luego se insertará NULL
        cedula = "" if raw_id.upper() == "UNKNOWN" else raw_id

        # ──────────────────────────────
        # 3. Preparar DB
        # ──────────────────────────────
        conn = get_db_connection()
        cur = conn.cursor()

        # UUID duplicado
        cur.execute("SELECT 1 FROM access_logs WHERE id = %s", (uuid,))
        if cur.fetchone():
            raise ValueError(f"Ya existe un log con UUID {uuid}")

        # Resolver access_user_id interno o dejar NULL en caso de denied/UNKNOWN
        raw_cedula = payload.get('access_user_id')
        access_user_id = None
        if event_type == 'accepted' and raw_cedula and raw_cedula.upper() != 'UNKNOWN':
            cur.execute(
                "SELECT id FROM access_users WHERE cedula = %s",
                (raw_cedula,)
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(
                    f"No existe ningún usuario con cédula {raw_cedula}")
            access_user_id = row[0]

        # Obtener id_device desde location
        cur.execute(
            "SELECT id_device FROM devices WHERE location = %s", (device_name,))
        device_row = cur.fetchone()
        if not device_row:
            raise ValueError(
                f"No se encontró un dispositivo con nombre '{device_name}'")

            cur.execute(
                "SELECT id FROM access_users WHERE cedula = %s", (cedula,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"No existe usuario con cédula {cedula}")
            access_user_id = row[0]        # FK encontrada

        # (si 'denied' -> access_user_id permanece en None)

        # ──────────────────────────────
        # 5. Resolver dispositivo
        # ──────────────────────────────
        cur.execute("SELECT id_device FROM devices WHERE location = %s",
                    (device_name,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"No existe dispositivo '{device_name}'")
        device_id = row[0]

        # ──────────────────────────────
        # 6. Insertar log (access_user_id puede ser NULL)
        # ──────────────────────────────
        cur.execute("""
            INSERT INTO access_logs
                   (id, access_user_id, device_id, event, timestamp)
            VALUES (%s, %s, %s, %s, %s)
        """, (uuid, access_user_id, device_id, event_type, timestamp))

        conn.commit()

        # <<< ADD: publicar el evento en EventBridge para downstream
        eb.put_events(Entries=[{
            'Source': 'tic2.access',
            'DetailType': 'AccessLog',
            'Detail': json.dumps(payload),
            'EventBusName': EVENT_BUS
        }])
        logger.info("Publicado en EventBridge: %s", payload)

        cur.close()
        conn.close()

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Log insertado correctamente"})
        }

    except Exception as e:
        logger.error("Error procesando evento: %s", e)
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)})
        }
