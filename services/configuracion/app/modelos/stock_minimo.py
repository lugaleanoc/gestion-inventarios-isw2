"""Tabla de stock minimo por producto (RF26).

Solo guarda los productos que tienen un valor propio. Los que no aparecen
aqui usan el stock minimo por defecto (origen = por_defecto).
El valor aplica al total del producto en todas las bodegas (decision 4).
"""

from ..extensiones import db


class StockMinimo(db.Model):
    __tablename__ = "stock_minimo"
    __table_args__ = (
        # Un producto tiene un solo stock minimo por empresa.
        db.UniqueConstraint("empresa_id", "producto_id", name="uq_stock_minimo_producto"),
    )

    stock_minimo_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    empresa_id = db.Column(db.Integer, nullable=False, index=True)
    # Referencia logica al producto (servicio de Inventario).
    producto_id = db.Column(db.Integer, nullable=False)
    stock_minimo = db.Column(db.Integer, nullable=False)

    def a_dic(self):
        return {
            "productoId": self.producto_id,
            "stockMinimo": self.stock_minimo,
            "origen": "producto",
        }
