"""Tabla de locales.

Configuracion es la duena del catalogo de locales (decision 1): los demas
servicios, como Inventario con sus bodegas, solo guardan el `localId`.
"""

from ..extensiones import db


class Local(db.Model):
    __tablename__ = "locales"
    __table_args__ = (
        # Una empresa no puede tener dos locales con el mismo nombre.
        db.UniqueConstraint("empresa_id", "nombre", name="uq_local_empresa_nombre"),
    )

    local_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    empresa_id = db.Column(db.Integer, nullable=False, index=True)
    nombre = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.String(200), nullable=True)
    ciudad = db.Column(db.String(100), nullable=True)
    # Baja logica (decision 8): nunca se borra la fila.
    activo = db.Column(db.Boolean, nullable=False, default=True)

    def a_dic(self):
        return {
            "localId": self.local_id,
            "empresaId": self.empresa_id,
            "nombre": self.nombre,
            "direccion": self.direccion,
            "ciudad": self.ciudad,
            "activo": self.activo,
        }
