from shared.models import WebUser


class WebUserRepository:
    """
    Repositorio para acceder a la tabla `web_users` usando Peewee.
    """

    def get_by_email(self, email: str):
        """
        Retorna una instancia de WebUser si existe el usuario con ese email,
        o None si no se encontró.
        """
        try:
            return WebUser.get(WebUser.email == email)
        except WebUser.DoesNotExist:
            return None
