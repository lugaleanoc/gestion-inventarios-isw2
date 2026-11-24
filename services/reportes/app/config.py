import os

ROL_ADMIN = "administrador"
ROL_VENDEDOR = "vendedor"
ROL_BODEGA = "encargado_bodega"
ROL_TIENDA = "tienda_web"

ROLES = {ROL_ADMIN, ROL_VENDEDOR, ROL_BODEGA, ROL_TIENDA}

SERVICIOS_POR_DEFECTO = {
    "configuracion": "http://configuracion-service:8000",
    "inventario": "http://inventario-service:8000",
    "ventas": "http://ventas-service:8000",
    "reposicion": "http://reposicion-service:8000",
    "balance": "http://balance-service:8000",
}

METRICAS = (
    "ventas_por_canal",
    "productos_baja_rotacion",
    "productos_agotados",
    "estado_reposiciones",
    "balance_diario",
    "ingresos_egresos",
    "valor_inventario",
)

PERIODOS_DIAS = {
    "hoy": 0,
    "semana": 6,
    "7_dias": 6,
    "ultimos_7_dias": 6,
    "mes": 29,
    "30_dias": 29,
    "ultimos_30_dias": 29,
}
PERIODO_POR_DEFECTO_DIAS = 29


def db_config():
    if os.getenv("DB_DRIVER", "mysql") == "sqlite":
        return {"driver": "sqlite", "path": os.getenv("DB_PATH", "reportes.db")}
    return {
        "driver": "mysql",
        "host": os.getenv("DB_HOST", "reportes-db"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "reportes"),
        "password": os.getenv("DB_PASSWORD", "reportes_pass"),
        "name": os.getenv("DB_NAME", "reportes_db"),
    }


def ajustes():
    return {
        "DB": db_config(),
        "SERVICIOS": {
            nombre: os.getenv(f"{nombre.upper()}_URL", url).rstrip("/")
            for nombre, url in SERVICIOS_POR_DEFECTO.items()
        },
        "TIMEOUT_CONEXION": float(os.getenv("TIMEOUT_CONEXION", "2")),
        "TIMEOUT_LECTURA": float(os.getenv("TIMEOUT_LECTURA", "4")),
        "CACHE_TTL_SEGUNDOS": int(os.getenv("CACHE_TTL_SEGUNDOS", "60")),
        "CACHE_TTL_PARCIAL_SEGUNDOS": int(os.getenv("CACHE_TTL_PARCIAL_SEGUNDOS", "10")),
        "REINTENTOS": int(os.getenv("REINTENTOS", "3")),
        "REINTENTO_ESPERA": float(os.getenv("REINTENTO_ESPERA", "0.2")),
        "CIRCUITO_FALLAS": int(os.getenv("CIRCUITO_FALLAS", "3")),
        "CIRCUITO_SEGUNDOS": float(os.getenv("CIRCUITO_SEGUNDOS", "5")),
        "ZONA_HORARIA_HORAS": int(os.getenv("ZONA_HORARIA_HORAS", "-5")),
    }
