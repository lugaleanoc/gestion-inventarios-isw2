"""Tabla de ordenes de compra (RF06, RF20).

Una orden sale de una solicitud ya aprobada y se le emite al proveedor.
Cuando llega la mercancia se registra la recepcion, que es lo que suma el
stock en el microservicio de Inventario.

Estados:  emitida --recepcion--> recibida
             |
             +--cancelacion--> cancelada
"""

from datetime import datetime

from ..extensiones import db

ESTADOS_ORDEN = ("emitida", "recibida", "cancelada")


class Orden(db.Model):
    __tablename__ = "ordenes"

    orden_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    empresa_id = db.Column(db.Integer, nullable=False, index=True)
    # La solicitud si vive en esta base, asi que es llave foranea real.
    solicitud_id = db.Column(
        db.Integer, db.ForeignKey("solicitudes.solicitud_id"), nullable=False, index=True
    )
    # Referencias logicas hacia Proveedores e Inventario.
    proveedor_id = db.Column(db.Integer, nullable=True, index=True)
    producto_id = db.Column(db.Integer, nullable=False, index=True)
    cantidad = db.Column(db.Integer, nullable=False)

    estado = db.Column(db.String(20), nullable=False, default="emitida")
    fecha_emision = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fecha_estimada_entrega = db.Column(db.Date, nullable=True)
    motivo_cancelacion = db.Column(db.String(200), nullable=True)

    # Datos de la recepcion. Quedan vacios hasta que llegue la mercancia.
    bodega_id = db.Column(db.Integer, nullable=True)
    cantidad_recibida = db.Column(db.Integer, nullable=True)
    fecha_recepcion = db.Column(db.DateTime, nullable=True)
    recibida_por = db.Column(db.String(60), nullable=True)

    def a_dic(self):
        return {
            "ordenId": self.orden_id,
            "solicitudId": self.solicitud_id,
            "proveedorId": self.proveedor_id,
            "productoId": self.producto_id,
            "cantidad": self.cantidad,
            "estado": self.estado,
            "fechaEmision": self.fecha_emision.isoformat() if self.fecha_emision else None,
            "fechaEstimadaEntrega": (
                self.fecha_estimada_entrega.isoformat() if self.fecha_estimada_entrega else None
            ),
            # El contrato devuelve la recepcion como un objeto aparte, o
            # null mientras la mercancia no haya llegado.
            "recepcion": (
                {
                    "bodegaId": self.bodega_id,
                    "cantidadRecibida": self.cantidad_recibida,
                    "fechaRecepcion": (
                        self.fecha_recepcion.isoformat() if self.fecha_recepcion else None
                    ),
                    "recibidaPor": self.recibida_por,
                }
                if self.fecha_recepcion
                else None
            ),
        }
