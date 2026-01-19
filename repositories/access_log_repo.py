# repositories/access_log_repo.py
from typing import List, Optional, Dict
from datetime import datetime
import uuid
from peewee import DoesNotExist, JOIN
from shared.models import AccessLog, AccessUser, Device
from typing import Optional
from datetime import datetime
from shared.models import AccessLog, db


class AccessLogRepository:
    """Repositorio para operaciones con AccessLog usando Peewee ORM"""

    def create(self, access_user_id: int, device_id: str, event: str, timestamp: datetime) -> AccessLog:
        """
        Crea un nuevo log de acceso.

        Args:
            access_user_id: ID del usuario
            device_id: ID del dispositivo (string)
            event: Tipo de evento
            timestamp: Fecha y hora del evento

        Returns:
            AccessLog creado
        """
        _id = uuid.uuid4()
        return AccessLog.create(
            id=_id,
            access_user_id=access_user_id,
            device_id=device_id,
            event=event,
            timestamp=timestamp
        )

    def ingest(
        self,
        uuid: str,
        access_user_id: Optional[int],
        device_id: str,
        event: str,
        timestamp: str
    ) -> None:
        """
        Inserta un nuevo AccessLog a partir del payload validado.

        Args:
            uuid:             UUID del log (string).
            access_user_id:   ID numérico del usuario o None.
            device_id:        ID del dispositivo (string).
            event:            Tipo de evento ('accepted'|'denied').
            timestamp:        ISO8601 string, ej. "2025-05-20T21:00:00Z".
        """
        # 1) Convierte el timestamp a datetime
        ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        # 2) Guarda dentro de una transacción
        with db.atomic():
            AccessLog.create(
                id=uuid,
                access_user=access_user_id,
                device=device_id,
                event=event,
                timestamp=ts
            )

    def get_logs_with_filters(
        self,
        user_id: Optional[int] = None,
        device_id: Optional[str] = None,
        limit: int = 100
    ) -> List[AccessLog]:
        """
        Obtiene logs con filtros opcionales, incluyendo datos de usuario y dispositivo.

        Args:
            user_id: Filtrar por ID de usuario (opcional)
            device_id: Filtrar por ID de dispositivo (opcional)
            limit: Número máximo de resultados

        Returns:
            Lista de AccessLog con datos relacionados
        """
        # Query base con joins
        query = (AccessLog
                 .select(AccessLog, AccessUser, Device)
                 .join(AccessUser, JOIN.LEFT_OUTER, on=(AccessLog.access_user_id == AccessUser.id))
                 .switch(AccessLog)
                 .join(Device, JOIN.LEFT_OUTER, on=(AccessLog.device_id == Device.id_device)))

        # Aplicar filtros si existen
        if user_id is not None:
            query = query.where(AccessLog.access_user_id == user_id)

        if device_id is not None:
            query = query.where(AccessLog.device_id == device_id)

        # Ordenar por timestamp descendente y limitar
        query = query.order_by(AccessLog.timestamp.desc()).limit(limit)

        # Ejecutar query y retornar resultados con datos precargados
        return list(query)

    def count_by_filters(
        self,
        user_id: Optional[int] = None,
        device_id: Optional[str] = None
    ) -> int:
        """
        Cuenta logs según filtros.

        Args:
            user_id: Filtrar por ID de usuario (opcional)
            device_id: Filtrar por ID de dispositivo (opcional)

        Returns:
            Número de logs que cumplen los filtros
        """
        query = AccessLog.select()

        if user_id is not None:
            query = query.where(AccessLog.access_user_id == user_id)

        if device_id is not None:
            query = query.where(AccessLog.device_id == device_id)

        return query.count()

    def exists(self, log_id: str) -> bool:
        """Devuelve True si AccessLog con UUID existe."""
        return AccessLog.select().where(AccessLog.id == log_id).exists()
