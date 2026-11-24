"""Crea las tablas de la base de datos UNA SOLA VEZ, antes de arrancar Gunicorn.

Por que existe este archivo:

La aplicacion creaba las tablas al arrancar, dentro de crear_app(), con
db.create_all(). Gunicorn ejecuta ese codigo una vez por cada proceso
trabajador. Con un solo proceso no hay problema, pero con dos o mas los dos
preguntan a MySQL "existe la tabla?" en el mismo instante, los dos reciben
"no", y los dos intentan crearla. El segundo llega tarde y MySQL responde:

    pymysql.err.OperationalError: (1050, "Table 'categorias' already exists")

Bajar a un solo proceso evitaba el error, pero a costa de atender una sola
peticion a la vez. La solucion de verdad es separar los dos trabajos:
este script crea las tablas, y solo cuando termina arranca Gunicorn con los
procesos que hagan falta. Asi la base de datos deja de depender de cuantos
procesos haya.

Lo ejecuta el contenedor al arrancar, antes de Gunicorn (ver el Dockerfile).
"""

import os
import sys
import time

from app import crear_app
from app.config import Config
from app.extensiones import db

# Cuantas veces reintentar si MySQL todavia no acepta conexiones. Al
# levantar todo junto, la base puede tardar unos segundos mas que el
# servicio en estar lista.
INTENTOS = int(os.getenv("INTENTOS_BD", "30"))
ESPERA_SEGUNDOS = 2


class ConfigInicial(Config):
    """Misma configuracion, pero sin crear tablas al construir la app.

    Las crea este script explicitamente, mas abajo.
    """

    CREAR_TABLAS = False


def main():
    app = crear_app(ConfigInicial)

    for intento in range(1, INTENTOS + 1):
        try:
            with app.app_context():
                # create_all comprueba primero que exista: si ya estan, no
                # hace nada. Al correr en un solo proceso, esa comprobacion
                # es segura.
                db.create_all()
            print("[init_db] tablas de Inventario listas", flush=True)
            return 0
        except Exception as exc:  # noqa: BLE001
            print("[init_db] intento {}/{}: la base aun no responde ({})".format(
                intento, INTENTOS, exc), flush=True)
            time.sleep(ESPERA_SEGUNDOS)

    print("[init_db] la base de datos no respondio; se cancela el arranque",
          flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
