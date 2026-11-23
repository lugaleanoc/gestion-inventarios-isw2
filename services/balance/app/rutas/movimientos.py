"""Movimientos de dinero (RF21, RF22, RNF20).

Ruta base: /api/balance/movimientos

    POST ""                    ingreso o egreso manual (administrador, vendedor)
    GET  ""                    listar movimientos (paginado)
    POST /ventas               ingreso de una venta (interna, SOLO la llama Ventas)
    GET  /{id}                 consultar un movimiento y sus ajustes
    POST /{id}/ajustes         corregir un movimiento con un ajuste (administrador)

No hay PUT ni DELETE: un movimiento nunca se modifica (RNF20).
"""

from flask import Blueprint, current_app, jsonify
from sqlalchemy.exc import IntegrityError

from ..entrada import cuerpo_json, decimal, entero, texto
from ..errores import Conflicto, DatosInvalidos, NoEncontrado
from ..extensiones import db
from ..fechas import ahora, desde_texto
from ..modelos import Movimiento
from ..modelos.movimiento import CANALES, MEDIOS_PAGO, ORIGENES, TIPOS
from ..paginacion import entero_de_url, fecha_de_url, opcion_de_url, paginar, rango_del_dia
from ..seguridad import ADMIN, VENDEDOR, empresa_actual, identidad, permitir

bp = Blueprint("movimientos", __name__, url_prefix="/api/balance/movimientos")


def _medio_pago(datos):
    medio = datos.get("medioPago")
    if medio not in MEDIOS_PAGO:
        raise DatosInvalidos("El campo medioPago debe ser efectivo, tarjeta o qr")
    return medio


def _monto_positivo(datos):
    """El monto de un ingreso o egreso debe ser mayor que cero."""
    monto = decimal(datos, "monto", obligatorio=True)
    if monto <= 0:
        raise DatosInvalidos("El monto debe ser mayor que cero")
    return round(monto, 2)


def _guardar(movimiento):
    db.session.add(movimiento)
    db.session.commit()
    return jsonify(movimiento.a_dic()), 201


@bp.post("")
@permitir(roles=[ADMIN, VENDEDOR])
def registrar_manual():
    """POST /api/balance/movimientos  - ingreso o egreso que no viene de una venta,
    por ejemplo la base de caja (ingreso) o el pago de un domicilio (egreso)."""
    datos = cuerpo_json("localId", "tipo", "medioPago", "monto", "concepto")
    tipo = datos.get("tipo")
    if tipo not in ("ingreso", "egreso"):
        raise DatosInvalidos("El campo tipo debe ser ingreso o egreso (los ajustes van por /ajustes)")

    return _guardar(Movimiento(
        empresa_id=empresa_actual(),
        local_id=entero(datos, "localId", obligatorio=True, minimo=1),
        tipo=tipo,
        origen="manual",
        medio_pago=_medio_pago(datos),
        monto=_monto_positivo(datos),
        concepto=texto(datos, "concepto", maximo=200, obligatorio=True),
        registrado_por=identidad().quien(),
        fecha_hora=ahora(),
    ))


@bp.post("/ventas")
@permitir(servicios=["ventas"])
def registrar_ingreso_venta():
    """POST /api/balance/movimientos/ventas  (interna, solo X-Servicio-Origen: ventas)

    Idempotente por ventaId: si el ingreso de esa venta ya existe, responde
    409 VENTA_YA_REGISTRADA y NO lo duplica. Asi Ventas puede reintentar
    sin miedo.
    """
    empresa_id = empresa_actual()
    datos = cuerpo_json("ventaId", "localId", "canal", "medioPago", "monto", "fechaHora")
    venta_id = entero(datos, "ventaId", obligatorio=True, minimo=1)
    canal = datos.get("canal")
    if canal not in CANALES:
        raise DatosInvalidos("El campo canal debe ser tienda_fisica o tienda_web")
    fecha = desde_texto(datos.get("fechaHora"))
    if fecha is None:
        raise DatosInvalidos("El campo fechaHora debe ser una fecha ISO 8601, por ejemplo 2026-10-23T15:42:10-05:00")

    def ya_registrada():
        return Conflicto("El ingreso de la venta {} ya fue registrado".format(venta_id),
                         error="VENTA_YA_REGISTRADA")

    if Movimiento.query.filter_by(empresa_id=empresa_id, venta_id=venta_id).first():
        raise ya_registrada()

    movimiento = Movimiento(
        empresa_id=empresa_id,
        local_id=entero(datos, "localId", obligatorio=True, minimo=1),
        tipo="ingreso",
        origen="venta",
        canal=canal,
        medio_pago=_medio_pago(datos),
        monto=_monto_positivo(datos),
        concepto="Venta {}".format(venta_id),
        venta_id=venta_id,
        registrado_por=identidad().quien(),  # "ventas"
        fecha_hora=fecha,
    )
    try:
        return _guardar(movimiento)
    except IntegrityError:
        # Dos reintentos llegaron casi al mismo tiempo y el otro gano:
        # la restriccion UNIQUE de MySQL impidio el duplicado.
        db.session.rollback()
        current_app.logger.info("Ingreso duplicado de la venta %s rechazado por la BD", venta_id)
        raise ya_registrada()


