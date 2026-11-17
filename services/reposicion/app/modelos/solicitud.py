"""Tabla de solicitudes de reposicion (RF18, RF19).

Una solicitud nace de dos maneras:
  - automatica: Inventario avisa que un producto quedo bajo el minimo.
  - manual: un administrador o encargado de bodega la crea el mismo.

Ciclo de vida del estado:

    pendiente --aprobacion--> aprobada --se emite la orden--> en_orden
        |                                                        |
        +--rechazo--> rechazada                    llega la mercancia
                                                                 v
                                                             recibida
"""

from datetime import datetime

from ..extensiones import db

ESTADOS_SOLICITUD = ("pendiente", "aprobada", "rechazada", "en_orden", "recibida")

# Estados en los que la solicitud todavia esta "viva". Sirven para no
# abrir dos solicitudes del mismo producto al tiempo: mientras una siga
# abierta, un nuevo aviso de stock bajo no crea otra.
ESTADOS_ABIERTOS = ("pendiente", "aprobada", "en_orden")


class Solicitud(db.Model):
    __tablename__ = "solicitudes"
    __table_args__ = (
        db.Index("ix_solicitud_empresa_producto_estado", "empresa_id", "producto_id", "estado"),
    )

    solicitud_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    empresa_id = db.Column(db.Integer, nullable=False, index=True)
    # Referencia logica: el producto vive en el servicio de Inventario.
    producto_id = db.Column(db.Integer, nullable=False, index=True)
    # Referencia logica: el proveedor vive en el servicio de Proveedores.
    # Puede quedar vacio si el producto no tiene proveedor asociado.
    proveedor_id = db.Column(db.Integer, nullable=True, index=True)
    origen = db.Column(db.String(20), nullable=False)  # automatica | manual

    # Foto del momento en que se creo la solicitud. Se guarda aunque el
    # stock cambie despues, para poder explicar por que se pidio.
    stock_al_crear = db.Column(db.Integer, nullable=True)
    stock_minimo = db.Column(db.Integer, nullable=True)

    cantidad_sugerida = db.Column(db.Integer, nullable=False)
    # Lo que finalmente autorizo el administrador: puede ser distinto de
    # lo sugerido. Vacio mientras no se apruebe.
    cantidad_aprobada = db.Column(db.Integer, nullable=True)

    estado = db.Column(db.String(20), nullable=False, default="pendiente")
    motivo_rechazo = db.Column(db.String(200), nullable=True)
    # Observacion que escribe quien crea una solicitud manual. No va en la
    # respuesta porque el contrato no la incluye, pero queda registrada.
    observacion = db.Column(db.String(200), nullable=True)

    # usuarioId, o 'inventario' si la creo el sistema.
    creada_por = db.Column(db.String(60), nullable=False)
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def a_dic(self):
        """Devuelve la solicitud con los nombres de campo del contrato."""
        return {
            "solicitudId": self.solicitud_id,
            "productoId": self.producto_id,
            "proveedorId": self.proveedor_id,
            "origen": self.origen,
            "stockAlCrear": self.stock_al_crear,
            "stockMinimo": self.stock_minimo,
            "cantidadSugerida": self.cantidad_sugerida,
            "cantidadAprobada": self.cantidad_aprobada,
            "estado": self.estado,
            "motivoRechazo": self.motivo_rechazo,
            "creadaPor": self.creada_por,
            "fechaCreacion": self.fecha_creacion.isoformat() if self.fecha_creacion else None,
        }
