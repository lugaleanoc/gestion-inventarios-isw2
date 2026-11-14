"""Reglas de negocio del stock: el corazon del servicio.

Aqui vive todo lo que cambia existencias, para que las rutas (stock.py y
movimientos.py) no repitan la misma logica. Cada cambio de stock hace
siempre tres cosas juntas:

    1. Ajusta el saldo de la bodega.
    2. Escribe una fila en el kardex con quien, cuando y por que (RF10).
    3. Si el total del producto quedo bajo el minimo, avisa a Reposicion.

Las tres pasan dentro de la misma transaccion: o se guardan todas, o no se
guarda ninguna. Asi nunca queda un saldo sin su movimiento.
"""

from .clientes import avisar_stock_bajo, stock_minimo_de
from .errores import Conflicto, DatosInvalidos, NoEncontrado
from .extensiones import db
from .modelos import Bodega, Movimiento, Producto, Stock
from .modelos.movimiento import TIPOS_QUE_SUMAN


def producto_activo(empresa_id, producto_id):
    """Devuelve el producto si existe y esta activo; si no, 404."""
    producto = Producto.query.filter_by(
        producto_id=producto_id, empresa_id=empresa_id, activo=True
    ).first()
    if producto is None:
        raise NoEncontrado("El producto {} no existe o esta inactivo".format(producto_id))
    return producto


def bodega_activa(empresa_id, bodega_id):
    """Devuelve la bodega si existe y esta activa; si no, 404."""
    bodega = Bodega.query.filter_by(
        bodega_id=bodega_id, empresa_id=empresa_id, activo=True
    ).first()
    if bodega is None:
        raise NoEncontrado("La bodega {} no existe o esta inactiva".format(bodega_id))
    return bodega


def fila_stock(empresa_id, producto_id, bodega_id, bloquear=False):
    """Trae (o crea en cero) la fila de existencias de un producto en una bodega.

    bloquear=True usa SELECT ... FOR UPDATE, que le pide a MySQL que nadie
    mas toque esa fila hasta que termine la transaccion. Es lo que evita el
    problema clasico: dos ventas simultaneas del ultimo articulo leyendo
    "queda 1" al mismo tiempo y dejando el stock en -1.
    """
    consulta = Stock.query.filter_by(producto_id=producto_id, bodega_id=bodega_id)
    if bloquear:
        consulta = consulta.with_for_update()
    fila = consulta.first()

    if fila is None:
        fila = Stock(
            empresa_id=empresa_id, producto_id=producto_id, bodega_id=bodega_id, cantidad=0
        )
        db.session.add(fila)
        # flush manda el INSERT a MySQL sin cerrar la transaccion todavia,
        # para que la fila ya exista si se consulta mas abajo.
        db.session.flush()
    return fila


def total_de_producto(empresa_id, producto_id):
    """Suma las existencias del producto en todas las bodegas.

    El stock minimo se evalua sobre este total, no bodega por bodega
    (decision 4 de la Entrega 2).
    """
    total = (
        db.session.query(db.func.coalesce(db.func.sum(Stock.cantidad), 0))
        .filter(Stock.empresa_id == empresa_id, Stock.producto_id == producto_id)
        .scalar()
    )
    return int(total or 0)