@bp.get("")
@permitir(roles=[ADMIN, VENDEDOR], servicios=["reportes"])
def listar():
    """GET /api/balance/movimientos  (paginado, el mas reciente primero)."""
    consulta = Movimiento.query.filter_by(empresa_id=empresa_actual())

    local_id = entero_de_url("localId")
    if local_id is not None:
        consulta = consulta.filter_by(local_id=local_id)
    for parametro, columna, opciones in (("tipo", "tipo", TIPOS),
                                         ("origen", "origen", ORIGENES),
                                         ("medioPago", "medio_pago", MEDIOS_PAGO)):
        valor = opcion_de_url(parametro, opciones)
        if valor is not None:
            consulta = consulta.filter(getattr(Movimiento, columna) == valor)

    desde = fecha_de_url("fechaDesde")
    hasta = fecha_de_url("fechaHasta")
    if desde or hasta:
        inicio, fin = rango_del_dia(desde or hasta, hasta or desde)
        consulta = consulta.filter(Movimiento.fecha_hora >= inicio, Movimiento.fecha_hora < fin)

    consulta = consulta.order_by(Movimiento.fecha_hora.desc(), Movimiento.movimiento_id.desc())
    return jsonify(paginar(consulta, lambda m: m.a_dic())), 200


def _buscar(movimiento_id):
    """Un movimiento de otra empresa responde 404, igual que uno que no existe."""
    movimiento = Movimiento.query.filter_by(movimiento_id=movimiento_id,
                                            empresa_id=empresa_actual()).first()
    if movimiento is None:
        raise NoEncontrado("El movimiento {} no existe".format(movimiento_id))
    return movimiento


@bp.get("/<int:movimiento_id>")
@permitir(roles=[ADMIN, VENDEDOR], servicios=["reportes"])
def consultar(movimiento_id):
    """GET /api/balance/movimientos/{id}"""
    return jsonify(_buscar(movimiento_id).a_dic()), 200


@bp.post("/<int:movimiento_id>/ajustes")
@permitir(roles=[ADMIN])
def registrar_ajuste(movimiento_id):
    """POST /api/balance/movimientos/{id}/ajustes  (administrador)

    Crea un movimiento NUEVO de tipo ajuste que corrige al original, sin
    tocarlo. El monto puede ser negativo para restar. El ajuste usa el
    mismo local y medio de pago del original, y cuenta en el balance del
    dia en que se registra.
    """
    original = _buscar(movimiento_id)
    datos = cuerpo_json("monto", "motivo")
    monto = round(decimal(datos, "monto", obligatorio=True), 2)
    if monto == 0:
        raise DatosInvalidos("Un ajuste de 0 no corrige nada")

    return _guardar(Movimiento(
        empresa_id=original.empresa_id,
        local_id=original.local_id,
        tipo="ajuste",
        origen="ajuste",
        canal=original.canal,
        medio_pago=original.medio_pago,
        monto=monto,
        concepto=texto(datos, "motivo", maximo=200, obligatorio=True),
        ajusta_a=original.movimiento_id,
        registrado_por=identidad().quien(),
        fecha_hora=ahora(),
    ))
