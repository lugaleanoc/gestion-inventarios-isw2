import os

ROL_ADMIN = "administrador"
ROL_VENDEDOR = "vendedor"
ROL_BODEGA = "encargado_bodega"
ROL_TIENDA_WEB = "tienda_web"

ROLES = {ROL_ADMIN, ROL_VENDEDOR, ROL_BODEGA, ROL_TIENDA_WEB}


def db_config():
    if os.getenv("DB_DRIVER", "mysql") == "sqlite":
        return {"driver": "sqlite", "path": os.getenv("DB_PATH", "proveedores.db")}
    return {
        "driver": "mysql",
        "host": os.getenv("DB_HOST", "proveedores-db"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "proveedores"),
        "password": os.getenv("DB_PASSWORD", "proveedores_pass"),
        "name": os.getenv("DB_NAME", "proveedores_db"),
    }
