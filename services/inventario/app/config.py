"""Configuracion del servicio.

Todo lo que cambia entre entornos (local, Docker, Kubernetes) se lee de
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
    NOMBRE_SERVICIO = os.getenv("NOMBRE_SERVICIO", "inventario")
    PUERTO = _entero("PUERTO", 8000)

    # --- Base de datos ---
    # Formato de la cadena de conexion de SQLAlchemy:
    #   mysql+pymysql://usuario:clave@host:puerto/nombre_base
    # "mysql+pymysql" significa: base MySQL, usando el driver PyMySQL.
    SQLALCHEMY_DATABASE_URI = (
        "mysql+pymysql://{usuario}:{clave}@{host}:{puerto}/{nombre}?charset=utf8mb4".format(
            usuario=os.getenv("DB_USUARIO", "root"),
            clave=os.getenv("DB_CLAVE", ""),
            host=os.getenv("DB_HOST", "localhost"),
            puerto=_entero("DB_PUERTO", 3306),
            nombre=os.getenv("DB_NOMBRE", "inventario_db"),
        )
    )
    # Desactiva un seguimiento de cambios que no usamos y que consume memoria.
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # pool_pre_ping prueba la conexion antes de usarla: evita el error
    # "MySQL server has gone away" cuando la base estuvo un rato inactiva.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    # Crear las tablas automaticamente al arrancar (comodo en desarrollo).
    CREAR_TABLAS = os.getenv("CREAR_TABLAS", "true").lower() == "true"

    # --- Direcciones de los otros microservicios ---
    # Dentro de Kubernetes estos nombres los resuelve el DNS del cluster.
    CONFIGURACION_URL = os.getenv("CONFIGURACION_URL", "http://configuracion-service:8000")
    PROVEEDORES_URL = os.getenv("PROVEEDORES_URL", "http://proveedores-service:8000")
    REPOSICION_URL = os.getenv("REPOSICION_URL", "http://reposicion-service:8000")

    # --- Politica de llamadas entre servicios (RF30) ---
    TIMEOUT_SEGUNDOS = _entero("TIMEOUT_SEGUNDOS", 3)
    MAX_REINTENTOS = _entero("MAX_REINTENTOS", 3)
    CB_FALLOS_PARA_ABRIR = _entero("CB_FALLOS_PARA_ABRIR", 5)
    CB_SEGUNDOS_ABIERTO = _entero("CB_SEGUNDOS_ABIERTO", 30)

    # Stock minimo que se usa mientras el servicio de Configuracion no responde.
    STOCK_MINIMO_POR_DEFECTO = _entero("STOCK_MINIMO_POR_DEFECTO", 5)

    # Tamano de pagina de los listados (el contrato fija el maximo en 100).
    POR_PAGINA_DEFECTO = 20
    POR_PAGINA_MAXIMO = 100
