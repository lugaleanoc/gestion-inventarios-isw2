"""Alertas de stock e indicadores del inventario (RF09, RF11, RF14).

Ruta base: /api/inventario
"""

from datetime import datetime

from flask import Blueprint, jsonify, request

from ..clientes import stock_minimo_de
from ..errores import DatosInvalidos
from ..extensiones import db
from ..modelos import Movimiento, Producto, Stock
from ..paginacion import entero_de_url
from ..seguridad import ADMIN, BODEGA, empresa_actual, roles_permitidos

bp = Blueprint("alertas", __name__, url_prefix="/api/inventario")


def _totales_por_producto(empresa_id):
    """Devuelve {productoId: unidades} sumando todas las bodegas.

    Una sola consulta con GROUP BY en vez de una consulta por producto.
    """
    filas = (
        db.session.query(Stock.producto_id, db.func.sum(Stock.cantidad))
        .filter(Stock.empresa_id == empresa_id)
        .group_by(Stock.producto_id)
        .all()
    )
    return {producto_id: int(total or 0) for producto_id, total in filas}


def _revisar_alertas(empresa_id):
    """Arma la lista de productos agotados y de los que estan bajo el minimo."""
    productos = Producto.query.filter_by(empresa_id=empresa_id, activo=True).all()
    totales = _totales_por_producto(empresa_id)

    agotados, bajo_minimo = [], []
    for producto in productos:
        total = totales.get(producto.producto_id, 0)
        # El minimo lo manda el servicio de Configuracion; si no responde,
        # se usa el valor por defecto en vez de dejar de dar alertas.
        minimo = stock_minimo_de(producto.producto_id)

        alerta = {
            "productoId": producto.producto_id,
            "nombre": producto.nombre,
            "stockTotal": total,
            "stockMinimo": minimo,
        }
        if total == 0:
            agotados.append(dict(alerta, tipo="agotado"))
        elif total <= minimo:
            bajo_minimo.append(dict(alerta, tipo="bajo_minimo"))

    return agotados, bajo_minimo


@bp.get("/alertas")
def alertas():
    """GET /api/inventario/alertas  -> productos agotados o bajo el minimo."""
    agotados, bajo_minimo = _revisar_alertas(empresa_actual())
    # Primero los agotados: son los mas urgentes.
    return jsonify(agotados + bajo_minimo), 200


@bp.get("/indicadores")
@roles_permitidos(ADMIN, BODEGA)
def indicadores():
    """GET /api/inventario/indicadores  -> datos para el dashboard (RF11, RF14).

    Lo consume el microservicio de Reportes, que los junta con los de
    Ventas y Balance para armar el panel.
    """
    empresa_id = empresa_actual()

    # Valor del inventario = suma de (unidades x precio) de cada producto.
    valor_total = (
        db.session.query(db.func.coalesce(db.func.sum(Stock.cantidad * Producto.precio), 0))
        .join(Producto, Producto.producto_id == Stock.producto_id)
        .filter(Stock.empresa_id == empresa_id, Producto.activo.is_(True))
        .scalar()
    )

    cantidad_productos = Producto.query.filter_by(empresa_id=empresa_id, activo=True).count()
    agotados, bajo_minimo = _revisar_alertas(empresa_id)

    # Rotacion: cuantas unidades salieron en el periodo consultado.
    consulta_salidas = (
        db.session.query(
            Movimiento.producto_id,
            # Las salidas estan guardadas en negativo, por eso se invierte
            # el signo para mostrar unidades positivas.
            db.func.sum(-Movimiento.cantidad).label("unidades"),
        )
        .filter(
            Movimiento.empresa_id == empresa_id,
            Movimiento.tipo.in_(("venta", "salida")),
        )
        .group_by(Movimiento.producto_id)
    )

    desde = request.args.get("fechaDesde")
    hasta = request.args.get("fechaHasta")
    try:
        if desde:
            consulta_salidas = consulta_salidas.filter(
                Movimiento.fecha_hora >= datetime.strptime(desde, "%Y-%m-%d")
            )
        if hasta:
            consulta_salidas = consulta_salidas.filter(
                Movimiento.fecha_hora <= datetime.strptime(hasta, "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59
                )
            )
    except ValueError:
        raise DatosInvalidos("Las fechas deben tener el formato AAAA-MM-DD")

    salidas = consulta_salidas.all()
    nombres = {
        p.producto_id: p.nombre
        for p in Producto.query.filter_by(empresa_id=empresa_id).all()
    }

    def a_rotacion(fila):
        return {
            "productoId": fila[0],
            "nombre": nombres.get(fila[0], ""),
            "unidadesSalidas": int(fila[1] or 0),
        }

    ordenadas = sorted(salidas, key=lambda f: int(f[1] or 0), reverse=True)
    return (
        jsonify(
            {
                "valorTotal": float(valor_total or 0),
                "cantidadProductos": cantidad_productos,
                "productosAgotados": agotados,
                "productosBajoMinimo": bajo_minimo,
                # Los 5 que mas rotaron y los 5 que menos.
                "mayorRotacion": [a_rotacion(f) for f in ordenadas[:5]],
                "menorRotacion": [a_rotacion(f) for f in ordenadas[-5:][::-1]],
            }
        ),
        200,
    )
