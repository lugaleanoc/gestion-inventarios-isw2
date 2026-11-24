import json

from datetime import timedelta

from flask import Blueprint, g, jsonify

from . import cache, informes, parametros
from .auth import ADM, ADM_BOD, ADM_VEN, TODOS, requiere
from .errores import ApiError
from .fuentes import Fuentes
from .tiempo import ahora, iso

bp = Blueprint("reportes", __name__, url_prefix="/api/reportes")


def servir(tipo, claves, construir):
    forzar = parametros.refrescar()
    if not forzar:
        guardado = cache.buscar(g.empresa_id, tipo, claves)
        if guardado is not None:
            cuerpo, fuentes, generado_en = guardado
            return jsonify(
                {"generadoEn": generado_en, "desdeCache": True, "fuentesNoDisponibles": fuentes, **cuerpo}
            )
    fuentes = Fuentes(g.empresa_id)
    cuerpo = construir(fuentes)
    generado = ahora()
    cache.guardar(g.empresa_id, tipo, claves, cuerpo, fuentes.no_disponibles, generado)
    return jsonify(
        {
            "generadoEn": iso(generado),
            "desdeCache": False,
            "fuentesNoDisponibles": list(fuentes.no_disponibles),
            **cuerpo,
        }
    )


@bp.get("/dashboard")
@requiere(TODOS)
def dashboard():
    local_id = parametros.entero_positivo("localId")
    desde = parametros.fecha("fechaDesde")
    hasta = parametros.fecha("fechaHasta")
    claves = {"localId": local_id, "fechaDesde": str(desde), "fechaHasta": str(hasta)}

    def construir(f):
        metricas, preferencias = informes.configuracion_dashboard(f)
        p = periodo_del_dashboard(local_id, desde, hasta, preferencias)
        return {
            "metricas": {nombre: informes.metrica(nombre, f, p) for nombre in metricas},
        }

    return servir("dashboard", claves, construir)


def periodo_del_dashboard(local_id, desde, hasta, preferencias):
    hasta = hasta or parametros.hoy()
    desde = desde or hasta - timedelta(days=informes.dias_del_periodo(preferencias))
    if desde > hasta:
        raise parametros.invalido("fechaDesde no puede ser posterior a fechaHasta")
    return parametros.Periodo(local_id or informes.local_por_defecto(preferencias), desde, hasta)


@bp.get("/ventas-por-canal")
@requiere(ADM_VEN)
def ventas_por_canal():
    p = parametros.periodo_desde_consulta(parametros.entero_positivo("localId"))
    return servir("ventas-por-canal", p.clave, lambda f: informes.ventas(f, p))


@bp.get("/inventario")
@requiere(ADM_BOD)
def inventario():
    p = parametros.periodo_desde_consulta(parametros.entero_positivo("localId"))
    return servir("inventario", p.clave, lambda f: informes.inventario(f, p))


@bp.get("/productos-agotados")
@requiere(ADM_BOD)
def productos_agotados():
    p = parametros.periodo_desde_consulta()
    return servir("productos-agotados", {}, lambda f: informes.productos_agotados(f, p))


@bp.get("/reposiciones")
@requiere(ADM_BOD)
def reposiciones():
    return servir("reposiciones", {}, lambda f: informes.reposiciones(f))


@bp.get("/balance")
@requiere(ADM_VEN)
def balance():
    p = parametros.periodo_desde_consulta(parametros.entero_positivo("localId"))
    return servir("balance", p.clave, lambda f: informes.balance(f, p))


@bp.get("/locales/<int:local_id>")
@requiere(ADM)
def reporte_de_local(local_id):
    p = parametros.periodo_desde_consulta(local_id)

    def construir(f):
        cuerpo = informes.reporte_de_local(f, p, local_id)
        if cuerpo is None:
            raise ApiError(404, "LOCAL_NO_ENCONTRADO", f"No existe el local {local_id}")
        return cuerpo

    return servir("local", p.clave, construir)
