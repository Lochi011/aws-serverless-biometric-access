from datetime import datetime, timedelta


class AlertService:
    def __init__(self, repository, sns_client):
        self._repo = repository
        self._sns = sns_client

    def process_denied_event(self, device_name: str, timestamp: datetime) -> bool:
        # 1) Obtener device_id
        device_id = self._repo.get_device_id(device_name)
        if device_id is None:
            return False

        # 2) Leer configuración
        threshold, window_seconds = self._repo.get_config(device_id)
        if threshold is None or window_seconds is None:
            return False

        # 3) Contar denies
        start = timestamp - timedelta(seconds=window_seconds)
        count = self._repo.count_denies(device_id, start, timestamp)

        # 4) Publicar alerta si supera umbral
        if count >= threshold:
            payload = {
                "alert_type":     "ACCESS_DENIED_THRESHOLD_EXCEEDED",
                "device_name":    device_name,
                "denied_count":   count,
                "threshold":      threshold,
                "window_seconds": window_seconds,
                "period_start":   start.isoformat() + 'Z',
                "period_end":     timestamp.isoformat() + 'Z',
                "timestamp":      datetime.utcnow().isoformat() + 'Z'
            }
            subject = f"[ALERTA] {count} denies en {device_name}"
            self._sns.publish_alert(payload, subject)
            return True

        return False
