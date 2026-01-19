import jwt


class AuthorizerService:
    """
    Servicio encargado únicamente de validar el JWT.
    No lee variables de entorno; recibe secret y algorithm por constructor.
    """

    def __init__(self, secret: str, algorithm: str):
        self._secret = secret
        self._algorithm = algorithm

    def is_token_valid(self, token: str) -> bool:
        """
        Devuelve True si el token es válido según PyJWT, False en caso contrario.
        """
        try:
            jwt.decode(token, self._secret, algorithms=[self._algorithm])
            return True
        except jwt.PyJWTError:
            return False
