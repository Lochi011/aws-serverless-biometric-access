import json
import logging
from db import get_db_connection

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info("Evento recibido: %s", json.dumps(event))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Si recibe un ID específico en pathParameters
        device_id = event.get('pathParameters', {}).get('id')
        if device_id:
            cursor.execute("""
                SELECT id_device, location, status, last_sync 
                FROM devices 
                WHERE id_device = %s
            """, (device_id,))
            row = cursor.fetchone()
            if not row:
                return {
                    'statusCode': 404,
                    'body': json.dumps({'error': 'Device not found'})
                }
            result = {'id_device': row[0], 'location': row[1], 'status': row[2], 'last_sync': str(row[3]) if row[3] else None}
        else:
            cursor.execute("""
                SELECT id_device, location, status, last_sync 
                FROM devices
            """)
            rows = cursor.fetchall()
            result = [
                {'id_device': r[0], 'location': r[1], 'status': r[2], 'last_sync': str(r[3]) if r[3] else None}
                for r in rows
            ]

        cursor.close()
        conn.close()

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(result)
        }

    except Exception as e:
        logger.error(f"Error en la Lambda: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error', 'details': str(e)})
        }
