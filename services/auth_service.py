import bcrypt
import jwt
from datetime import datetime, timedelta

from repositories.web_user_repo import WebUserRepository


class AuthService:
    """
    Servicio que encapsula la lógica de autenticación (login).
    Recibe el repositorio de WebUser y los parámetros de JWT por constructor.
    """

    def __init__(self, user_repo: WebUserRepository, jwt_secret: str, jwt_algorithm: str):
        self._user_repo = user_repo
        self._secret = jwt_secret
        self._algorithm = jwt_algorithm

    def login(self, email: str, password: str):
        """
        1) Verifica que 'email' y 'password' no estén vacíos (ValueError si faltan).
        2) Busca el usuario en BD por email (PermissionError si no existe).
        3) Verifica el password con bcrypt (PermissionError si no coincide).
        4) Genera y retorna (token_jwt, user_info_dict).
           user_info_dict = {'id': ..., 'email': ..., 'name': 'Firstname Lastname'}
        """
        # 1) Validación básica de inputs
        if not email or not password:
            raise ValueError("Email and password are required")

        # 2) Buscar usuario en la BD
        user = self._user_repo.get_by_email(email)
        if not user:
            raise PermissionError("Invalid credentials")

        # 3) Verificar contraseña
        stored_hash = user.password_hash.encode("utf-8")
        if not bcrypt.checkpw(password.encode("utf-8"), stored_hash):
            raise PermissionError("Invalid credentials")

        # 4) Construir payload y generar JWT
        payload = {
            "user_id": str(user.id),
            "email": user.email,
            "name": f"{user.first_name} {user.last_name}",
            "role": user.role,
            "exp": datetime.utcnow() + timedelta(days=1),
        }
        token = jwt.encode(payload, self._secret, algorithm=self._algorithm)

        user_info = {
            "id": user.id,
            "email": user.email,
            "name": f"{user.first_name} {user.last_name}",
        }
        return token, user_info
