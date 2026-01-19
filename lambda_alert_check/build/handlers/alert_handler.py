import os
import json
from datetime import datetime

import boto3
import psycopg2

from infra.sns_client import SnsClient
from repositories.log_repository import LogRepository
from services.alert_service import AlertService


def lambda_handler(event, context):
    # Filtrar solo los eventos 'denied'
    detail = event.get('detail', {})
    if detail.get('event') != 'denied':
        return {"status": "ignored"}

    # Conexión a la base de datos
    conn = psycopg2.connect(
        host=os.environ['DB_HOST'],
        port=int(os.environ.get('DB_PORT', 5432)),
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
        dbname=os.environ['DB_NAME']
    )

    # Inicializar capas
    repo = LogRepository(conn)
    sns_client = SnsClient(os.environ['SNS_TOPIC_ARN'])
    service = AlertService(repo, sns_client)

    # Procesar evento
    timestamp = datetime.fromisoformat(
        detail['timestamp'].replace('Z', '+00:00'))
    alerted = service.process_denied_event(
        device_name=detail['device_name'],
        timestamp=timestamp
    )

    conn.close()
    return {"alerted": alerted}
