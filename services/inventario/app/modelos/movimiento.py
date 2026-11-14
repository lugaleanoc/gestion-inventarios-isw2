"""Tabla de movimientos: el kardex (RF04, RF10, RF13).

Cada vez que entra o sale mercancia queda una fila aqui, con quien lo hizo
y cuando. Es el historial que permite auditar el inventario.

Integridad (RNF20): estas filas NO se editan ni se borran. Si un movimiento
quedo mal, se registra otro de tipo 'ajuste' que apunta al original con el
campo ajusta_a. Asi siempre se puede reconstruir que paso.
"""

from datetime import datetime

from ..extensiones import db

# Tipos validos, tal como los fija el contrato.
# Los dos ultimos no los puede crear una persona: los genera el propio
# servicio cuando Ventas descuenta stock o Reposicion recibe una orden.
TIPOS_MOVIMIENTO = (
    "entrada",
    "salida",
    "ajuste",
    "traslado",
    "devolucion_cliente",
    "devolucion_proveedor",
    "venta",
    "recepcion_orden",
)

# Tipos que suman unidades a la bodega. Los demas restan (salvo el ajuste,
# que puede venir con cantidad negativa y por eso se trata aparte).
TIPOS_QUE_SUMAN = ("entrada", "devolucion_cliente", "recepcion_orden")


class Movimiento(db.Model):
    __tablename__ = "movimientos"
    __table_args__ = (
        # Indice pensado para la consulta mas comun del kardex:
        # "movimientos de este producto, del mas nuevo al mas viejo".
        db.Index("ix_mov_empresa_producto_fecha", "empresa_id", "producto_id", "fecha_hora"),
    )

    movimiento_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    empresa_id = db.Column(db.Integer, nullable=False, index=True)
    tipo = db.Column(db.String(30), nullable=False)
    producto_id = db.Column(
        db.Integer, db.ForeignKey("productos.producto_id"), nullable=False
    )
    bodega_id = db.Column(db.Integer, db.ForeignKey("bodegas.bodega_id"), nullable=False)
    # Solo se llena en los traslados: la bodega a la que va la mercancia.
    bodega_destino_id = db.Column(
        db.Integer, db.ForeignKey("bodegas.bodega_id"), nullable=True
    )
    cantidad = db.Column(db.Integer, nullable=False)
    # Saldo que quedo en la bodega despues de este movimiento. Se guarda
    # para poder leer el kardex sin tener que sumar toda la historia.
    saldo_resultante = db.Column(db.Integer, nullable=False)
    motivo = db.Column(db.String(200), nullable=False)
    # De donde viene el movimiento cuando lo genero otro servicio,
    # por ejemplo "venta:3021" u "orden:84".
    referencia = db.Column(db.String(60), nullable=True, index=True)
    # Quien lo hizo: "usuario:12" o "servicio:ventas" (RF10).
    registrado_por = db.Column(db.String(60), nullable=False)
    # Movimiento que este ajuste corrige (RNF20).
    ajusta_a = db.Column(db.Integer, db.ForeignKey("movimientos.movimiento_id"), nullable=True)
    # utcnow sin parentesis: se le pasa la funcion para que SQLAlchemy la
    # ejecute al insertar. Con parentesis guardaria siempre la hora del arranque.
    fecha_hora = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def a_dic(self):
        return {
            "movimientoId": self.movimiento_id,
            "tipo": self.tipo,
            "productoId": self.producto_id,
            "bodegaId": self.bodega_id,
            "bodegaDestinoId": self.bodega_destino_id,
            "cantidad": self.cantidad,
            "saldoResultante": self.saldo_resultante,
            "motivo": self.motivo,
            "referencia": self.referencia,
            "registradoPor": self.registrado_por,
            # isoformat() da "2026-11-13T14:35:02", el formato date-time del contrato.
            "fechaHora": self.fecha_hora.isoformat() if self.fecha_hora else None,
        }
