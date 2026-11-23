"""Tablas de alertas (RF27) y del dashboard (RF28).

Cada empresa tiene UNA fila en cada tabla, por eso la llave primaria es el
mismo empresa_id. Se crean con valores por defecto al registrar la empresa.
"""

from ..extensiones import db

# Valores con los que arranca una empresa nueva.
METRICAS_VALIDAS = [
    "ventas_por_canal",
    "productos_baja_rotacion",
    "productos_agotados",
    "estado_reposiciones",
    "balance_diario",
    "ingresos_egresos",
    "valor_inventario",
]
METRICAS_POR_DEFECTO = ["ventas_por_canal", "productos_agotados", "balance_diario"]
PERIODOS_VALIDOS = ["hoy", "semana", "mes"]


class ConfigAlertas(db.Model):
    """Que alertas quiere ver la empresa en el panel web."""

    __tablename__ = "config_alertas"

    empresa_id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    stock_minimo = db.Column(db.Boolean, nullable=False, default=True)
    producto_agotado = db.Column(db.Boolean, nullable=False, default=True)
    reposicion_pendiente = db.Column(db.Boolean, nullable=False, default=True)

    def a_dic(self):
        return {
            "stockMinimo": self.stock_minimo,
            "productoAgotado": self.producto_agotado,
            "reposicionPendiente": self.reposicion_pendiente,
        }


class ConfigDashboard(db.Model):
    """Que metricas muestra el dashboard y con que filtros arranca."""

    __tablename__ = "config_dashboard"

    empresa_id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    # Lista de metricas; db.JSON la guarda como texto JSON en MySQL.
    metricas = db.Column(db.JSON, nullable=False)
    # null = todos los locales
    local_por_defecto = db.Column(db.Integer, nullable=True)
    periodo_por_defecto = db.Column(db.String(10), nullable=False, default="semana")

    def a_dic(self):
        return {
            "metricas": self.metricas,
            "preferencias": {
                "localPorDefecto": self.local_por_defecto,
                "periodoPorDefecto": self.periodo_por_defecto,
            },
        }
