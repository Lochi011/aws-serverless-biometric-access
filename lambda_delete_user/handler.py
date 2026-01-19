import os
import json
import boto3
import psycopg2
from urllib.parse import urlparse

# Cliente AWS IoT
iot = boto3.client(
    "iot-data",
    endpoint_url=f"https://{os.environ['IOT_ENDPOINT']}"
)

def delete_user_image(image_url):
    try:
        parsed = urlparse(image_url)
        # Elimina el primer '/' para obtener la key
        key = parsed.path.lstrip("/")
        s3.delete_object(Bucket=S3_BUCKET, Key=key)
    except s3.exceptions.NoSuchKey:
        pass  # Si no existe, no hacer nada
    except Exception as e:
        print(f"Error deleting image: {e}")  # Log simple

# Cliente S3
s3 = boto3.client("s3")
S3_BUCKET = os.environ["S3_BUCKET"]

def get_conn():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASS"],
        sslmode="require"
    )

def notify_user_deletion(cedula, raspis):
    for raspi in raspis:
        topic = f"access/users/delete/{raspi}"
        iot.publish(
            topic=topic,
            qos=1,
            payload=json.dumps({"cedula": cedula})
        )

def lambda_handler(event, context):
    try:
        user_id = event.get("pathParameters", {}).get("id")
        if not user_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "User ID is required"})
            }

        conn = get_conn()
        cur = conn.cursor()

        # Obtener cédula e image_ref
        cur.execute("SELECT cedula, image_ref FROM access_users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        if not row:
            return {"statusCode": 404, "body": json.dumps({"error": "User not found"})}
        cedula, image_ref = row

        # Eliminar imagen de S3 (si existe image_ref)
        if image_ref:
            delete_user_image(image_ref)

        # Obtener nombres de raspis a las que tiene acceso el usuario
        cur.execute("""
            SELECT d.location
            FROM device_user_mappings dum
            JOIN devices d ON dum.device_id = d.id_device
            WHERE dum.access_user_id = %s
        """, (user_id,))
        raspis = [row[0] for row in cur.fetchall()]

        cur.execute("BEGIN")
        cur.execute("DELETE FROM access_logs WHERE access_user_id = %s", (user_id,))
        cur.execute("DELETE FROM device_user_mappings WHERE access_user_id = %s", (user_id,))
        cur.execute("DELETE FROM access_users WHERE id = %s", (user_id,))
        conn.commit()

        notify_user_deletion(cedula, raspis)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "User and image deleted successfully",
                "user_id": user_id,
                "raspis_notified": raspis
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
