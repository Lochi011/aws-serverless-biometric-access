# tests/services/test_access_service.py

import pytest
from services.access_service import AccessService


class DummyLogRepo:
    def __init__(self, exists=False):
        self._exists = exists
        self.inserted = False

    def exists(self, log_id):
        return self._exists

    def insert(self, *args, **kwargs):
        self.inserted = True


class DummyDeviceRepo:
    def __init__(self, device_id=None):
        self._device_id = device_id

    def get_id_by_location(self, location):
        return self._device_id


class DummyUserRepo:
    def __init__(self, user_id=None):
        self._user_id = user_id

    def get_id_by_cedula(self, cedula):
        return self._user_id


def test_ingest_success():
    log_repo = DummyLogRepo(exists=False)
    dev_repo = DummyDeviceRepo(device_id=99)
    user_repo = DummyUserRepo(user_id=42)
    svc = AccessService(log_repo, dev_repo, user_repo)

    payload = {
        "uuid": "abc-111",
        "access_user_id": "12345678",
        "device_name": "Puerta X",
        "event": "accepted",
        "timestamp": "2025-06-03T18:00:00Z"
    }

    svc.ingest(payload)
    assert log_repo.inserted is True


def test_ingest_duplicate():
    log_repo = DummyLogRepo(exists=True)
    dev_repo = DummyDeviceRepo(device_id=1)
    user_repo = DummyUserRepo(user_id=2)
    svc = AccessService(log_repo, dev_repo, user_repo)

    payload = {
        "uuid": "dup-111",
        "access_user_id": "12345678",
        "device_name": "Puerta X",
        "event": "accepted",
        "timestamp": "2025-06-03T18:00:00Z"
    }

    with pytest.raises(ValueError) as excinfo:
        svc.ingest(payload)
    assert "Ya existe un log" in str(excinfo.value)


def test_ingest_invalid_event():
    log_repo = DummyLogRepo(exists=False)
    dev_repo = DummyDeviceRepo(device_id=1)
    user_repo = DummyUserRepo(user_id=2)
    svc = AccessService(log_repo, dev_repo, user_repo)

    payload = {
        "uuid": "bad-evt",
        "access_user_id": "12345678",
        "device_name": "Puerta X",
        "event": "invalid",
        "timestamp": "2025-06-03T18:00:00Z"
    }

    with pytest.raises(ValueError) as excinfo:
        svc.ingest(payload)
    assert "Tipo de evento inválido" in str(excinfo.value)


def test_ingest_invalid_device():
    log_repo = DummyLogRepo(exists=False)
    dev_repo = DummyDeviceRepo(device_id=None)
    user_repo = DummyUserRepo(user_id=2)
    svc = AccessService(log_repo, dev_repo, user_repo)

    payload = {
        "uuid": "no-dev",
        "access_user_id": "12345678",
        "device_name": "Puerta Inexistente",
        "event": "accepted",
        "timestamp": "2025-06-03T18:00:00Z"
    }

    with pytest.raises(ValueError) as excinfo:
        svc.ingest(payload)
    assert "No existe dispositivo" in str(excinfo.value)


def test_ingest_user_not_found():
    log_repo = DummyLogRepo(exists=False)
    dev_repo = DummyDeviceRepo(device_id=55)
    user_repo = DummyUserRepo(user_id=None)
    svc = AccessService(log_repo, dev_repo, user_repo)

    payload = {
        "uuid": "user-not",
        "access_user_id": "00000000",
        "device_name": "Puerta X",
        "event": "accepted",
        "timestamp": "2025-06-03T18:00:00Z"
    }

    with pytest.raises(ValueError) as excinfo:
        svc.ingest(payload)
    assert "No existe usuario" in str(excinfo.value)
