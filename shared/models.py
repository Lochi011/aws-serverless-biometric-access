# shared/models.py

import os
from peewee import (
    Model,
    PostgresqlDatabase,
    SqliteDatabase,
    CharField,
    IntegerField,
    DateTimeField,
    UUIDField,
    ForeignKeyField,
    TextField
)

# 1) Si no hay DB_NAME definido o está vacío, usar ":memory:" por defecto.
#    Esto hace que en tests, donde no definimos vars, use SQLite en memoria.
DB_NAME = os.environ.get("DB_NAME") or ":memory:"
DB_USER = os.environ.get("DB_USER", "")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_HOST = os.environ.get("DB_HOST", "")
DB_PORT = int(os.environ.get("DB_PORT", 5432))

if DB_NAME == ":memory:":
    db = SqliteDatabase(":memory:")
else:
    db = PostgresqlDatabase(
        DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )


class BaseModel(Model):
    class Meta:
        database = db


class AccessUser(BaseModel):
    id = IntegerField(primary_key=True)
    first_name = CharField(null=True)
    last_name = CharField(null=True)
    cedula = CharField(unique=True)
    rfid = CharField(null=True)
    image_ref = CharField(null=True)
    face_embedding = TextField(null=True)
    created_at = DateTimeField(null=True)

    class Meta:
        table_name = "access_users"


class Device(BaseModel):
    id_device = CharField(primary_key=True)  # Cambiar de IntegerField a CharField
    location = CharField(unique=True)
    status = CharField(null=True)
    last_sync = DateTimeField(null=True)

    class Meta:
        table_name = "devices"


class AccessLog(BaseModel):
    id = UUIDField(primary_key=True)
    access_user = ForeignKeyField(
        AccessUser, 
        field="id", 
        backref="logs", 
        null=True, 
        column_name="access_user_id"
    )
    device = ForeignKeyField(
        Device, 
        field="id_device", 
        backref="logs", 
        column_name="device_id",
        # Importante: NO usar to_field aquí, ya está especificado en field=
    )
    event = CharField()
    timestamp = DateTimeField()

    class Meta:
        table_name = "access_logs"


class WebUser(BaseModel):
    """
    Modelo para la tabla `web_users`:
    - id: clave primaria auto-incremental
    - email: único
    - first_name, last_name: nombres del usuario
    - password_hash: hash de bcrypt
    - role: rol (por ejemplo, 'admin', 'user', etc.)
    """
    id = IntegerField(primary_key=True)
    email = CharField(unique=True)
    first_name = CharField()
    last_name = CharField()
    password_hash = CharField()
    role = CharField()

    class Meta:
        table_name = "web_users"


class DeviceUserMapping(BaseModel):
    """
    Tabla intermedia para la relación many-to-many entre usuarios y dispositivos
    """
    # ELIMINAR la línea: id = IntegerField(primary_key=True)
    
    access_user = ForeignKeyField(
        AccessUser,
        field="id",
        backref="device_mappings",
        column_name="access_user_id"
    )
    device = ForeignKeyField(
        Device,
        field="id_device",
        backref="user_mappings",
        column_name="device_id"
    )

    class Meta:
        table_name = "device_user_mappings"
        primary_key = False  # AGREGAR esta línea
        indexes = (
            # Crear índice único para evitar duplicados
            (("access_user", "device"), True),
        )

class Configuration(BaseModel):
    """Tabla de configuraciones del sistema"""
    id_config = IntegerField(primary_key=True)
    name_config = CharField(max_length=100)
    value = CharField(max_length=255)
    description = TextField(null=True)
    device_id = CharField(null=True)  # Para futuro uso por dispositivo
    
    class Meta:
        table_name = "configurations"
