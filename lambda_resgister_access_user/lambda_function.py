import os
import json
import base64
import uuid
import boto3
import psycopg2
from datetime import datetime
import face_recognition
import numpy as np
import cv2

iot = boto3.client(
    "iot-data",
    endpoint_url=f"https://{os.environ['IOT_ENDPOINT']}"
)


# Cliente S3
s3 = boto3.client("s3")

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


def extract_embedding(image_bytes):
    """
    Toma bytes JPEG, los decodifica, convierte BGR→RGB,
    detecta la primera cara y devuelve la lista de 128 floats.
    """
    # 1) JPEG bytes → NumPy BGR array
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("No se pudo decodificar la imagen")

    # 2) BGR → RGB
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    # 3) Detecta caras (HOG por defecto)
    face_locs = face_recognition.face_locations(rgb)
    if not face_locs:
        raise ValueError("No se detectó ninguna cara en la imagen")

    # 4) Genera el embedding (128D) de la primera cara
    encoding = face_recognition.face_encodings(rgb, face_locs)[0]

    # 5) Devolver como lista de floats
    return encoding.tolist()
# Handler de Lambda


def notify_new_user(user, raspis):
    """
    Publica un JSON de usuario en access/users/new/<raspi>
    para cada raspi de la lista.
    """
    for raspi in raspis:
        topic = f"access/users/new/{raspi}"
        iot.publish(
            topic=topic,
            qos=1,
            payload=json.dumps(user)
        )


def lambda_handler(event, context):
    # Parsear body
    body = event.get("body", event)
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Request body is not valid JSON"})
            }

    # Campos esperados
    fn = (body.get("firstName") or "").strip()
    ln = (body.get("lastName") or "").strip()
    ced = (body.get("cedula") or "").strip()
    rfid = (body.get("rfid") or "").strip()
    raspis = body.get("raspis", [])  # lista de ubicaciones de raspis
    img_b64 = body.get("image")

    # Validaciones básicas
    errors = []
    if not fn:
        errors.append("First name is required")
    if not ln:
        errors.append("Last name is required")
    if not ced:
        errors.append("Cédula is required")
    if not rfid:
        errors.append("RFID is required")
    if not img_b64:
        errors.append("Image is required in base64 format")
    if errors:
        return {"statusCode": 400, "body": json.dumps({"errors": errors})}

    # Normalizar y decodificar imagen Base64
    raw = img_b64
    if raw.startswith("data:") and "," in raw:
        raw = raw.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(raw)
    except Exception:
        return {"statusCode": 400, "body": json.dumps({"error": "Image is not valid base64"})}

    # Subir imagen a S3 con el ContentType correcto
    key = f"access_users/{uuid.uuid4()}.jpg"
    s3.put_object(
        Bucket=os.environ["S3_BUCKET"],
        Key=key,
        Body=image_bytes,
        ContentType="image/jpeg"
    )
    image_url = f"https://{os.environ['S3_BUCKET']}.s3.amazonaws.com/{key}"

    # face_emb = extract_embedding(image_bytes)  # stub
    try:
        face_emb = extract_embedding(image_bytes)
    except ValueError as e:
        return {"statusCode": 400, "body": json.dumps({"error": str(e)})}

    # Conectar a la BD para validaciones de unicidad
    conn = get_conn()
    cur = conn.cursor()

    # Chequear unicidad de cédula
    cur.execute("SELECT 1 FROM access_users WHERE cedula = %s", (ced,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return {"statusCode": 409, "body": json.dumps({"error": "Cédula already exists"})}

    # Chequear unicidad de RFID
    cur.execute("SELECT 1 FROM access_users WHERE rfid = %s", (rfid,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return {"statusCode": 409, "body": json.dumps({"error": "RFID already exists"})}

    # 2. Extraer embedding (stub)
    face_emb = extract_embedding(image_bytes)

    # 3. Insertar en la BD access_users
    cur.execute(
        """
        INSERT INTO access_users (
            first_name, last_name, cedula, rfid, image_ref, face_embedding, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
        """,
        (fn, ln, ced, rfid, image_url, json.dumps(
            face_emb), datetime.utcnow(), datetime.utcnow())
    )
    user_id = cur.fetchone()[0]

    # 4. Mapear N:N según ubicaciones de raspis
    for raspi_location in raspis:
        cur.execute(
            "SELECT id_device FROM devices WHERE location = %s", (
                raspi_location,)
        )
        row = cur.fetchone()
        if row:
            device_id = row[0]
            cur.execute(
                """
                INSERT INTO device_user_mappings (
                    device_id, access_user_id
                ) VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (device_id, user_id)
            )
        else:
            print(
                f"Advertencia: ningún dispositivo con location='{raspi_location}' encontrado.")

    new_user = {
        "id": user_id,
        "first_name": fn,
        "last_name": ln,
        "cedula": ced,
        "rfid": rfid,
        "image_ref": image_url,
        "face_embedding": face_emb
    }
    notify_new_user(new_user, raspis)  # raspis = body["raspis"]

    conn.commit()
    cur.close()
    conn.close()

    return {"statusCode": 201, "body": json.dumps({"user_id": user_id, "image_ref": image_url})}
