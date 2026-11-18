"""Extensiones compartidas por toda la aplicacion.

Se crean aqui, vacias, y se conectan a la aplicacion dentro de crear_app().
Esto evita las importaciones circulares: los modelos importan `db` de este
archivo, y no de __init__.py, que a su vez importa los modelos.
"""

from flask_sqlalchemy import SQLAlchemy

# `db` es la puerta de entrada al ORM: con db.Model se definen las tablas
# y con db.session se guardan y consultan los datos.
db = SQLAlchemy()
