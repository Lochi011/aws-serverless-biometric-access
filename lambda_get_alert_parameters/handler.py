import json
from db import get_db_connection

def lambda_handler(event, context):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Buscar las configuraciones necesarias
        cursor.execute("""
            SELECT name_config, value
            FROM configurations
            WHERE name_config IN ('max_denied_attempts', 'window_seconds');
        """)
        rows = cursor.fetchall()

        # Convertir a diccionario
        config = {name: int(value) for name, value in rows}

        return {
            'statusCode': 200,
            'body': json.dumps({
                'max_denied_attempts': config.get('max_denied_attempts', None),
                'window_seconds': config.get('window_seconds', None)
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
