"""Configuracion del servicio de Balance Diario.

Todo lo que cambia entre entornos (local, Docker) se lee de variables de
entorno (RNF14, portabilidad). Este servicio no llama a ningun otro, por eso
no tiene URLs de otros servicios.
"""

import os


def _entero(nombre, por_defecto):
    """Lee una variable de entorno entera; si no existe o trae basura, usa el valor por defecto."""
    try:
        return int(os.getenv(nombre, por_defecto))
    except (TypeError, ValueError):
        return int(por_defecto)


class Config:
    # --- Identificacion (el contrato usa "balance-diario" en /health) ---
    NOMBRE_SERVICIO = os.getenv("NOMBRE_SERVICIO", "balance-diario")
    PUERTO = _entero("PUERTO", 8000)

    # --- Base de datos propia: balance_db ---
    SQLALCHEMY_DATABASE_URI = (
        "mysql+pymysql://{usuario}:{clave}@{host}:{puerto}/{nombre}?charset=utf8mb4".format(
            usuario=os.getenv("DB_USUARIO", "balance"),
            clave=os.getenv("DB_CLAVE", "balance"),
            host=os.getenv("DB_HOST", "localhost"),
            puerto=_entero("DB_PUERTO", 3306),
            nombre=os.getenv("DB_NOMBRE", "balance_db"),
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
