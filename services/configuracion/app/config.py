"""Configuracion del servicio.

Todo lo que cambia entre entornos (local, Docker) se lee de
variables de entorno. Asi la misma imagen de Docker sirve en cualquier lado
sin tocar el codigo, que es lo que pide el RNF14 (portabilidad).
"""

import os


def _entero(nombre, por_defecto):
    """Lee una variable de entorno y la convierte a entero.

    Si la variable no existe o trae basura, devuelve el valor por defecto
    en vez de reventar al arrancar.
    """
    try:
        return int(os.getenv(nombre, por_defecto))
    except (TypeError, ValueError):
        return int(por_defecto)


class Config:
    """Valores de configuracion que la aplicacion Flask leera al arrancar."""

    # --- Identificacion ---
    NOMBRE_SERVICIO = os.getenv("NOMBRE_SERVICIO", "configuracion")
    PUERTO = _entero("PUERTO", 8000)

    # --- Base de datos ---
    #   mysql+pymysql://usuario:clave@host:puerto/nombre_base
    SQLALCHEMY_DATABASE_URI = (
        "mysql+pymysql://{usuario}:{clave}@{host}:{puerto}/{nombre}?charset=utf8mb4".format(
            usuario=os.getenv("DB_USUARIO", "root"),
            clave=os.getenv("DB_CLAVE", ""),
            host=os.getenv("DB_HOST", "localhost"),
            puerto=_entero("DB_PUERTO", 3306),
            nombre=os.getenv("DB_NOMBRE", "configuracion_db"),
        )
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # pool_pre_ping evita el error "MySQL server has gone away".
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    # Crear las tablas automaticamente al arrancar (comodo en desarrollo).
    CREAR_TABLAS = os.getenv("CREAR_TABLAS", "true").lower() == "true"
    # Al arrancar, MySQL puede no estar listo todavia: se reintenta cada
    # ESPERA_BD segundos, hasta INTENTOS_BD veces (30 x 3 s = 1,5 minutos).
    INTENTOS_BD = _entero("INTENTOS_BD", 30)
    ESPERA_BD = _entero("ESPERA_BD", 3)

    # Stock minimo con el que se crea una empresa nueva. Despues cada empresa
    # puede cambiar el suyo con PUT /api/configuracion/empresa.
    STOCK_MINIMO_POR_DEFECTO = _entero("STOCK_MINIMO_POR_DEFECTO", 5)

    # Este servicio no llama a ningun otro (lo dice el contrato), por eso no
    # tiene URLs de otros servicios ni politica de reintentos.
