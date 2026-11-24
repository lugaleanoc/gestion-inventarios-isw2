"""Crea las tablas de la base de datos UNA SOLA VEZ, antes de arrancar Gunicorn.

Gunicorn arranca 2 procesos y, si cada uno creara las tablas al iniciar, los
dos preguntarian a MySQL "existe la tabla?" al mismo tiempo. Por eso el
contenedor ejecuta primero este script (en un solo proceso) y despues
arranca Gunicorn con CREAR_TABLAS=false (ver el Dockerfile y el compose).

Se reutiliza _crear_tablas() de crear_app(), que ya reintenta mientras MySQL
todavia no acepta conexiones. create_all() solo crea las tablas que faltan:
si ya existen, no hace nada.
"""

import sys

from app import crear_app
from app.config import Config


class ConfigInicial(Config):
    """Misma configuracion, pero forzando la creacion de tablas."""

    CREAR_TABLAS = True


def main():
    try:
        crear_app(ConfigInicial)
    except RuntimeError as exc:
        print("[init_db] {}; se cancela el arranque".format(exc), flush=True)
        return 1
    print("[init_db] tablas de Configuracion listas", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
