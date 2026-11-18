"""Configuracion del microservicio de Reposicion.

Igual que en Inventario, todo sale de variables de entorno para que la
misma imagen sirva en local, en Docker y en Kubernetes (RNF14).

Nota: estos archivos de apoyo (config, errores, seguridad, entrada,
paginacion y el cliente HTTP) estan repetidos en cada microservicio a
proposito. En microservicios no se comparte una libreria comun entre
servicios: cada uno debe poder cambiarse y desplegarse solo, sin que
tocar una libreria obligue a volver a desplegar los ocho (RNF01, RNF13).
"""

import os


def _entero(nombre, por_defecto):
    """Lee una variable de entorno y la convierte a entero."""
    try:
        return int(os.getenv(nombre, por_defecto))
    except (TypeError, ValueError):
        return int(por_defecto)


class Config:
    NOMBRE_SERVICIO = os.getenv("NOMBRE_SERVICIO", "reposicion")
    PUERTO = _entero("PUERTO", 8000)

    SQLALCHEMY_DATABASE_URI = (
        "mysql+pymysql://{usuario}:{clave}@{host}:{puerto}/{nombre}?charset=utf8mb4".format(
            usuario=os.getenv("DB_USUARIO", "reposicion"),
            clave=os.getenv("DB_CLAVE", "reposicion"),
            host=os.getenv("DB_HOST", "localhost"),
            puerto=_entero("DB_PUERTO", 3306),
            nombre=os.getenv("DB_NOMBRE", "reposicion_db"),
        )
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
    CREAR_TABLAS = os.getenv("CREAR_TABLAS", "true").lower() == "true"

    # Servicios a los que llama Reposicion.
    INVENTARIO_URL = os.getenv("INVENTARIO_URL", "http://inventario-service:8000")
    PROVEEDORES_URL = os.getenv("PROVEEDORES_URL", "http://proveedores-service:8000")
    CONFIGURACION_URL = os.getenv("CONFIGURACION_URL", "http://configuracion-service:8000")

    TIMEOUT_SEGUNDOS = _entero("TIMEOUT_SEGUNDOS", 3)
    MAX_REINTENTOS = _entero("MAX_REINTENTOS", 3)
    CB_FALLOS_PARA_ABRIR = _entero("CB_FALLOS_PARA_ABRIR", 5)
    CB_SEGUNDOS_ABIERTO = _entero("CB_SEGUNDOS_ABIERTO", 30)

    # Valores por defecto mientras Configuracion no este listo.
    STOCK_MINIMO_POR_DEFECTO = _entero("STOCK_MINIMO_POR_DEFECTO", 5)
    # Cuanto pedir cuando el sistema sugiere solo una cantidad: se repone
    # hasta este multiplo del stock minimo (minimo x 3 - lo que queda).
    FACTOR_REPOSICION = _entero("FACTOR_REPOSICION", 3)

    POR_PAGINA_DEFECTO = 20
    POR_PAGINA_MAXIMO = 100
