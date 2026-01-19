import os
import json
import boto3
import psycopg2

# Cliente AWS IoT
iot = boto3.client(
    "iot-data",
    endpoint_url=f"https://{os.environ['IOT_ENDPOINT']}"
)

# Conexión a PostgreSQL
def get_conn():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASS"],
        sslmode="require"
    )

def get_user_info(user_id, cur):
    cur.execute("SELECT first_name, last_name, cedula, rfid, image_ref, face_embedding FROM access_users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    if not row:
        return None
    return {
        "id": user_id,
        "first_name": row[0],
        "last_name": row[1],
        "cedula": row[2],
        "rfid": row[3],
        "image_ref": row[4],
        "face_embedding": row[5]
    }

def notify_add(user, raspis):
    for raspi in raspis:
        topic = f"access/users/new/{raspi}"
        iot.publish(
            topic=topic,
            qos=1,
            payload=json.dumps(user)
        )

def notify_remove(cedula, raspis):
    for raspi in raspis:
        topic = f"access/users/delete/{raspi}"
        iot.publish(
            topic=topic,
            qos=1,
            payload=json.dumps({"cedula": cedula})
        )

def lambda_handler(event, context):
    try:
        # Obtener el ID del path
        user_id = event.get("pathParameters", {}).get("id")
        if not user_id:
            return {"statusCode": 400, "body": json.dumps({"error": "User ID is required"})}

        # Parsear el body
        body = event.get("body", event)
        if isinstance(body, str):
            body = json.loads(body)

        add_devices = body.get("addDevices", [])
        remove_devices = body.get("removeDevices", [])

        if not isinstance(add_devices, list) or not isinstance(remove_devices, list):
            return {"statusCode": 400, "body": json.dumps({"error": "addDevices and removeDevices must be lists"})}

        conn = get_conn()
        cur = conn.cursor()

        # Obtener información del usuario
        user = get_user_info(user_id, cur)
        if not user:
            return {"statusCode": 404, "body": json.dumps({"error": "User not found"})}

        cedula = user["cedula"]

        # ---- Eliminar accesos ----
        raspis_removed = []
        for device_name in remove_devices:
            cur.execute("SELECT id_device FROM devices WHERE location = %s", (device_name,))
            row = cur.fetchone()
            if row:
                device_id = row[0]
                cur.execute("DELETE FROM device_user_mappings WHERE access_user_id = %s AND device_id = %s", (user_id, device_id))
                raspis_removed.append(device_name)

        # ---- Agregar accesos ----
        raspis_added = []
        for device_name in add_devices:
            cur.execute("SELECT id_device FROM devices WHERE location = %s", (device_name,))
            row = cur.fetchone()
            if row:
                device_id = row[0]
                cur.execute("""
                    INSERT INTO device_user_mappings (device_id, access_user_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING;
                """, (device_id, user_id))
                raspis_added.append(device_name)

        conn.commit()

        # Notificar a las Raspis
        if raspis_removed:
            notify_remove(cedula, raspis_removed)

        if raspis_added:
            notify_add(user, raspis_added)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "User device access updated",
                "added": raspis_added,
                "removed": raspis_removed
            })
        }

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error", "details": str(e)})
        }

    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
