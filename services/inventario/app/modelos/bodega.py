"""Tabla de bodegas (RF05).

Una bodega es un sitio fisico donde se guarda mercancia, y pertenece a un
local. El local vive en el microservicio de Configuracion, por eso aqui
solo se guarda su numero.
"""

from ..extensiones import db


class Bodega(db.Model):
    __tablename__ = "bodegas"
    __table_args__ = (
        db.UniqueConstraint("empresa_id", "local_id", "nombre", name="uq_bodega_local_nombre"),
    )

    bodega_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    empresa_id = db.Column(db.Integer, nullable=False, index=True)
    nombre = db.Column(db.String(100), nullable=False)
    # Referencia logica al local (servicio de Configuracion).
    local_id = db.Column(db.Integer, nullable=False, index=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)

    def a_dic(self):
        return {
            "bodegaId": self.bodega_id,
            "nombre": self.nombre,
            "localId": self.local_id,
            "activo": self.activo,
        }
