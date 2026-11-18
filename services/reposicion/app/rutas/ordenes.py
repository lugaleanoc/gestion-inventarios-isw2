"""Ordenes de compra y recepcion de mercancia (RF06, RF20).

Ruta base: /api/reposicion/ordenes

Una orden sale de una solicitud ya aprobada. Cuando llega la mercancia se
registra la recepcion, y es ahi cuando Inventario sube el stock.
"""

from datetime import date, datetime

from flask import Blueprint, jsonify, request

from ..clientes import registrar_entrada
from ..entrada import cuerpo_json, entero, texto
from ..errores import Conflicto, DatosInvalidos, NoEncontrado
from ..extensiones import db
from ..modelos import Orden, Solicitud
from ..paginacion import entero_de_url, paginar
from ..seguridad import ADMIN, BODEGA, empresa_actual, identidad, roles_permitidos

bp = Blueprint("ordenes", __name__, url_prefix="/api/reposicion")


def _buscar_orden(orden_id, empresa_id):
    """Trae una orden de esta empresa, o lanza 404."""
    orden = Orden.query.filter_by(orden_id=orden_id, empresa_id=empresa_id).first()
    if orden is None:
        raise NoEncontrado("La orden {} no existe".format(orden_id))
    return orden


@bp.get("/ordenes")
def listar():
    """GET /ordenes  -> lista paginada, filtrable por estado y proveedor."""
    empresa_id = empresa_actual()
    consulta = Orden.query.filter_by(empresa_id=empresa_id)

    estado = request.args.get("estado")
    if estado:
        consulta = consulta.filter_by(estado=estado)

    proveedor_id = entero_de_url("proveedorId")
    if proveedor_id is not None:
        consulta = consulta.filter_by(proveedor_id=proveedor_id)

    consulta = consulta.order_by(Orden.fecha_emision.desc(), Orden.orden_id.desc())
    return jsonify(paginar(consulta, lambda o: o.a_dic())), 200


@bp.post("/ordenes")
@roles_permitidos(ADMIN)
def emitir():
    """POST /ordenes  -> emite la orden de una solicitud aprobada.

    La solicitud pasa a 'en_orden', para que no se le pueda emitir una
    segunda orden por lo mismo.
    """
    empresa_id = empresa_actual()
    datos = cuerpo_json("solicitudId")
    solicitud_id = entero(datos, "solicitudId", obligatorio=True)

    solicitud = Solicitud.query.filter_by(
        solicitud_id=solicitud_id, empresa_id=empresa_id
    ).first()
    if solicitud is None:
        raise NoEncontrado("La solicitud {} no existe".format(solicitud_id))

    if solicitud.estado != "aprobada":
        raise Conflicto(
            "La solicitud no esta aprobada; esta '{}'".format(solicitud.estado)
        )

    # Fecha estimada de entrega, opcional.
    fecha_estimada = None
    valor = datos.get("fechaEstimadaEntrega")
    if valor:
        try:
            fecha_estimada = datetime.strptime(str(valor), "%Y-%m-%d").date()
        except ValueError:
            raise DatosInvalidos("'fechaEstimadaEntrega' debe tener el formato AAAA-MM-DD")
        if fecha_estimada < date.today():
            raise DatosInvalidos("La fecha estimada de entrega no puede estar en el pasado")

    orden = Orden(
        empresa_id=empresa_id,
        solicitud_id=solicitud.solicitud_id,
        proveedor_id=solicitud.proveedor_id,
        producto_id=solicitud.producto_id,
        # Se compra lo aprobado; si falta, lo sugerido.
        cantidad=solicitud.cantidad_aprobada or solicitud.cantidad_sugerida,
        estado="emitida",
        fecha_estimada_entrega=fecha_estimada,
    )
    solicitud.estado = "en_orden"

    db.session.add(orden)
    db.session.commit()
    return jsonify(orden.a_dic()), 201


@bp.get("/ordenes/<int:orden_id>")
def consultar(orden_id):
    """GET /ordenes/{id}"""
    return jsonify(_buscar_orden(orden_id, empresa_actual()).a_dic()), 200


