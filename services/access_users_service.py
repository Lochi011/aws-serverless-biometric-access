# services/access_user_service.py
# sube imagen a S3
# nuevo helper
from datetime import datetime as dt
import base64
from typing import List, Dict, Optional
from repositories.access_user_repo import AccessUserRepository
import boto3
import os
import json
from urllib.parse import urlparse
import logging

logger = logging.getLogger()


class AccessUserService:
    """Servicio para lógica de negocio de usuarios de acceso"""

    def __init__(self, access_user_repo: AccessUserRepository):
        self.access_user_repo = access_user_repo
        # Inicializar clientes AWS
        self.s3 = boto3.client("s3")
        self.s3_bucket = os.environ.get("S3_BUCKET", "")
        endpoint = os.getenv("IOT_ENDPOINT")             # None si no existe
        if endpoint:                                     # .env presente
            endpoint_url = endpoint if endpoint.startswith(
                "http") else f"https://{endpoint}"
        else:                                            # fallback para tests / integraciones locales
            endpoint_url = "https://localhost"
        self.iot = boto3.client("iot-data", endpoint_url=endpoint_url)

    def _format_user_with_doors(self, user) -> Dict:
        """
        Formatea un usuario con sus puertas en el formato esperado.

        Args:
            user: Instancia de AccessUser con _mappings cargados

        Returns:
            Dict con formato de respuesta
        """
        # Construir lista de puertas desde los mappings
        doors = []
        if hasattr(user, '_mappings'):
            for mapping in user._mappings:
                doors.append({
                    'device_id': mapping.device.id_device,
                    'location': mapping.device.location
                })

        return {
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'cedula': user.cedula,
            'created_at': str(user.created_at) if user.created_at else None,
            'image_ref': user.image_ref,
            'doors': doors
        }

    def get_user_by_id(self, user_id: str) -> Dict:
        """
        Obtiene un usuario por ID con sus puertas asociadas.

        Args:
            user_id: ID del usuario (string desde path parameter)

        Returns:
            Dict con datos del usuario y puertas

        Raises:
            ValueError: Si el user_id no es válido
            LookupError: Si el usuario no existe
        """
        # Validar que user_id sea un número
        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            raise ValueError("ID de usuario inválido")

        # Buscar usuario con dispositivos
        user = self.access_user_repo.get_by_id_with_devices(user_id_int)

        if not user:
            raise LookupError(f"Usuario con ID {user_id} no encontrado")

        return self._format_user_with_doors(user)

    def get_all_users(self) -> List[Dict]:
        """
        Obtiene todos los usuarios con sus puertas asociadas.

        Returns:
            Lista de diccionarios con datos de usuarios
        """
        users = self.access_user_repo.get_all_with_devices()

        return [self._format_user_with_doors(user) for user in users]

    def _delete_user_image(self, image_ref: str) -> None:
        """
        Elimina la imagen del usuario de S3.

        Args:
            image_ref: URL o referencia de la imagen
        """
        if not image_ref or not self.s3_bucket:
            return

        try:
            parsed = urlparse(image_ref)
            # Eliminar el primer '/' para obtener la key
            key = parsed.path.lstrip("/")

            self.s3.delete_object(Bucket=self.s3_bucket, Key=key)
            logger.info(f"Imagen eliminada de S3: {key}")

        except self.s3.exceptions.NoSuchKey:
            # Si no existe, no hacer nada
            logger.warning(f"Imagen no encontrada en S3: {image_ref}")
        except Exception as e:
            # Log del error pero continuar con la eliminación del usuario
            logger.error(f"Error eliminando imagen de S3: {e}")

    def _notify_user_deletion(self, cedula: str, device_locations: List[str]) -> None:
        """
        Notifica a las Raspberry Pi sobre la eliminación del usuario.

        Args:
            cedula: Cédula del usuario eliminado
            device_locations: Lista de ubicaciones/nombres de dispositivos
        """
        if not cedula or not device_locations:
            return

        for location in device_locations:
            try:
                topic = f"access/users/delete/{location}"
                payload = json.dumps({"cedula": cedula})

                self.iot.publish(
                    topic=topic,
                    qos=1,
                    payload=payload
                )
                logger.info(
                    f"Notificación enviada a {location} para eliminar usuario {cedula}")

            except Exception as e:
                # Log del error pero continuar con las otras notificaciones
                logger.error(f"Error notificando a {location}: {e}")

    def delete_user(self, user_id: str) -> Dict:
        """
        Elimina un usuario, su imagen y notifica a los dispositivos.

        Args:
            user_id: ID del usuario a eliminar (string desde path parameter)

        Returns:
            Dict con información sobre la eliminación

        Raises:
            ValueError: Si el user_id no es válido
            LookupError: Si el usuario no existe
        """
        # Validar que user_id sea un número
        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            raise ValueError("ID de usuario inválido")

        # Obtener información del usuario antes de eliminar
        user = self.access_user_repo.get_user_with_image(user_id_int)
        if not user:
            raise LookupError(f"Usuario con ID {user_id} no encontrado")

        # Obtener dispositivos asociados antes de eliminar
        device_locations = self.access_user_repo.get_user_devices_locations(
            user_id_int)

        # Eliminar imagen de S3 si existe
        if user.image_ref:
            self._delete_user_image(user.image_ref)

        # Eliminar usuario y datos relacionados
        success = self.access_user_repo.delete_user_and_related_data(
            user_id_int)

        if not success:
            raise Exception("Error al eliminar el usuario de la base de datos")

        # Notificar a las Raspberry Pi
        self._notify_user_deletion(user.cedula, device_locations)

        return {
            "message": "User and image deleted successfully",
            "user_id": user_id,
            "raspis_notified": device_locations
        }

        # ------------------------------------------------------------------
    # Notifica a las RPis que hay un usuario nuevo (alta / update)
    # ------------------------------------------------------------------
        # ------------------ NOTIFICACIÓN DE ALTA ------------------

    def _notify_new_user(self, user: Dict, device_locations: List[str]) -> None:
        """
        Publica en MQTT el JSON del nuevo usuario para que cada Raspberry Pi
        lo agregue localmente.
        """
        if not device_locations:
            return

        for location in device_locations:
            try:
                self.iot.publish(
                    topic=f"access/users/new/{location}",
                    qos=1,
                    payload=json.dumps(user)
                )
                logger.info("Notificación NEW enviada a %s (usuario %s)",
                            location, user.get('cedula'))
            except Exception as e:
                logger.error("Error notificando NEW a %s: %s", location, e)

        # ------------------- CREAR USUARIO ------------------------

       # ------------------- CREAR USUARIO ------------------------
    def create_user(self, body: Dict) -> Dict:
        """
        Alta completa de usuario:
        - valida campos requeridos y formatos
        - decodifica imagen, valida tamaño, obtiene embedding
        - comprueba unicidad de cédula y RFID
        - sube imagen a S3
        - inserta en BD (AccessUserRepository.create)
        - notifica a las Raspberry Pi
        Devuelve {"user_id": id, "image_ref": url}
        """
        # 1) Campos obligatorios
        required = ["firstName", "lastName", "cedula", "rfid", "image"]
        missing = [k for k in required if not body.get(k)]
        if missing:
            raise ValueError(f"Missing fields: {', '.join(missing)}")

        # 1.1) Formato de cedula y RFID
        import re
        ced = body["cedula"]
        rfid = body["rfid"]
        if not re.fullmatch(r"\d{7,10}", ced):
            raise ValueError(
                "Cédula debe tener entre 7 y 10 dígitos numéricos")
        if not re.fullmatch(r"[A-Za-z0-9\\-]{5,20}", rfid):
            raise ValueError(
                "RFID debe ser 5-20 caracteres alfanuméricos o guiones")

        # 1.2) Lista de raspis
        raspis = body.get("raspis", [])
        if not isinstance(raspis, list) or not all(isinstance(r, str) for r in raspis):
            raise ValueError("raspis debe ser una lista de strings")

        # 2) Imagen base64 → bytes + validar tamaño (<=5MB)
        raw = body["image"].split(",", 1)[-1]
        try:
            img_bytes = base64.b64decode(raw)
        except Exception:
            raise ValueError("Image is not valid base64")
        if len(img_bytes) > 5 * 1024 * 1024:
            raise ValueError("Image size must be <= 5MB")

        # 3) Embedding facial + validar longitud
        from services.face_service import extract_embedding
        face_emb = extract_embedding(img_bytes)
        if not isinstance(face_emb, list) or len(face_emb) != 128:
            raise ValueError("Invalid face embedding (expected 128 floats)")

        # 4) Unicidad de cédula y RFID
        if self.access_user_repo.exists(ced):
            raise LookupError("Cédula already exists")
        if self.access_user_repo.exists_rfid(rfid):
            raise LookupError("RFID already exists")

        # 5) Subir imagen a S3
        from services.storage_service import upload_jpeg
        img_url = upload_jpeg(img_bytes)

        # 6) Insertar en BD
        user = self.access_user_repo.create(
            first_name=body["firstName"],
            last_name=body["lastName"],
            cedula=ced,
            rfid=rfid,
            image_ref=img_url,
            face_embedding=json.dumps(face_emb),
            created_at=dt.utcnow()
        )

        # 7) Notificar a las Raspberry Pi
        self._notify_new_user({
            "id": user.id,
            "first_name": user.first_name,
            "last_name":  user.last_name,
            "cedula":     user.cedula,
            "rfid":       user.rfid,
            "image_ref":  img_url,
            "face_embedding": face_emb,
        }, raspis)

        return {"user_id": user.id, "image_ref": img_url}
