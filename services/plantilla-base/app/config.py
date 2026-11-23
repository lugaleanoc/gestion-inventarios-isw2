import os

ROL_ADMIN = "administrador"
ROL_VENDEDOR = "vendedor"
ROL_BODEGA = "encargado_bodega"
ROL_TIENDA_WEB = "tienda_web"

ROLES = {ROL_ADMIN, ROL_VENDEDOR, ROL_BODEGA, ROL_TIENDA_WEB}


def db_config():
    if os.getenv("DB_DRIVER", "mysql") == "sqlite":
        return {"driver": "sqlite", "path": os.getenv("DB_PATH", "plantilla.db")}
    return {
        "driver": "mysql",
        "host": os.getenv("DB_HOST", "plantilla-db"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "plantilla"),
        "password": os.getenv("DB_PASSWORD", "plantilla_pass"),
        "name": os.getenv("DB_NAME", "plantilla_db"),
    }
