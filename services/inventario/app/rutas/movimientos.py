"""Movimientos de inventario y kardex (RF04, RF10, RF13).

Ruta base: /api/inventario/movimientos

Aqui se registran las entradas, salidas, ajustes, traslados y devoluciones
que hace una persona. Los movimientos que genera el propio sistema (venta y
recepcion de orden) entran por las rutas internas de stock.py.
"""

from datetime import datetime

from flask import Blueprint, jsonify

from .. import operaciones
from ..entrada import cuerpo_json, entero, texto
from ..errores import DatosInvalidos, NoEncontrado
from ..extensiones import db
from ..modelos import Movimiento
from ..paginacion import entero_de_url, paginar
from ..seguridad import ADMIN, BODEGA, empresa_actual, identidad, roles_permitidos
from flask import request

bp = Blueprint("movimientos", __name__, url_prefix="/api/inventario/movimientos")

# Tipos que puede registrar una persona desde esta ruta. 'venta' y
# 'recepcion_orden' no estan: esos solo los crea el sistema.
TIPOS_MANUALES = (
    "entrada",
    "salida",
    "ajuste",
    "traslado",
    "devolucion_cliente",
    "devolucion_proveedor",
)


def _fecha_de_url(nombre):
    """Lee una fecha de la URL en formato 2026-11-13."""
    valor = request.args.get(nombre)
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d")
    except ValueError:
        raise DatosInvalidos("El parametro '{}' debe tener el formato AAAA-MM-DD".format(nombre))


@bp.get("")
def listar():
    """GET /api/inventario/movimientos  -> el kardex, con filtros.

    Filtros: productoId, bodegaId, tipo, fechaDesde, fechaHasta.
    """
    empresa_id = empresa_actual()
    consulta = Movimiento.query.filter_by(empresa_id=empresa_id)

    producto_id = entero_de_url("productoId")
    if producto_id is not None:
        consulta = consulta.filter_by(producto_id=producto_id)

    bodega_id = entero_de_url("bodegaId")
    if bodega_id is not None:
        consulta = consulta.filter_by(bodega_id=bodega_id)

    tipo = request.args.get("tipo")
    if tipo:
        consulta = consulta.filter_by(tipo=tipo)

    desde = _fecha_de_url("fechaDesde")
    if desde:
        consulta = consulta.filter(Movimiento.fecha_hora >= desde)

    hasta = _fecha_de_url("fechaHasta")
    if hasta:
        # Se suma un dia para incluir todo el dia indicado, no solo las 00:00.
        consulta = consulta.filter(
            Movimiento.fecha_hora < hasta.replace(hour=23, minute=59, second=59)
        )

    # Del mas nuevo al mas viejo: es como se lee un kardex.
    consulta = consulta.order_by(Movimiento.fecha_hora.desc(), Movimiento.movimiento_id.desc())
    return jsonify(paginar(consulta, lambda m: m.a_dic())), 200


@bp.post("")
@roles_permitidos(ADMIN, BODEGA)
def registrar():
    """POST /api/inventario/movimientos  -> registra un movimiento manual.

    El stock y el kardex se actualizan juntos dentro de la misma
    transaccion; de eso se encarga app/operaciones.py.
    """
    empresa_id = empresa_actual()
    datos = cuerpo_json("tipo", "productoId", "bodegaId", "cantidad", "motivo")

    tipo = texto(datos, "tipo", obligatorio=True)
    if tipo not in TIPOS_MANUALES:
        raise DatosInvalidos(
            "El tipo '{}' no es valido. Validos: {}".format(tipo, ", ".join(TIPOS_MANUALES))
        )

    producto_id = entero(datos, "productoId", obligatorio=True)
    bodega_id = entero(datos, "bodegaId", obligatorio=True)
    cantidad = entero(datos, "cantidad", obligatorio=True)
    motivo = texto(datos, "motivo", maximo=200, obligatorio=True)
    bodega_destino_id = entero(datos, "bodegaDestinoId")
    ajusta_a = entero(datos, "ajustaA")

    # Un ajuste puede corregir un movimiento anterior (RNF20). El original
    # no se toca: queda el par original + ajuste.
    if ajusta_a is not None:
        original = Movimiento.query.filter_by(
            movimiento_id=ajusta_a, empresa_id=empresa_id
        ).first()
        if original is None:
            raise NoEncontrado("El movimiento {} que se quiere ajustar no existe".format(ajusta_a))
        if tipo != "ajuste":
            raise DatosInvalidos("Solo un movimiento de tipo 'ajuste' puede llevar 'ajustaA'")

    try:
        movimientos = operaciones.aplicar_movimiento(
            empresa_id=empresa_id,
            tipo=tipo,
            producto_id=producto_id,
            bodega_id=bodega_id,
            cantidad=cantidad,
            motivo=motivo,
            registrado_por=identidad().quien(),
            bodega_destino_id=bodega_destino_id,
            ajusta_a=ajusta_a,
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    # Si la salida dejo el producto bajo el minimo, se avisa a Reposicion.
    operaciones.revisar_stock_minimo(empresa_id, producto_id)

    # Un traslado genera dos movimientos; los demas, uno solo.
    cuerpo = [m.a_dic() for m in movimientos]
    return jsonify(cuerpo[0] if len(cuerpo) == 1 else cuerpo), 201
