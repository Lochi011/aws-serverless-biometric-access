# tests/services/test_auth_service.py

import bcrypt
import jwt
import pytest
from datetime import datetime, timedelta

from services.auth_service import AuthService


class DummyUser:
    """
    Simula un objeto WebUser con atributos usados por AuthService.
    """

    def __init__(self, id, email, first_name, last_name, password_hash, role):
        self.id = id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.password_hash = password_hash
        self.role = role


class DummyRepo:
    """
    Simula WebUserRepository. Devuelve un DummyUser o None.
    """

    def __init__(self, user):
        self._user = user

    def get_by_email(self, email: str):
        if self._user and self._user.email == email:
            return self._user
        return None


@pytest.fixture
def secret_and_algo():
    return {"secret": "testsecret", "algorithm": "HS256"}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def test_login_raises_value_error_on_missing_fields(secret_and_algo):
    repo = DummyRepo(None)
    svc = AuthService(
        repo, secret_and_algo["secret"], secret_and_algo["algorithm"])

    with pytest.raises(ValueError):
        svc.login("", "")
    with pytest.raises(ValueError):
        svc.login("user@example.com", "")


def test_login_raises_permission_error_user_not_found(secret_and_algo):
    repo = DummyRepo(None)
    svc = AuthService(
        repo, secret_and_algo["secret"], secret_and_algo["algorithm"])

    with pytest.raises(PermissionError):
        svc.login("notfound@example.com", "anypassword")


def test_login_raises_permission_error_wrong_password(secret_and_algo):
    correct_pw = "CorrectPass!"
    hashed = hash_password(correct_pw)
    user = DummyUser(
        id=1,
        email="test@example.com",
        first_name="Test",
        last_name="User",
        password_hash=hashed,
        role="user"
    )
    repo = DummyRepo(user)
    svc = AuthService(
        repo, secret_and_algo["secret"], secret_and_algo["algorithm"])

    with pytest.raises(PermissionError):
        svc.login("test@example.com", "WrongPass!")


def test_login_returns_token_and_user_info(secret_and_algo):
    password = "MyPassword!"
    hashed = hash_password(password)
    user = DummyUser(
        id=42,
        email="foo@bar.com",
        first_name="Foo",
        last_name="Bar",
        password_hash=hashed,
        role="admin"
    )
    repo = DummyRepo(user)
    svc = AuthService(
        repo, secret_and_algo["secret"], secret_and_algo["algorithm"])

    token, user_info = svc.login("foo@bar.com", password)

    # Verificar que el JWT contenga los claims correctos
    decoded = jwt.decode(token, secret_and_algo["secret"], algorithms=[
                         secret_and_algo["algorithm"]])
    assert decoded["email"] == "foo@bar.com"
    assert decoded["name"] == "Foo Bar"
    assert decoded["role"] == "admin"
    # Verificar user_info
    assert user_info["id"] == 42
    assert user_info["email"] == "foo@bar.com"
    assert user_info["name"] == "Foo Bar"
