import json
from db import get_db_connection

def lambda_handler(event, context):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Leer parámetros opcionales
        user_id = event.get('queryStringParameters', {}).get('user_id')
        device_id = event.get('queryStringParameters', {}).get('device_id')

        # Armar query dinámico según filtros
        query = """
            SELECT 
                al.id,
                al.access_user_id,
                au.first_name,
                au.last_name,
                au.image_ref,
                al.device_id,
                d.location as device_location,
                al.event,
                al.timestamp
            FROM access_logs al
            LEFT JOIN access_users au ON al.access_user_id = au.id
            LEFT JOIN devices d ON al.device_id = d.id_device
        """
        conditions = []
        params = []

        if user_id:
            conditions.append("al.access_user_id = %s")
            params.append(user_id)

        if device_id:
            conditions.append("al.device_id = %s")
            params.append(device_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY al.timestamp DESC LIMIT 100"

        cur.execute(query, params)
        rows = cur.fetchall()

        logs = []
        for row in rows:
            logs.append({
                'id': row[0],
                'access_user_id': row[1],
                'user': {
                    'first_name': row[2],
                    'last_name': row[3],
                    'image_ref': row[4]
                },
                'device_id': row[5],
                'device_location': row[6],
                'event': row[7],
                'timestamp': row[8].isoformat() if row[8] else None
            })

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(logs)
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
