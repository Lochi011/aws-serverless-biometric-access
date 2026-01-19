# tests/handlers/test_ingesta_logs.py

import json
import pytest
from unittest.mock import patch

import handlers.ingesta_logs as h  # importamos el módulo completo


@pytest.fixture
def dummy_event():
    return {
        "uuid": "evt-123",
        "access_user_id": "11111111",
        "device_name": "Puerta A",
        "event": "accepted",
        "timestamp": "2025-06-03T18:00:00Z",
    }


def test_handler_ok(dummy_event):
    # Parcheamos _service.ingest → no error
    # También parchamos db.is_closed para que devuelva False (no conecte)
    with patch.object(h._service, "ingest", return_value=None) as mock_ingest, \
            patch.object(h.db, "is_closed", return_value=False), \
            patch.object(h, "eb") as mock_eb:
        mock_eb.put_events.return_value = {"FailedEntryCount": 0}

        resp = h.handler(dummy_event, None)
        body = json.loads(resp["body"])

        assert resp["statusCode"] == 200
        assert body["message"] == "Log insertado correctamente"
        mock_ingest.assert_called_once_with(dummy_event)
        mock_eb.put_events.assert_called_once()


def test_handler_validation_error(dummy_event):
    # Hacemos que ingest lance ValueError
    with patch.object(h._service, "ingest", side_effect=ValueError("evento inválido")) as mock_ingest, \
            patch.object(h.db, "is_closed", return_value=False):
        resp = h.handler(dummy_event, None)
        body = json.loads(resp["body"])

        assert resp["statusCode"] == 400
        assert "evento inválido" in body["error"]
        mock_ingest.assert_called_once_with(dummy_event)


def test_handler_unexpected_error(dummy_event):
    # Hacemos que ingest lance Exception genérico
    with patch.object(h._service, "ingest", side_effect=Exception("errorDB")) as mock_ingest, \
            patch.object(h.db, "is_closed", return_value=False):
        resp = h.handler(dummy_event, None)
        body = json.loads(resp["body"])

        assert resp["statusCode"] == 500
        assert "errorDB" in body["error"]
        mock_ingest.assert_called_once_with(dummy_event)
