"""Tabla de movimientos de dinero (RF21, RF22).

Un movimiento es un ingreso, un egreso o un ajuste, en un local y con un
medio de pago (efectivo, tarjeta o qr).

Integridad (RNF20): los movimientos NUNCA se editan ni se borran. Si uno
tiene un error, se crea un movimiento de tipo "ajuste" que lo referencia
(columna ajusta_a) y corrige la diferencia. Por eso este servicio no tiene
rutas PUT, PATCH ni DELETE.
"""

from ..extensiones import db
from ..fechas import a_texto, ahora

TIPOS = ["ingreso", "egreso", "ajuste"]
ORIGENES = ["venta", "manual", "ajuste"]
MEDIOS_PAGO = ["efectivo", "tarjeta", "qr"]
CANALES = ["tienda_fisica", "tienda_web"]


class Movimiento(db.Model):
    __tablename__ = "movimientos"
    __table_args__ = (
        # Idempotencia: una venta solo puede tener UN ingreso por empresa.
        # Aunque dos reintentos lleguen al mismo tiempo, MySQL rechaza el
        # segundo. (MySQL permite varios NULL, asi que los movimientos que no
        # vienen de una venta no chocan entre si.)
        db.UniqueConstraint("empresa_id", "venta_id", name="uq_movimiento_venta"),
        # Indice para el balance diario: empresa + local + fecha.
        db.Index("ix_movimientos_empresa_local_fecha", "empresa_id", "local_id", "fecha_hora"),
    )

    movimiento_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    empresa_id = db.Column(db.Integer, nullable=False)
    local_id = db.Column(db.Integer, nullable=False)
    tipo = db.Column(db.String(10), nullable=False)          # ingreso | egreso | ajuste
    origen = db.Column(db.String(10), nullable=False)        # venta | manual | ajuste
    canal = db.Column(db.String(20), nullable=True)          # solo si viene de una venta
    medio_pago = db.Column(db.String(10), nullable=False)
    # Siempre positivo en ingresos y egresos; en un ajuste puede ser negativo.
    monto = db.Column(db.Numeric(14, 2), nullable=False)
    concepto = db.Column(db.String(200), nullable=False)
    venta_id = db.Column(db.Integer, nullable=True)          # referencia logica (Ventas)
    # Movimiento original que corrige este ajuste (misma tabla, misma base).
    ajusta_a = db.Column(db.Integer, db.ForeignKey("movimientos.movimiento_id"), nullable=True)
    registrado_por = db.Column(db.String(50), nullable=False)  # X-Usuario-Id o nombre del servicio
    fecha_hora = db.Column(db.DateTime, nullable=False, default=ahora)

    def a_dic(self, con_ajustes=True):
        datos = {
            "movimientoId": self.movimiento_id,
            "empresaId": self.empresa_id,
            "localId": self.local_id,
            "tipo": self.tipo,
            "origen": self.origen,
            "canal": self.canal,
            "medioPago": self.medio_pago,
            "monto": float(self.monto),
            "concepto": self.concepto,
            "ventaId": self.venta_id,
            "ajustaA": self.ajusta_a,
            "registradoPor": self.registrado_por,
            "fechaHora": a_texto(self.fecha_hora),
        }
        if con_ajustes:
            # Ids de los ajustes que corrigen a este movimiento.
            ajustes = (Movimiento.query.with_entities(Movimiento.movimiento_id)
                       .filter_by(empresa_id=self.empresa_id, ajusta_a=self.movimiento_id)
                       .order_by(Movimiento.movimiento_id).all())
            datos["ajustes"] = [fila[0] for fila in ajustes]
        return datos
