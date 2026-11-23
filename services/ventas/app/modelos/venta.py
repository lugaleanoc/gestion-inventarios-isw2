"""Tablas de ventas y de sus items (RF15, RF16).

Estados de una venta:
    en_proceso -> se esta descontando el stock en Inventario
    confirmada -> Inventario desconto el stock
    rechazada  -> Inventario rechazo o no respondio; no se desconto nada

Estado del ingreso en Balance Diario (estadoBalance):
    registrado -> Balance recibio el ingreso
    pendiente  -> Balance no respondio; se puede reintentar
    no_aplica  -> la venta no esta confirmada, no genera ingreso
"""

from ..extensiones import db
from ..fechas import a_texto, ahora

CANALES = ["tienda_fisica", "tienda_web"]
MEDIOS_PAGO = ["efectivo", "tarjeta", "qr"]
ESTADOS = ["en_proceso", "confirmada", "rechazada"]
ESTADOS_BALANCE = ["registrado", "pendiente", "no_aplica"]


class Venta(db.Model):
    __tablename__ = "ventas"
    __table_args__ = (
        # Indice para los filtros mas usados: empresa + fecha.
        db.Index("ix_ventas_empresa_fecha", "empresa_id", "fecha_hora"),
    )

    venta_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    empresa_id = db.Column(db.Integer, nullable=False)      # de X-Empresa-Id
    local_id = db.Column(db.Integer, nullable=False)        # referencia logica (Configuracion)
    bodega_id = db.Column(db.Integer, nullable=True)        # referencia logica (Inventario)
    canal = db.Column(db.String(20), nullable=False)
    medio_pago = db.Column(db.String(20), nullable=False)
    # Numeric guarda el dinero exacto (sin errores de redondeo de float).
    total = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    usuario_id = db.Column(db.Integer, nullable=True)       # de X-Usuario-Id
    fecha_hora = db.Column(db.DateTime, nullable=False, default=ahora)
    estado = db.Column(db.String(20), nullable=False, default="en_proceso")
    estado_balance = db.Column(db.String(20), nullable=False, default="no_aplica")

    # relationship: venta.items trae los items de la venta.
    items = db.relationship("ItemVenta", backref="venta", lazy="selectin",
                            order_by="ItemVenta.item_id")

    def a_dic(self):
        return {
            "ventaId": self.venta_id,
            "empresaId": self.empresa_id,
            "localId": self.local_id,
            "bodegaId": self.bodega_id,
            "canal": self.canal,
            "medioPago": self.medio_pago,
            "items": [item.a_dic() for item in self.items],
            "total": float(self.total or 0),
            "usuarioId": self.usuario_id,
            "fechaHora": a_texto(self.fecha_hora),
            "estado": self.estado,
            "estadoBalance": self.estado_balance,
        }


class ItemVenta(db.Model):
    __tablename__ = "items_venta"

    item_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    venta_id = db.Column(db.Integer, db.ForeignKey("ventas.venta_id"), nullable=False, index=True)
    producto_id = db.Column(db.Integer, nullable=False)     # referencia logica (Inventario)
    cantidad = db.Column(db.Integer, nullable=False)
    # El precio lo da Inventario al descontar el stock; el cliente nunca lo envia.
    precio_unitario = db.Column(db.Numeric(14, 2), nullable=False)
    subtotal = db.Column(db.Numeric(14, 2), nullable=False)

    def a_dic(self):
        return {
            "productoId": self.producto_id,
            "cantidad": self.cantidad,
            "precioUnitario": float(self.precio_unitario),
            "subtotal": float(self.subtotal),
        }
