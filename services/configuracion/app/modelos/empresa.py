"""Tabla de empresas.

Configuracion es la duena del catalogo de empresas (decision 1). Los demas
servicios solo guardan el numero `empresaId`, sin llave foranea.
La crea el API Gateway cuando una empresa se registra.
"""

from ..extensiones import db
from ..fechas import a_texto, ahora


class Empresa(db.Model):
    __tablename__ = "empresas"

    empresa_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(150), nullable=False)
    # El NIT no se puede repetir entre empresas.
    nit = db.Column(db.String(30), nullable=False, unique=True)
    # Se usa para los productos que no tienen un stock minimo propio.
    stock_minimo_por_defecto = db.Column(db.Integer, nullable=False, default=5)
    activa = db.Column(db.Boolean, nullable=False, default=True)
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=ahora)

    def a_dic(self):
        return {
            "empresaId": self.empresa_id,
            "nombre": self.nombre,
            "nit": self.nit,
            "stockMinimoPorDefecto": self.stock_minimo_por_defecto,
            "activa": self.activa,
            "fechaCreacion": a_texto(self.fecha_creacion),
        }
