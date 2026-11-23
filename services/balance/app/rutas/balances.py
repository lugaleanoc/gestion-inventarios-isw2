"""Balances (RF21, RF23).

    GET /api/balance/diario?localId=1&fecha=2026-11-20
        Balance de un local en un dia.
    GET /api/balance/reporte?fechaDesde=...&fechaHasta=...[&localId=1]
        Un balance por cada dia y local del periodo, mas los totales.

Formula (por medio de pago: efectivo, tarjeta, qr):

    disponible = ingresos - egresos + ajustes

"efectivo" disponible es el dinero que deberia haber en la caja.
"""

from flask import Blueprint, jsonify
from sqlalchemy import func

from ..errores import DatosInvalidos
from ..extensiones import db
from ..modelos import Movimiento
from ..modelos.movimiento import CANALES, MEDIOS_PAGO
from ..paginacion import entero_de_url, fecha_de_url, rango_del_dia
from ..seguridad import ADMIN, VENDEDOR, empresa_actual, permitir

bp = Blueprint("balances", __name__, url_prefix="/api/balance")


def _totales_vacios():
    """{"efectivo": 0, "tarjeta": 0, "qr": 0, "total": 0}"""
    return dict({medio: 0.0 for medio in MEDIOS_PAGO}, total=0.0)


def _balance_vacio(local_id, fecha):
    return {
        "localId": local_id,
        "fecha": fecha,
        "ingresos": _totales_vacios(),
        "egresos": _totales_vacios(),
        "ajustes": _totales_vacios(),
        "disponible": _totales_vacios(),
        "ventasPorCanal": {canal: 0.0 for canal in CANALES},
    }


def _sumar(balance, tipo, medio, monto):
    """Suma un monto en la seccion (ingresos/egresos/ajustes) y recalcula el disponible."""
    seccion = {"ingreso": "ingresos", "egreso": "egresos", "ajuste": "ajustes"}[tipo]
    # Los egresos restan; ingresos y ajustes suman (un ajuste negativo resta solo).
    signo = -1 if tipo == "egreso" else 1
    for destino, valor in ((balance[seccion], monto), (balance["disponible"], signo * monto)):
        # round(..., 2): el dinero va con 2 decimales y asi se evitan
        # resultados como 0.30000000000000004 de los numeros float.
        destino[medio] = round(destino[medio] + valor, 2)
        destino["total"] = round(destino["total"] + valor, 2)


def _calcular(empresa_id, desde, hasta, local_id=None):
    """Calcula los balances de [desde, hasta] agrupados por dia y local.

    Hace solo DOS consultas agrupadas (MySQL suma, no Python):
      1. SUM(monto) por dia, local, tipo y medio de pago
      2. SUM(monto) de los ingresos por venta, por dia, local y canal
    Devuelve un diccionario {(fecha, localId): balance}.
    """
    inicio, fin = rango_del_dia(desde, hasta)
    dia = func.date(Movimiento.fecha_hora)
    filtros = [Movimiento.empresa_id == empresa_id,
               Movimiento.fecha_hora >= inicio, Movimiento.fecha_hora < fin]
    if local_id is not None:
        filtros.append(Movimiento.local_id == local_id)

    balances = {}

    def balance_de(fecha, local):
        # func.date devuelve date en MySQL y texto en SQLite: str()[:10] sirve para los dos.
        clave = (str(fecha)[:10], local)
        if clave not in balances:
            balances[clave] = _balance_vacio(local, clave[0])
        return balances[clave]

    sumas = (db.session.query(dia, Movimiento.local_id, Movimiento.tipo, Movimiento.medio_pago,
                              func.sum(Movimiento.monto))
             .filter(*filtros)
             .group_by(dia, Movimiento.local_id, Movimiento.tipo, Movimiento.medio_pago))
    for fecha, local, tipo, medio, suma in sumas:
        _sumar(balance_de(fecha, local), tipo, medio, float(suma or 0))

    por_canal = (db.session.query(dia, Movimiento.local_id, Movimiento.canal, func.sum(Movimiento.monto))
                 .filter(*filtros, Movimiento.origen == "venta")
                 .group_by(dia, Movimiento.local_id, Movimiento.canal))
    for fecha, local, canal, suma in por_canal:
        canales = balance_de(fecha, local)["ventasPorCanal"]
        canales[canal] = round(canales[canal] + float(suma or 0), 2)

    return balances


@bp.get("/diario")
@permitir(roles=[ADMIN, VENDEDOR], servicios=["reportes"])
def diario():
    """GET /api/balance/diario?localId=1&fecha=AAAA-MM-DD  (los dos son obligatorios)"""
    local_id = entero_de_url("localId", obligatorio=True)
    fecha = fecha_de_url("fecha", obligatorio=True)
    balances = _calcular(empresa_actual(), fecha, fecha, local_id)
    # Si el dia no tuvo movimientos, el balance sale en ceros (no es un error).
    balance = balances.get((fecha.isoformat(), local_id), _balance_vacio(local_id, fecha.isoformat()))
    return jsonify(balance), 200


@bp.get("/reporte")
@permitir(roles=[ADMIN], servicios=["reportes"])
def reporte():
    """GET /api/balance/reporte?fechaDesde=...&fechaHasta=...[&localId=...]

    Solo aparecen los dias y locales que tuvieron movimientos.
    totales = suma del disponible de todo el periodo, por medio de pago.
    """
    desde = fecha_de_url("fechaDesde", obligatorio=True)
    hasta = fecha_de_url("fechaHasta", obligatorio=True)
    if desde > hasta:
        raise DatosInvalidos("fechaDesde no puede ser posterior a fechaHasta")

    balances = _calcular(empresa_actual(), desde, hasta, entero_de_url("localId"))
    lista = [balances[clave] for clave in sorted(balances)]

    totales = _totales_vacios()
    for balance in lista:
        for clave in totales:
            totales[clave] = round(totales[clave] + balance["disponible"][clave], 2)

    return jsonify({
        "fechaDesde": desde.isoformat(),
        "fechaHasta": hasta.isoformat(),
        "balances": lista,
        "totales": totales,
    }), 200
