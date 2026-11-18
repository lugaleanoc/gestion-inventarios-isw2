"""Bodegas o almacenes (RF05).

Ruta base: /api/inventario/bodegas
Una bodega pertenece a un local. El local lo administra el microservicio de
Configuracion, por eso aqui solo se guarda su numero (referencia logica).
"""

from flask import Blueprint, jsonify

from ..entrada import cuerpo_json, entero, texto
from ..errores import Conflicto, NoEncontrado
from ..extensiones import db
from ..modelos import Bodega, Stock
from ..paginacion import booleano_de_url, entero_de_url
from ..seguridad import ADMIN, empresa_actual, roles_permitidos

bp = Blueprint("bodegas", __name__, url_prefix="/api/inventario/bodegas")


def _buscar(bodega_id, empresa_id):
    """Trae una bodega de esta empresa, o lanza 404."""
    bodega = Bodega.query.filter_by(bodega_id=bodega_id, empresa_id=empresa_id).first()
    if bodega is None:
        raise NoEncontrado("La bodega {} no existe".format(bodega_id))
    return bodega


@bp.get("")
def listar():
    """GET /api/inventario/bodegas  -> lista, filtrable por local."""
    empresa_id = empresa_actual()
    consulta = Bodega.query.filter_by(empresa_id=empresa_id)

    local_id = entero_de_url("localId")
    if local_id is not None:
        consulta = consulta.filter_by(local_id=local_id)

    activo = booleano_de_url("activo", True)
    if activo is not None:
        consulta = consulta.filter_by(activo=activo)

    return jsonify([b.a_dic() for b in consulta.order_by(Bodega.nombre).all()]), 200


@bp.post("")
@roles_permitidos(ADMIN)
def crear():
    """POST /api/inventario/bodegas"""
    empresa_id = empresa_actual()
    datos = cuerpo_json("nombre", "localId")
    nombre = texto(datos, "nombre", maximo=100, obligatorio=True)
    local_id = entero(datos, "localId", obligatorio=True)

    # Dos bodegas del mismo local no pueden llamarse igual.
    if Bodega.query.filter_by(empresa_id=empresa_id, local_id=local_id, nombre=nombre).first():
        raise Conflicto(
            "El local {} ya tiene una bodega llamada '{}'".format(local_id, nombre)
        )

    bodega = Bodega(empresa_id=empresa_id, nombre=nombre, local_id=local_id)
    db.session.add(bodega)
    db.session.commit()
    return jsonify(bodega.a_dic()), 201


@bp.get("/<int:bodega_id>")
def consultar(bodega_id):
    """GET /api/inventario/bodegas/{id}"""
    return jsonify(_buscar(bodega_id, empresa_actual()).a_dic()), 200


@bp.put("/<int:bodega_id>")
@roles_permitidos(ADMIN)
def actualizar(bodega_id):
    """PUT /api/inventario/bodegas/{id}"""
    empresa_id = empresa_actual()
    bodega = _buscar(bodega_id, empresa_id)
    datos = cuerpo_json("nombre", "localId")
    bodega.nombre = texto(datos, "nombre", maximo=100, obligatorio=True)
    bodega.local_id = entero(datos, "localId", obligatorio=True)
    db.session.commit()
    return jsonify(bodega.a_dic()), 200


@bp.delete("/<int:bodega_id>")
@roles_permitidos(ADMIN)
def dar_de_baja(bodega_id):
    """DELETE /api/inventario/bodegas/{id}  -> baja logica.

    Una bodega con mercancia dentro no se puede dar de baja: primero hay que
    trasladar lo que tiene, o el stock quedaria perdido.
    """
    empresa_id = empresa_actual()
    bodega = _buscar(bodega_id, empresa_id)

    con_existencias = Stock.query.filter(
        Stock.bodega_id == bodega_id, Stock.cantidad > 0
    ).count()
    if con_existencias:
        raise Conflicto(
            "La bodega tiene {} productos con existencias: trasladelos primero".format(
                con_existencias
            )
        )

    bodega.activo = False
    db.session.commit()
    return jsonify(bodega.a_dic()), 200
