"""Stock minimo por producto (RF26).

Ruta base: /api/configuracion/stock-minimo

    GET ""              listar los productos con stock minimo propio
    GET /{productoId}   stock minimo vigente de un producto
    PUT /{productoId}   definir el stock minimo (administrador)

GET /{productoId} lo llaman Inventario y Reposicion por la red interna
(con X-Servicio-Origen y X-Empresa-Id) para saber cuando disparar alertas
y cuanto sugerir comprar. Por eso nunca responde 404: si el producto no
tiene valor propio, devuelve el de la empresa con origen = por_defecto.
"""

from flask import Blueprint, current_app, jsonify

from ..entrada import cuerpo_json, entero
from ..extensiones import db
from ..modelos import Empresa, StockMinimo
from ..seguridad import ADMIN, TODOS_LOS_ROLES, empresa_actual, permitir

bp = Blueprint("stock_minimo", __name__, url_prefix="/api/configuracion/stock-minimo")

SERVICIOS_QUE_CONSULTAN = ("inventario", "reposicion", "reportes")


def minimo_de_la_empresa(empresa_id):
    """stockMinimoPorDefecto de la empresa.

    Si la empresa no esta registrada (por ejemplo, en pruebas sin Gateway)
    se usa el valor de la variable STOCK_MINIMO_POR_DEFECTO.
    """
    empresa = db.session.get(Empresa, empresa_id)
    if empresa is not None:
        return empresa.stock_minimo_por_defecto
    return current_app.config["STOCK_MINIMO_POR_DEFECTO"]


@bp.get("")
@permitir(roles=TODOS_LOS_ROLES, servicios=SERVICIOS_QUE_CONSULTAN)
def listar():
    """GET /api/configuracion/stock-minimo  -> arreglo (sin paginacion, segun el contrato)."""
    reglas = (StockMinimo.query.filter_by(empresa_id=empresa_actual())
              .order_by(StockMinimo.producto_id).all())
    return jsonify([r.a_dic() for r in reglas]), 200


@bp.get("/<int:producto_id>")
@permitir(roles=TODOS_LOS_ROLES, servicios=SERVICIOS_QUE_CONSULTAN)
def consultar(producto_id):
    """GET /api/configuracion/stock-minimo/{productoId}"""
    empresa_id = empresa_actual()
    regla = StockMinimo.query.filter_by(empresa_id=empresa_id, producto_id=producto_id).first()
    if regla is not None:
        return jsonify(regla.a_dic()), 200

    return jsonify({
        "productoId": producto_id,
        "stockMinimo": minimo_de_la_empresa(empresa_id),
        "origen": "por_defecto",
    }), 200


@bp.put("/<int:producto_id>")
@permitir(roles=[ADMIN])
def definir(producto_id):
    """PUT /api/configuracion/stock-minimo/{productoId}  (rol administrador)

    Crea el valor si no existia o lo reemplaza si ya estaba.
    """
    empresa_id = empresa_actual()
    datos = cuerpo_json("stockMinimo")
    valor = entero(datos, "stockMinimo", obligatorio=True, minimo=0)

    regla = StockMinimo.query.filter_by(empresa_id=empresa_id, producto_id=producto_id).first()
    if regla is None:
        regla = StockMinimo(empresa_id=empresa_id, producto_id=producto_id)
        db.session.add(regla)
    regla.stock_minimo = valor
    db.session.commit()
    return jsonify(regla.a_dic()), 200
