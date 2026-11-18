"""Existencias y operaciones internas de stock (RF04).

Ruta base: /api/inventario/stock

Dos de estas rutas son INTERNAS: no se llaman desde el Gateway, sino desde
otro microservicio por la red interna.
    POST /stock/descuentos  <- lo llama Ventas cuando se vende algo
    POST /stock/entradas    <- lo llama Reposicion cuando llega mercancia
"""

from flask import Blueprint, jsonify

from .. import operaciones
from ..entrada import cuerpo_json, entero
from ..errores import DatosInvalidos
from ..extensiones import db
from ..modelos import Bodega, Producto, Stock
from ..paginacion import entero_de_url, paginar
from ..seguridad import empresa_actual, identidad, solo_interno

bp = Blueprint("stock", __name__, url_prefix="/api/inventario/stock")


def _local_de_cada_bodega(empresa_id):
    """Diccionario {bodegaId: localId} para no consultar la bodega una por una.

    Sin esto, una lista de 100 existencias haria 100 consultas extra a la
    base (el problema conocido como "N+1 consultas").
    """
    return {
        bodega.bodega_id: bodega.local_id
        for bodega in Bodega.query.filter_by(empresa_id=empresa_id).all()
    }


@bp.get("")
def listar():
    """GET /api/inventario/stock  -> existencias, con filtros y paginacion."""
    empresa_id = empresa_actual()
    consulta = Stock.query.filter_by(empresa_id=empresa_id)

    producto_id = entero_de_url("productoId")
    if producto_id is not None:
        consulta = consulta.filter_by(producto_id=producto_id)

    bodega_id = entero_de_url("bodegaId")
    if bodega_id is not None:
        consulta = consulta.filter_by(bodega_id=bodega_id)

    # Filtrar por local exige cruzar con la tabla de bodegas, porque el
    # local no esta en la tabla de stock.
    local_id = entero_de_url("localId")
    if local_id is not None:
        consulta = consulta.join(Bodega, Bodega.bodega_id == Stock.bodega_id).filter(
            Bodega.local_id == local_id
        )

    locales = _local_de_cada_bodega(empresa_id)
    consulta = consulta.order_by(Stock.producto_id, Stock.bodega_id)
    return jsonify(paginar(consulta, lambda s: s.a_dic(locales.get(s.bodega_id)))), 200


@bp.get("/productos/<int:producto_id>")
def stock_de_producto(producto_id):
    """GET /api/inventario/stock/productos/{id}

    Devuelve el total del producto y su reparto por bodega. Es la consulta
    mas usada del sistema, por eso es una de las candidatas a las pruebas
    de rendimiento.
    """
    empresa_id = empresa_actual()
    operaciones.producto_activo(empresa_id, producto_id)

    filas = Stock.query.filter_by(empresa_id=empresa_id, producto_id=producto_id).all()
    locales = _local_de_cada_bodega(empresa_id)
    return (
        jsonify(
            {
                "productoId": producto_id,
                "total": sum(fila.cantidad for fila in filas),
                "porBodega": [fila.a_dic(locales.get(fila.bodega_id)) for fila in filas],
            }
        ),
        200,
    )


@bp.post("/descuentos")
@solo_interno("ventas")
def descontar():
    """POST /api/inventario/stock/descuentos  (interno, solo Ventas).

    Ventas manda los articulos vendidos y aqui se restan del stock. O se
    descuentan TODOS o no se descuenta ninguno: si falta uno solo, se
    responde 409 y la venta no se confirma.
    """
    empresa_id = empresa_actual()
    datos = cuerpo_json("ventaId", "items")
    venta_id = entero(datos, "ventaId", obligatorio=True)
    items = datos.get("items")

    if not isinstance(items, list) or not items:
        raise DatosInvalidos("'items' debe ser una lista con al menos un articulo")

    resultado = []
    try:
        for item in items:
            producto_id = entero(item, "productoId", obligatorio=True)
            bodega_id = entero(item, "bodegaId", obligatorio=True)
            cantidad = entero(item, "cantidad", obligatorio=True, minimo=1)

            producto = operaciones.producto_activo(empresa_id, producto_id)
            operaciones.aplicar_movimiento(
                empresa_id=empresa_id,
                tipo="venta",
                producto_id=producto_id,
                bodega_id=bodega_id,
                cantidad=cantidad,
                motivo="Venta {}".format(venta_id),
                registrado_por=identidad().quien(),
                referencia="venta:{}".format(venta_id),
            )
            resultado.append(
                {
                    "productoId": producto_id,
                    "bodegaId": bodega_id,
                    "cantidad": cantidad,
                    "precioUnitario": float(producto.precio),
                }
            )
        # Un solo commit al final: esto es lo que hace que la operacion sea
        # "todo o nada".
        db.session.commit()
    except Exception:
        # rollback deshace los descuentos ya aplicados en esta peticion.
        db.session.rollback()
        raise

    # Ya guardado el descuento, se revisa si algun producto quedo bajo el
    # minimo. Va despues del commit a proposito: si Reposicion esta caido,
    # la venta no se pierde.
    for item in resultado:
        operaciones.revisar_stock_minimo(empresa_id, item["productoId"])

    return jsonify({"ventaId": venta_id, "items": resultado}), 200


@bp.post("/entradas")
@solo_interno("reposicion")
def registrar_entrada():
    """POST /api/inventario/stock/entradas  (interno, solo Reposicion).

    Entra la mercancia de una orden de compra recibida. Es idempotente: si
    Reposicion reintenta la misma orden, no se suma el stock dos veces.
    """
    empresa_id = empresa_actual()
    datos = cuerpo_json("ordenId", "items")
    orden_id = entero(datos, "ordenId", obligatorio=True)
    items = datos.get("items")

    if not isinstance(items, list) or not items:
        raise DatosInvalidos("'items' debe ser una lista con al menos un articulo")

    referencia = "orden:{}".format(orden_id)

    # Idempotencia: si ya existe un movimiento con esta referencia, la
    # entrada ya se registro antes (probablemente un reintento de la red).
    from ..modelos import Movimiento

    ya_registrada = Movimiento.query.filter_by(
        empresa_id=empresa_id, referencia=referencia
    ).first()
    if ya_registrada:
        from ..errores import Conflicto

        raise Conflicto("La entrada de la orden {} ya estaba registrada".format(orden_id))

    movimientos = []
    try:
        for item in items:
            producto_id = entero(item, "productoId", obligatorio=True)
            bodega_id = entero(item, "bodegaId", obligatorio=True)
            cantidad = entero(item, "cantidad", obligatorio=True, minimo=1)

            movimientos += operaciones.aplicar_movimiento(
                empresa_id=empresa_id,
                tipo="recepcion_orden",
                producto_id=producto_id,
                bodega_id=bodega_id,
                cantidad=cantidad,
                motivo="Recepcion de la orden {}".format(orden_id),
                registrado_por=identidad().quien(),
                referencia=referencia,
            )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify([m.a_dic() for m in movimientos]), 201
