import os

ROL_ADMIN = "administrador"
ROL_VENDEDOR = "vendedor"
ROL_BODEGA = "encargado_bodega"
ROL_TIENDA = "tienda_web"

ROLES_USUARIO = (ROL_ADMIN, ROL_VENDEDOR, ROL_BODEGA)

SERVICIOS_POR_DEFECTO = {
    "configuracion": "http://configuracion-service:8000",
    "inventario": "http://inventario-service:8000",
    "proveedores": "http://proveedores-service:8000",
    "ventas": "http://ventas-service:8000",
    "reposicion": "http://reposicion-service:8000",
    "balance": "http://balance-service:8000",
    "reportes": "http://reportes-service:8000",
}

RUTAS_INTERNAS = (
    "/api/inventario/stock/descuentos",
    "/api/inventario/stock/entradas",
    "/api/reposicion/solicitudes/automaticas",
    "/api/balance/movimientos/ventas",
    "/api/configuracion/empresas",
)


def db_config():
    if os.getenv("DB_DRIVER", "mysql") == "sqlite":
        return {"driver": "sqlite", "path": os.getenv("DB_PATH", "gateway.db")}
    return {
        "driver": "mysql",
        "host": os.getenv("DB_HOST", "gateway-db"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "gateway"),
        "password": os.getenv("DB_PASSWORD", "gateway_pass"),
        "name": os.getenv("DB_NAME", "gateway_db"),
    }


def ajustes():
    servicios = {
        nombre: os.getenv(f"{nombre.upper()}_URL", url).rstrip("/")
        for nombre, url in SERVICIOS_POR_DEFECTO.items()
    }
    return {
        "DB": db_config(),
        "JWT_SECRET": os.getenv("JWT_SECRET", "cambiar-este-secreto"),
        "JWT_EXPIRA_MINUTOS": int(os.getenv("JWT_EXPIRA_MINUTOS", "480")),
        "JWT_TIENDA_EXPIRA_MINUTOS": int(os.getenv("JWT_TIENDA_EXPIRA_MINUTOS", "60")),
        "CODIGO_RECUPERACION_MINUTOS": int(os.getenv("CODIGO_RECUPERACION_MINUTOS", "15")),
        "EXPONER_CODIGO_RECUPERACION": os.getenv("EXPONER_CODIGO_RECUPERACION", "false").lower() == "true",
        "SERVICIOS": servicios,
        "TIMEOUT_CONEXION": float(os.getenv("TIMEOUT_CONEXION", "3")),
        "TIMEOUT_LECTURA": float(os.getenv("TIMEOUT_LECTURA", "15")),
    }