def aplicar_movimiento(empresa_id, tipo, producto_id, bodega_id, cantidad, motivo,
                       registrado_por, bodega_destino_id=None, referencia=None,
                       ajusta_a=None):
    """Cambia el stock y deja la fila correspondiente en el kardex.

    Devuelve la lista de movimientos creados (un traslado genera dos: la
    salida de una bodega y la entrada en la otra).
    """
    producto_activo(empresa_id, producto_id)
    bodega_activa(empresa_id, bodega_id)

    if cantidad == 0:
        raise DatosInvalidos("La cantidad no puede ser cero")
    # Solo el ajuste admite cantidades negativas (sirve para corregir de
    # mas o de menos). Los demas tipos siempre vienen en positivo.
    if cantidad < 0 and tipo != "ajuste":
        raise DatosInvalidos("Solo los ajustes pueden llevar cantidad negativa")

    movimientos = []

    if tipo == "traslado":
        # Un traslado es una salida de la bodega origen y una entrada en la
        # destino. Se guardan como dos movimientos para que el kardex de
        # cada bodega cuadre por separado.
        if bodega_destino_id is None:
            raise DatosInvalidos("Un traslado necesita 'bodegaDestinoId'")
        if bodega_destino_id == bodega_id:
            raise DatosInvalidos("La bodega destino debe ser distinta de la origen")
        bodega_activa(empresa_id, bodega_destino_id)

        origen = fila_stock(empresa_id, producto_id, bodega_id, bloquear=True)
        if origen.cantidad < cantidad:
            raise Conflicto(
                "Hay {} unidades en la bodega {} y se intentan trasladar {}".format(
                    origen.cantidad, bodega_id, cantidad
                ),
                error="STOCK_INSUFICIENTE",
            )
        destino = fila_stock(empresa_id, producto_id, bodega_destino_id, bloquear=True)

        origen.cantidad -= cantidad
        destino.cantidad += cantidad

        movimientos.append(_anotar(empresa_id, "traslado", producto_id, bodega_id,
                                   -cantidad, origen.cantidad, motivo, registrado_por,
                                   bodega_destino_id, referencia, ajusta_a))
        movimientos.append(_anotar(empresa_id, "traslado", producto_id, bodega_destino_id,
                                   cantidad, destino.cantidad, motivo, registrado_por,
                                   None, referencia, ajusta_a))
    else:
        fila = fila_stock(empresa_id, producto_id, bodega_id, bloquear=True)

        # El signo lo decide el tipo de movimiento, no quien llama.
        if tipo == "ajuste":
            delta = cantidad            # puede venir negativo
        elif tipo in TIPOS_QUE_SUMAN:
            delta = abs(cantidad)       # entrada, devolucion de cliente, recepcion
        else:
            delta = -abs(cantidad)      # salida, venta, devolucion a proveedor

        if fila.cantidad + delta < 0:
            raise Conflicto(
                "Hay {} unidades del producto {} en la bodega {} y se intentan sacar {}".format(
                    fila.cantidad, producto_id, bodega_id, abs(delta)
                ),
                error="STOCK_INSUFICIENTE",
            )

        fila.cantidad += delta
        movimientos.append(_anotar(empresa_id, tipo, producto_id, bodega_id, delta,
                                   fila.cantidad, motivo, registrado_por, None,
                                   referencia, ajusta_a))

    return movimientos


def _anotar(empresa_id, tipo, producto_id, bodega_id, cantidad, saldo, motivo,
            registrado_por, bodega_destino_id, referencia, ajusta_a):
    """Crea la fila del kardex. No se llama desde fuera de este archivo."""
    movimiento = Movimiento(
        empresa_id=empresa_id,
        tipo=tipo,
        producto_id=producto_id,
        bodega_id=bodega_id,
        bodega_destino_id=bodega_destino_id,
        cantidad=cantidad,
        saldo_resultante=saldo,
        motivo=motivo,
        referencia=referencia,
        registrado_por=registrado_por,
        ajusta_a=ajusta_a,
    )
    db.session.add(movimiento)
    db.session.flush()  # para que el movimiento ya tenga su id
    return movimiento


def revisar_stock_minimo(empresa_id, producto_id):
    """Compara el total del producto con su minimo y avisa si hace falta.

    Se llama DESPUES del commit: si Reposicion no responde, el movimiento
    de inventario ya quedo guardado igual (RF30, aislamiento de fallos).
    """
    total = total_de_producto(empresa_id, producto_id)
    minimo = stock_minimo_de(producto_id)
    if total <= minimo:
        avisar_stock_bajo(producto_id, total)
    return total, minimo
