# services/access_service.py

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from repositories.access_log_repo import AccessLogRepository
from repositories.device_repo import DeviceRepository
from repositories.access_user_repo import AccessUserRepository

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

VALID_EVENTS = {"accepted", "denied"}


class AccessService:
    """
    Servicio que orquesta la lógica de ingresar un evento de acceso.
    """

    def __init__(
        self,
        log_repo: AccessLogRepository,
        device_repo: DeviceRepository,
        user_repo: AccessUserRepository,
    ):
        self._logs = log_repo
        self._devices = device_repo
        self._users = user_repo

    def ingest(self, payload: Dict[str, Any]) -> None:
        # 1) Validar el tipo de evento
        event_type = payload.get("event")
        if event_type not in VALID_EVENTS:
            raise ValueError(f"Tipo de evento inválido: {event_type}")

        # 2) Validar timestamp
        ts_str = payload.get("timestamp", "")
        try:
            datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            raise ValueError(f"Timestamp inválido: {ts_str}")

        uuid = payload.get("uuid")
        if not uuid:
            raise ValueError("Falta campo 'uuid'")

        # 3) Revisar si ya existe
        if self._logs.exists(uuid):
            raise ValueError(f"Ya existe un log con UUID {uuid}")

        # 4) Resolver device
        location = payload.get("device_name")
        device_id = self._devices.get_id_by_location(location)
        if device_id is None:
            raise ValueError(f"No existe dispositivo '{location}'")

        # 5) Resolver user (solo si 'accepted' y no UNKNOWN)
        raw = payload.get("access_user_id", "")
        access_user_id: Optional[int] = None
        if event_type == "accepted" and raw and raw.upper() != "UNKNOWN":
            user_id = self._users.get_id_by_cedula(raw)
            if user_id is None:
                raise ValueError(f"No existe usuario con cédula {raw}")
            access_user_id = user_id

        # 6) Insertar el log
        self._logs.ingest(
            uuid=uuid,
            access_user_id=access_user_id,
            device_id=device_id,
            event=event_type,
            timestamp=ts_str,
        )
