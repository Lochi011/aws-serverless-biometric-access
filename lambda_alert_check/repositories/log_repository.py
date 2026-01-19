from datetime import datetime


class LogRepository:
    def __init__(self, connection):
        self._conn = connection

    def get_device_id(self, device_name: str) -> int:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT id_device FROM devices WHERE location = %s",
                (device_name,)
            )
            row = cur.fetchone()
            return row[0] if row else None

    def get_config(self, device_id: int) -> tuple:
        query = """
        WITH cfg AS (
          SELECT
            COALESCE(dev_th.value, glob_th.value)::int AS threshold,
            COALESCE(dev_wi.value,  glob_wi.value )::int AS window_seconds
          FROM devices d
          LEFT JOIN configurations dev_th
            ON dev_th.name_config='max_denied_attempts' AND dev_th.device_id = d.id_device
          LEFT JOIN configurations glob_th
            ON glob_th.name_config='max_denied_attempts' AND glob_th.device_id IS NULL
          LEFT JOIN configurations dev_wi
            ON dev_wi.name_config='window_seconds' AND dev_wi.device_id = d.id_device
          LEFT JOIN configurations glob_wi
            ON glob_wi.name_config='window_seconds' AND glob_wi.device_id IS NULL
          WHERE d.id_device = %s
        )
        SELECT threshold, window_seconds FROM cfg
        """
        with self._conn.cursor() as cur:
            cur.execute(query, (device_id,))
            row = cur.fetchone()
            return (row[0], row[1]) if row else (None, None)

    def count_denies(self, device_id: int, start: datetime, end: datetime) -> int:
        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM access_logs
                WHERE device_id = %s
                  AND event = 'denied'
                  AND timestamp BETWEEN %s AND %s
                """,
                (device_id, start, end)
            )
            return cur.fetchone()[0]
