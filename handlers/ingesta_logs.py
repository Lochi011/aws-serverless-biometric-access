# handlers/ingesta_logs.py

import json
import logging
import os
import boto3

from shared.models import db
from services.access_service import AccessService
from repositories.access_log_repo import AccessLogRepository
from repositories.device_repo import DeviceRepository
from repositories.access_user_repo import AccessUserRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)

EVENT_BUS = os.environ.get("EVENT_BUS_NAME", "default")
eb = boto3.client("events")

# Inyectamos repositorios en el servicio
_service = AccessService(
    AccessLogRepository(),
    DeviceRepository(),
    AccessUserRepository(),
)


def handler(event, context):
    try:
        # 1) Abrir conexión Peewee (si aún está cerrada)
        if db.is_closed():
            db.connect()

        logger.info("Evento recibido: %s", json.dumps(event))

        # 2) Ejecutar lógica de negocio
        _service.ingest(event)

        # 3) Publicar en EventBridge
        eb.put_events(
            Entries=[{
                "Source": "tic2.access",
                "DetailType": "AccessLog",
                "Detail": json.dumps(event),
                "EventBusName": EVENT_BUS,
            }]
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Log insertado correctamente"})
        }

    except ValueError as ve:
        logger.error("Error de validación: %s", ve)
        return {"statusCode": 400, "body": json.dumps({"error": str(ve)})}

    except Exception as exc:
        logger.error("Error procesando evento: %s", exc)
        return {"statusCode": 500, "body": json.dumps({"error": str(exc)})}

    finally:
        # 4) Cerrar la conexión Peewee
        if not db.is_closed():
            db.close()
