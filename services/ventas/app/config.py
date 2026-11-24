"""Configuracion del servicio de Ventas.

Todo lo que cambia entre entornos (local, Docker) se lee de variables de
entorno. Asi la misma imagen de Docker sirve en cualquier lado sin tocar el
codigo (RNF14, portabilidad).
"""

import os


def _entero(nombre, por_defecto):
    """Lee una variable de entorno entera; si no existe o trae basura, usa el valor por defecto."""
    try:
        return int(os.getenv(nombre, por_defecto))
    except (TypeError, ValueError):
        return int(por_defecto)


def _decimal(nombre, por_defecto):
    try:
        return float(os.getenv(nombre, por_defecto))
    except (TypeError, ValueError):
        return float(por_defecto)


class Config:
    # --- Identificacion ---
    # Con este nombre se presenta Ventas ante los demas (X-Servicio-Origen).
    NOMBRE_SERVICIO = os.getenv("NOMBRE_SERVICIO", "ventas")
    PUERTO = _entero("PUERTO", 8000)

    # --- Base de datos propia: ventas_db ---
    SQLALCHEMY_DATABASE_URI = (
        "mysql+pymysql://{usuario}:{clave}@{host}:{puerto}/{nombre}?charset=utf8mb4".format(
            usuario=os.getenv("DB_USUARIO", "ventas"),
            clave=os.getenv("DB_CLAVE", "ventas"),
            host=os.getenv("DB_HOST", "localhost"),
            puerto=_entero("DB_PUERTO", 3306),
            nombre=os.getenv("DB_NOMBRE", "ventas_db"),
        )
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
    CREAR_TABLAS = os.getenv("CREAR_TABLAS", "true").lower() == "true"
    INTENTOS_BD = _entero("INTENTOS_BD", 30)
    ESPERA_BD = _entero("ESPERA_BD", 3)

    # --- Paginacion de los listados ---
    POR_PAGINA_DEFECTO = 20
    POR_PAGINA_MAXIMO = 100

    # --- Otros servicios (nombres de la red interna de Docker) ---
    INVENTARIO_URL = os.getenv("INVENTARIO_URL", "http://inventario-service:8000")
    BALANCE_URL = os.getenv("BALANCE_URL", "http://balance-service:8000")

    # Politica de llamadas (acuerdo del equipo): 3 s de espera, hasta 3 intentos.
    TIMEOUT_SEGUNDOS = _decimal("TIMEOUT_SEGUNDOS", 3)
    MAX_INTENTOS = _entero("MAX_INTENTOS", 3)

    # --- Modo simulado de Inventario ---
    # Mientras el servicio de Inventario no este listo, Ventas puede simular
    # sus respuestas: bodega 1 y un precio fijo para todos los productos.
    USAR_MOCK_INVENTARIO = os.getenv("USAR_MOCK_INVENTARIO", "false").lower() == "true"
    MOCK_PRECIO = _decimal("MOCK_PRECIO", 10000)
    # Para poder probar el 409: si se pide mas de esta cantidad, el mock
    # responde "stock insuficiente", como lo haria Inventario.
    MOCK_STOCK_DISPONIBLE = _entero("MOCK_STOCK_DISPONIBLE", 100)
