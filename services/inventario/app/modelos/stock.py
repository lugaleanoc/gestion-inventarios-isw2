"""Tabla de existencias: cuantas unidades hay de cada producto en cada bodega (RF04).

Es el saldo actual. El historial de como se llego a ese saldo esta en la
tabla de movimientos (el kardex).
"""

from ..extensiones import db


class Stock(db.Model):
    __tablename__ = "stock"
    __table_args__ = (
        # Solo puede existir una fila por producto y bodega. Esta restriccion
        # es la que evita que queden dos saldos distintos del mismo producto.
        db.UniqueConstraint("producto_id", "bodega_id", name="uq_stock_producto_bodega"),
    )

    stock_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    empresa_id = db.Column(db.Integer, nullable=False, index=True)
    producto_id = db.Column(
        db.Integer, db.ForeignKey("productos.producto_id"), nullable=False, index=True
    )
    bodega_id = db.Column(
        db.Integer, db.ForeignKey("bodegas.bodega_id"), nullable=False, index=True
    )
    # Nunca deberia quedar negativa: antes de descontar se verifica el saldo.
    cantidad = db.Column(db.Integer, nullable=False, default=0)

    def a_dic(self, local_id=None):
        return {
            "productoId": self.producto_id,
            "bodegaId": self.bodega_id,
            "localId": local_id,
            "cantidad": self.cantidad,
        }
