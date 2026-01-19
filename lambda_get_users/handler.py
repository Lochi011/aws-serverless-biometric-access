import json, logging
from lib.db import get_db_connection
import psycopg2

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        user_id = event.get('pathParameters', {}).get('id')

        if user_id:
            # Solicitud GET /access_users/{id}
            cur.execute("""
                SELECT 
                    au.id, 
                    au.first_name, 
                    au.last_name, 
                    au.cedula,
                    au.created_at,
                    au.image_ref,
                    COALESCE(
                        json_agg(
                            json_build_object(
                                'device_id', d.id_device,
                                'location', d.location
                            )
                        ) FILTER (WHERE d.id_device IS NOT NULL),
                        '[]'
                    ) as doors
                FROM access_users au
                LEFT JOIN device_user_mappings dum ON au.id = dum.access_user_id
                LEFT JOIN devices d ON dum.device_id = d.id_device
                WHERE au.id = %s
                GROUP BY au.id, au.first_name, au.last_name, au.cedula, au.created_at, au.image_ref
            """, (user_id,))
            row = cur.fetchone()
            if not row:
                return {
                    "statusCode": 404,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"message": "Usuario no encontrado"})
                }
            result = row
        else:
            # Solicitud GET /access_users
            cur.execute("""
                SELECT 
                    au.id, 
                    au.first_name, 
                    au.last_name, 
                    au.cedula,
                    au.created_at,
                    au.image_ref,
                    COALESCE(
                        json_agg(
                            json_build_object(
                                'device_id', d.id_device,
                                'location', d.location
                            )
                        ) FILTER (WHERE d.id_device IS NOT NULL),
                        '[]'
                    ) as doors
                FROM access_users au
                LEFT JOIN device_user_mappings dum ON au.id = dum.access_user_id
                LEFT JOIN devices d ON dum.device_id = d.id_device
                GROUP BY au.id, au.first_name, au.last_name, au.cedula, au.created_at, au.image_ref
                ORDER BY au.id
            """)
            result = cur.fetchall()

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result, default=str)
        }

    except Exception as e:
        logger.exception("Error querying access_users")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "Error interno del servidor"})
        }
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass
