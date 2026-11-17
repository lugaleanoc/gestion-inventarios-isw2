"""Solicitudes de reposicion (RF18, RF19).

Ruta base: /api/reposicion/solicitudes

Una solicitud puede nacer de dos formas:
  - automatica: la crea Inventario cuando un producto queda bajo el minimo
    (ruta interna, no pasa por el Gateway);
  - manual: la crea un administrador o encargado de bodega.
"""

from datetime import datetime

from flask import Blueprint, jsonify, request

from ..clientes import producto_de, proveedor_principal_de, stock_minimo_de
from ..config import Config
from ..entrada import cuerpo_json, entero, texto
from ..errores import Conflicto, DatosInvalidos, NoEncontrado
from ..extensiones import db
from ..modelos import ESTADOS_ABIERTOS, Solicitud
from ..paginacion import entero_de_url, paginar
from ..seguridad import ADMIN, BODEGA, empresa_actual, identidad, roles_permitidos, solo_interno

bp = Blueprint("solicitudes", __name__, url_prefix="/api/reposicion/solicitudes")


def _buscar(solicitud_id, empresa_id):
    """Trae una solicitud de esta empresa, o lanza 404."""
    solicitud = Solicitud.query.filter_by(
        solicitud_id=solicitud_id, empresa_id=empresa_id
    ).first()
    if solicitud is None:
        raise NoEncontrado("La solicitud {} no existe".format(solicitud_id))
    return solicitud


def _solicitud_abierta(empresa_id, producto_id):
    """Devuelve la solicitud viva del producto, si ya hay una.

    Evita que cada venta que deja el producto bajo el minimo abra una
    solicitud nueva: mientras la anterior siga pendiente, aprobada o con
    orden emitida, se reutiliza.
    """
    return Solicitud.query.filter(
        Solicitud.empresa_id == empresa_id,
        Solicitud.producto_id == producto_id,
        Solicitud.estado.in_(ESTADOS_ABIERTOS),
    ).first()


def _cantidad_sugerida(stock_actual, stock_minimo):
    """Calcula cuanto conviene pedir.

    Se repone hasta tres veces el minimo (el factor es configurable), para
    no quedar justo en el umbral y volver a disparar la alerta enseguida.
    Siempre se pide al menos una unidad.
    """
    objetivo = stock_minimo * Config.FACTOR_REPOSICION
    return max(1, objetivo - (stock_actual or 0))


@bp.post("/automaticas")
@solo_interno("inventario")
def crear_automatica():
    """POST /solicitudes/automaticas  (interno, solo Inventario).

    Responde 201 si creo la solicitud, o 200 si ya existia una abierta
    para ese producto. Las dos son respuestas correctas: Inventario no
    tiene que saber si era la primera vez.
    """
    empresa_id = empresa_actual()
    datos = cuerpo_json("productoId")
    producto_id = entero(datos, "productoId", obligatorio=True)
    stock_actual = entero(datos, "stockActual") or 0

    existente = _solicitud_abierta(empresa_id, producto_id)
    if existente:
        return jsonify(existente.a_dic()), 200

    stock_minimo = stock_minimo_de(producto_id)
    solicitud = Solicitud(
        empresa_id=empresa_id,
        producto_id=producto_id,
        proveedor_id=proveedor_principal_de(producto_id),
        origen="automatica",
        stock_al_crear=stock_actual,
        stock_minimo=stock_minimo,
        cantidad_sugerida=_cantidad_sugerida(stock_actual, stock_minimo),
        estado="pendiente",
        # Queda constancia de que la creo el sistema y no una persona.
        creada_por="inventario",
    )
    db.session.add(solicitud)
    db.session.commit()
    return jsonify(solicitud.a_dic()), 201


@bp.get("")
def listar():
    """GET /solicitudes  -> lista paginada con filtros.

    Filtros: estado, productoId, origen, fechaDesde, fechaHasta.
    """
    empresa_id = empresa_actual()
    consulta = Solicitud.query.filter_by(empresa_id=empresa_id)

    estado = request.args.get("estado")
    if estado:
        consulta = consulta.filter_by(estado=estado)

    producto_id = entero_de_url("productoId")
    if producto_id is not None:
        consulta = consulta.filter_by(producto_id=producto_id)

    origen = request.args.get("origen")
    if origen:
        consulta = consulta.filter_by(origen=origen)

    for nombre, comparacion in (("fechaDesde", "desde"), ("fechaHasta", "hasta")):
        valor = request.args.get(nombre)
        if not valor:
            continue
        try:
            fecha = datetime.strptime(valor, "%Y-%m-%d")
        except ValueError:
            raise DatosInvalidos(
                "El parametro '{}' debe tener el formato AAAA-MM-DD".format(nombre)
            )
        if comparacion == "desde":
            consulta = consulta.filter(Solicitud.fecha_creacion >= fecha)
        else:
            consulta = consulta.filter(
                Solicitud.fecha_creacion <= fecha.replace(hour=23, minute=59, second=59)
            )

    # De la mas nueva a la mas vieja.
    consulta = consulta.order_by(Solicitud.fecha_creacion.desc(), Solicitud.solicitud_id.desc())
    return jsonify(paginar(consulta, lambda s: s.a_dic())), 200


@bp.post("")
@roles_permitidos(ADMIN, BODEGA)
def crear_manual():
    """POST /solicitudes  -> solicitud creada a mano."""
    empresa_id = empresa_actual()
    datos = cuerpo_json("productoId", "cantidadSugerida")
    producto_id = entero(datos, "productoId", obligatorio=True)
    cantidad = entero(datos, "cantidadSugerida", obligatorio=True, minimo=1)
    observacion = texto(datos, "observacion", maximo=200)

    # Si ya hay una solicitud viva del producto, pedir otra duplicaria la
    # compra. Se responde 409 con el numero de la que ya existe.
    existente = _solicitud_abierta(empresa_id, producto_id)
    if existente:
        raise Conflicto(
            "Ya existe una solicitud abierta para ese producto (numero {})".format(
                existente.solicitud_id
            )
        )

    # Se comprueba que el producto exista. Si Inventario no responde se
    # deja crear igual: la solicitud todavia tiene que aprobarla alguien.
    producto = producto_de(producto_id)
    if producto is not None and not producto.get("activo", True):
        raise DatosInvalidos("El producto {} esta inactivo".format(producto_id))

    solicitud = Solicitud(
        empresa_id=empresa_id,
        producto_id=producto_id,
        proveedor_id=proveedor_principal_de(producto_id),
        origen="manual",
        stock_minimo=stock_minimo_de(producto_id),
        cantidad_sugerida=cantidad,
        observacion=observacion,
        estado="pendiente",
        creada_por=identidad().quien(),
    )
    db.session.add(solicitud)
    db.session.commit()
    return jsonify(solicitud.a_dic()), 201


@bp.get("/<int:solicitud_id>")
def consultar(solicitud_id):
    """GET /solicitudes/{id}"""
    return jsonify(_buscar(solicitud_id, empresa_actual()).a_dic()), 200


@bp.post("/<int:solicitud_id>/aprobacion")
@roles_permitidos(ADMIN)
def aprobar(solicitud_id):
    """POST /solicitudes/{id}/aprobacion  -> la deja lista para comprar.

    El administrador puede autorizar una cantidad distinta de la
    sugerida; si no manda ninguna, se aprueba la sugerida.
    """
    empresa_id = empresa_actual()
    solicitud = _buscar(solicitud_id, empresa_id)

    if solicitud.estado != "pendiente":
        raise Conflicto(
            "Solo se aprueba una solicitud pendiente; esta esta '{}'".format(solicitud.estado)
        )

    # El cuerpo es opcional en esta ruta, por eso no se usa cuerpo_json.
    datos = request.get_json(silent=True) or {}
    cantidad = entero(datos, "cantidadAprobada", minimo=1)

    solicitud.cantidad_aprobada = cantidad or solicitud.cantidad_sugerida
    solicitud.estado = "aprobada"
    db.session.commit()
    return jsonify(solicitud.a_dic()), 200


@bp.post("/<int:solicitud_id>/rechazo")
@roles_permitidos(ADMIN)
def rechazar(solicitud_id):
    """POST /solicitudes/{id}/rechazo  -> la cierra sin comprar.

    El motivo es obligatorio: una solicitud rechazada sin explicacion no
    sirve para auditar despues por que no se repuso un producto.
    """
    empresa_id = empresa_actual()
    solicitud = _buscar(solicitud_id, empresa_id)

    if solicitud.estado != "pendiente":
        raise Conflicto(
            "Solo se rechaza una solicitud pendiente; esta esta '{}'".format(solicitud.estado)
        )

    datos = cuerpo_json("motivo")
    solicitud.motivo_rechazo = texto(datos, "motivo", maximo=200, obligatorio=True)
    solicitud.estado = "rechazada"
    db.session.commit()
    return jsonify(solicitud.a_dic()), 200
