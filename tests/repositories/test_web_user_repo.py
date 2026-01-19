# tests/repositories/test_web_user_repo.py

import bcrypt
import pytest

from shared.models import WebUser, db
from repositories.web_user_repo import WebUserRepository


@pytest.fixture(autouse=True)
def prepare_db():
    """
    Conecta a SQLite en memoria y crea/dropea la tabla WebUser antes/después de cada test.
    """
    db.connect()
    db.create_tables([WebUser])
    yield
    db.drop_tables([WebUser])
    db.close()


@pytest.fixture
def create_user():
    """
    Inserta un usuario de prueba en la BD en memoria.
    """
    password = "Password123!"
    password_hash = bcrypt.hashpw(password.encode(
        "utf-8"), bcrypt.gensalt()).decode("utf-8")

    user = WebUser.create(
        email="test@example.com",
        first_name="Test",
        last_name="User",
        password_hash=password_hash,
        role="user"
    )
    return user


def test_get_by_email_exist(create_user):
    repo = WebUserRepository()
    result = repo.get_by_email("test@example.com")

    assert result is not None
    assert result.email == "test@example.com"
    assert result.first_name == "Test"
    assert result.role == "user"


def test_get_by_email_no_exist():
    repo = WebUserRepository()
    result = repo.get_by_email("noone@example.com")

    assert result is None
