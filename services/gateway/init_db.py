import sys
import time

from app.config import db_config
from app.db import DBNoDisponible, crear_tablas

INTENTOS = 60


def main():
    cfg = db_config()
    for intento in range(1, INTENTOS + 1):
        try:
            crear_tablas(cfg)
            print("Base de datos lista", flush=True)
            return 0
        except DBNoDisponible as exc:
            print(f"Esperando la base de datos ({intento}/{INTENTOS}): {exc}", flush=True)
            time.sleep(2)
    return 1


if __name__ == "__main__":
    sys.exit(main())