@bp.post("/ordenes/<int:orden_id>/recepcion")
@roles_permitidos(ADMIN, BODEGA)
def recibir(orden_id):
    """POST /ordenes/{id}/recepcion  -> llega la mercancia.

    Es el punto donde este servicio y el de Inventario tienen que quedar
    de acuerdo. El orden de los pasos importa:

      1. Se marca la orden como recibida, sin confirmar todavia.
      2. Se le avisa a Inventario que entro la mercancia.
      3. Solo si Inventario respondio bien, se confirma el cambio.

    Si Inventario no responde, se deshace todo y se devuelve 503: la
    orden sigue emitida y se puede volver a recibir. Al reves (confirmar
    primero y avisar despues) quedaria una orden recibida con el stock
    sin subir, que es el error peor de los dos.
    """
    empresa_id = empresa_actual()
    orden = _buscar_orden(orden_id, empresa_id)

    if orden.estado != "emitida":
        raise Conflicto(
            "Solo se recibe una orden emitida; esta esta '{}'".format(orden.estado)
        )

    datos = cuerpo_json("bodegaId", "cantidadRecibida")
    bodega_id = entero(datos, "bodegaId", obligatorio=True)
    cantidad_recibida = entero(datos, "cantidadRecibida", obligatorio=True, minimo=1)

    if cantidad_recibida > orden.cantidad:
        raise Conflicto(
            "Se intentan recibir {} unidades y la orden es de {}".format(
                cantidad_recibida, orden.cantidad
            )
        )

    solicitud = Solicitud.query.filter_by(
        solicitud_id=orden.solicitud_id, empresa_id=empresa_id
    ).first()

    try:
        # Paso 1: se escribe el cambio, sin confirmarlo.
        orden.estado = "recibida"
        orden.bodega_id = bodega_id
        orden.cantidad_recibida = cantidad_recibida
        orden.fecha_recepcion = datetime.utcnow()
        orden.recibida_por = identidad().quien()
        if solicitud:
            solicitud.estado = "recibida"
        db.session.flush()

        # Paso 2: Inventario sube el stock. Si falla, lanza 503.
        registrar_entrada(orden.orden_id, orden.producto_id, bodega_id, cantidad_recibida)

        # Paso 3: ahora si se confirma.
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify(orden.a_dic()), 200


@bp.post("/ordenes/<int:orden_id>/cancelacion")
@roles_permitidos(ADMIN)
def cancelar(orden_id):
    """POST /ordenes/{id}/cancelacion  -> se anula la orden.

    La solicitud vuelve a 'aprobada', no a 'pendiente': ya alguien la
    autorizo, lo que se cayo fue la compra. Asi se le puede emitir otra
    orden, por ejemplo a otro proveedor, sin aprobarla de nuevo.
    """
    empresa_id = empresa_actual()
    orden = _buscar_orden(orden_id, empresa_id)

    if orden.estado != "emitida":
        raise Conflicto(
            "Solo se cancela una orden emitida; esta esta '{}'".format(orden.estado)
        )

    datos = cuerpo_json("motivo")
    orden.motivo_cancelacion = texto(datos, "motivo", maximo=200, obligatorio=True)
    orden.estado = "cancelada"

    solicitud = Solicitud.query.filter_by(
        solicitud_id=orden.solicitud_id, empresa_id=empresa_id
    ).first()
    if solicitud:
        solicitud.estado = "aprobada"

    db.session.commit()
    return jsonify(orden.a_dic()), 200


@bp.get("/resumen")
def resumen():
    """GET /resumen  -> cuantas solicitudes y ordenes hay en cada estado.

    Lo consulta el microservicio de Reportes para el dashboard. Se
    resuelve con dos GROUP BY, no contando estado por estado.
    """
    empresa_id = empresa_actual()

    solicitudes = (
        db.session.query(Solicitud.estado, db.func.count(Solicitud.solicitud_id))
        .filter(Solicitud.empresa_id == empresa_id)
        .group_by(Solicitud.estado)
        .all()
    )
    ordenes = (
        db.session.query(Orden.estado, db.func.count(Orden.orden_id))
        .filter(Orden.empresa_id == empresa_id)
        .group_by(Orden.estado)
        .all()
    )

    return (
        jsonify(
            {
                "solicitudes": {estado: total for estado, total in solicitudes},
                "ordenes": {estado: total for estado, total in ordenes},
            }
        ),
        200,
    )
