"""Alertas (RF27) y dashboard (RF28).

    GET/PUT /api/configuracion/alertas     que alertas estan activas
    GET/PUT /api/configuracion/dashboard   metricas y preferencias del dashboard

Si una empresa todavia no tiene su fila (por ejemplo, porque se creo antes
de existir estas tablas), el GET devuelve los valores por defecto y el PUT
crea la fila.
"""

from flask import Blueprint, jsonify

from ..entrada import booleano, cuerpo_json, entero
from ..errores import DatosInvalidos
from ..extensiones import db
from ..modelos import ConfigAlertas, ConfigDashboard
from ..modelos.preferencias import METRICAS_POR_DEFECTO, METRICAS_VALIDAS, PERIODOS_VALIDOS
from ..seguridad import ADMIN, TODOS_LOS_ROLES, empresa_actual, permitir

bp = Blueprint("preferencias", __name__, url_prefix="/api/configuracion")


def _alertas(empresa_id):
    """Fila de alertas de la empresa (nueva, sin guardar, si no existe)."""
    fila = db.session.get(ConfigAlertas, empresa_id)
    if fila is None:
        fila = ConfigAlertas(empresa_id=empresa_id, stock_minimo=True,
                             producto_agotado=True, reposicion_pendiente=True)
    return fila


def _dashboard(empresa_id):
    """Fila del dashboard de la empresa (nueva, sin guardar, si no existe)."""
    fila = db.session.get(ConfigDashboard, empresa_id)
    if fila is None:
        fila = ConfigDashboard(empresa_id=empresa_id, metricas=list(METRICAS_POR_DEFECTO),
                               local_por_defecto=None, periodo_por_defecto="semana")
    return fila


# Alertas
@bp.get("/alertas")
@permitir(roles=TODOS_LOS_ROLES, servicios=("inventario",))
def consultar_alertas():
    """GET /api/configuracion/alertas"""
    return jsonify(_alertas(empresa_actual()).a_dic()), 200


@bp.put("/alertas")
@permitir(roles=[ADMIN])
def configurar_alertas():
    """PUT /api/configuracion/alertas  (rol administrador)

    Cada alerta se activa o desactiva por separado; las que no se envian
    se quedan como estaban.
    """
    fila = _alertas(empresa_actual())
    datos = cuerpo_json()
    for campo_json, columna in (("stockMinimo", "stock_minimo"),
                                ("productoAgotado", "producto_agotado"),
                                ("reposicionPendiente", "reposicion_pendiente")):
        valor = booleano(datos, campo_json)
        if valor is not None:
            setattr(fila, columna, valor)

    db.session.add(fila)  # si la fila es nueva, esto la inserta
    db.session.commit()
    return jsonify(fila.a_dic()), 200


# Dashboard
@bp.get("/dashboard")
@permitir(roles=TODOS_LOS_ROLES, servicios=("reportes",))
def consultar_dashboard():
    """GET /api/configuracion/dashboard"""
    return jsonify(_dashboard(empresa_actual()).a_dic()), 200


@bp.put("/dashboard")
@permitir(roles=[ADMIN])
def configurar_dashboard():
    """PUT /api/configuracion/dashboard  (rol administrador)"""
    fila = _dashboard(empresa_actual())
    datos = cuerpo_json()

    if "metricas" in datos:
        metricas = datos["metricas"]
        if not isinstance(metricas, list) or any(m not in METRICAS_VALIDAS for m in metricas):
            raise DatosInvalidos("'metricas' debe ser una lista con valores de: {}".format(
                ", ".join(METRICAS_VALIDAS)))
        fila.metricas = metricas

    preferencias = datos.get("preferencias") or {}
    if not isinstance(preferencias, dict):
        raise DatosInvalidos("'preferencias' debe ser un objeto")
    if "localPorDefecto" in preferencias:
        # null es valido: significa "todos los locales".
        fila.local_por_defecto = entero(preferencias, "localPorDefecto", minimo=1)
    if "periodoPorDefecto" in preferencias:
        periodo = preferencias["periodoPorDefecto"]
        if periodo not in PERIODOS_VALIDOS:
            raise DatosInvalidos("'periodoPorDefecto' debe ser: {}".format(", ".join(PERIODOS_VALIDOS)))
        fila.periodo_por_defecto = periodo

    db.session.add(fila)
    db.session.commit()
    return jsonify(fila.a_dic()), 200
