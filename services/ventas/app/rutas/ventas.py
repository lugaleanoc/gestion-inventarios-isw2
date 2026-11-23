"""Ventas (RF15, RF16, RF17).

Ruta base: /api/ventas

    POST ""                          registrar una venta
    GET  ""                          listar ventas (paginado)
    GET  /resumen                    totales por canal y medio de pago (Reportes)
    GET  /{ventaId}                  consultar una venta
    POST /{ventaId}/reintento-balance  reenviar el ingreso a Balance (administrador)
"""

from flask import Blueprint, current_app, jsonify
from sqlalchemy import func

from .. import clientes
from ..entrada import cuerpo_json, entero
from ..errores import Conflicto, DatosInvalidos, NoEncontrado, ServicioNoDisponible, SinPermiso
from ..extensiones import db
from ..fechas import ahora
from ..modelos import ItemVenta, Venta
from ..modelos.venta import CANALES, ESTADOS, ESTADOS_BALANCE, MEDIOS_PAGO
from ..paginacion import entero_de_url, fecha_de_url, opcion_de_url, paginar, rango_del_dia
from ..seguridad import ADMIN, TIENDA_WEB, VENDEDOR, empresa_actual, identidad, permitir

bp = Blueprint("ventas", __name__, url_prefix="/api/ventas")


# POST /api/ventas  -  registrar una venta
def _validar_venta(datos):
    """Revisa el cuerpo de la venta y devuelve los valores ya limpios (paso 1)."""
    local_id = entero(datos, "localId", obligatorio=True, minimo=1)
    bodega_id = entero(datos, "bodegaId", minimo=1)  # opcional

    canal = datos.get("canal")
    if canal not in CANALES:
        raise DatosInvalidos("El campo canal debe ser tienda_fisica o tienda_web")
    medio_pago = datos.get("medioPago")
    if medio_pago not in MEDIOS_PAGO:
        raise DatosInvalidos("El campo medioPago debe ser efectivo, tarjeta o qr")

    items = datos.get("items")
    if not isinstance(items, list) or not items:
        raise DatosInvalidos("'items' debe ser una lista con al menos un producto")
    items_limpios = []
    for item in items:
        if not isinstance(item, dict):
            raise DatosInvalidos("Cada item debe tener productoId y cantidad")
        if "precioUnitario" in item or "precio" in item:
            # El precio lo pone Inventario, nunca el cliente.
            raise DatosInvalidos("No se envia el precio: Ventas lo toma de Inventario")
        items_limpios.append({
            "productoId": entero(item, "productoId", obligatorio=True, minimo=1),
            "cantidad": entero(item, "cantidad", obligatorio=True, minimo=1),
        })
    return local_id, bodega_id, canal, medio_pago, items_limpios


@bp.post("")
@permitir(roles=[ADMIN, VENDEDOR, TIENDA_WEB])
def registrar():
    """Registra una venta siguiendo el flujo del contrato:

    1. Valida los datos (tienda_web solo puede vender por el canal tienda_web).
    2. Si no viene bodegaId, pide a Inventario las bodegas del local y toma la primera.
    3. Guarda la venta "en_proceso" (asi ya tiene ventaId).
    4. Pide a Inventario descontar el stock ("todo o nada"). Inventario
       devuelve el precio de cada producto.
         409 -> venta "rechazada" y se responde 409
         sin respuesta -> venta "rechazada" y se responde 503
    5. Guarda items, total y estado "confirmada", y registra el ingreso en
       Balance Diario. Si Balance no responde, la venta SI queda confirmada,
       con estadoBalance = "pendiente".
    """
    empresa_id = empresa_actual()
    quien = identidad()

    # --- Paso 1: validar ---
    local_id, bodega_id, canal, medio_pago, items = _validar_venta(cuerpo_json("localId", "canal", "medioPago", "items"))
    if quien.rol == TIENDA_WEB and canal != "tienda_web":
        raise SinPermiso("El rol tienda_web solo puede registrar ventas con canal tienda_web")

    # --- Paso 2: elegir bodega ---
    if bodega_id is None:
        bodegas = clientes.bodegas_del_local(empresa_id, local_id)
        if not bodegas:
            raise DatosInvalidos("El local {} no tiene bodegas activas en Inventario".format(local_id))
        bodega_id = bodegas[0]["bodegaId"]

    # --- Paso 3: guardar la venta en_proceso ---
    venta = Venta(
        empresa_id=empresa_id,
        local_id=local_id,
        bodega_id=bodega_id,
        canal=canal,
        medio_pago=medio_pago,
        usuario_id=int(quien.usuario_id) if str(quien.usuario_id or "").isdigit() else None,
        fecha_hora=ahora(),
        estado="en_proceso",
        estado_balance="no_aplica",
    )
    db.session.add(venta)
    db.session.commit()  # commit: ahora la venta tiene venta_id

    # --- Paso 4: descontar el stock en Inventario ---
    pedido = [dict(item, bodegaId=bodega_id) for item in items]
    try:
        respuesta = clientes.descontar_stock(empresa_id, venta.venta_id, pedido)
    except ServicioNoDisponible:
        _rechazar(venta, "Inventario no respondio")
        raise  # el manejador de errores responde 503 SERVICIO_NO_DISPONIBLE

    if respuesta.status_code != 200:
        error = _error_de(respuesta)
        _rechazar(venta, "Inventario respondio {} {}".format(respuesta.status_code, error["error"]))
        if respuesta.status_code == 409:
            raise Conflicto(error["detalle"], error=error["error"])  # STOCK_INSUFICIENTE
        # Cualquier otro rechazo (por ejemplo, un producto que no existe)
        # es un problema de los datos de la venta.
        raise DatosInvalidos(error["detalle"], error=error["error"])

    # --- Paso 5: guardar items y total, confirmar, avisar a Balance ---
    total = 0
    for item in respuesta.json()["items"]:
        precio = float(item["precioUnitario"])
        subtotal = precio * item["cantidad"]
        total += subtotal
        venta.items.append(ItemVenta(producto_id=item["productoId"], cantidad=item["cantidad"],
                                     precio_unitario=precio, subtotal=subtotal))
    venta.total = total
    venta.estado = "confirmada"
    venta.estado_balance = "pendiente"  # hasta que Balance confirme
    db.session.commit()

    if clientes.registrar_ingreso(venta):
        venta.estado_balance = "registrado"
        db.session.commit()

    current_app.logger.info("Venta %s confirmada: total %s, estadoBalance %s",
                            venta.venta_id, total, venta.estado_balance)
    return jsonify(venta.a_dic()), 201


def _rechazar(venta, motivo):
    """Marca la venta como rechazada. No se borra: queda en el historial."""
    venta.estado = "rechazada"
    venta.estado_balance = "no_aplica"
    db.session.commit()
    current_app.logger.warning("Venta %s rechazada: %s", venta.venta_id, motivo)


def _error_de(respuesta):
    """Saca {error, detalle} de la respuesta de otro servicio, aunque venga rara."""
    try:
        datos = respuesta.json()
        return {"error": datos.get("error", "ERROR_INVENTARIO"), "detalle": datos.get("detalle", "")}
    except (ValueError, AttributeError):
        return {"error": "ERROR_INVENTARIO", "detalle": "Inventario respondio {}".format(respuesta.status_code)}


# Consultas
@bp.get("")
@permitir(roles=[ADMIN, VENDEDOR], servicios=["reportes"])
def listar():
    """GET /api/ventas  (paginado). Por defecto solo las ventas confirmadas."""
    consulta = Venta.query.filter_by(empresa_id=empresa_actual())

    local_id = entero_de_url("localId")
    if local_id is not None:
        consulta = consulta.filter_by(local_id=local_id)
    for parametro, columna, opciones in (("canal", "canal", CANALES),
                                         ("medioPago", "medio_pago", MEDIOS_PAGO),
                                         ("estadoBalance", "estado_balance", ESTADOS_BALANCE)):
        valor = opcion_de_url(parametro, opciones)
        if valor is not None:
            consulta = consulta.filter(getattr(Venta, columna) == valor)
    consulta = consulta.filter_by(estado=opcion_de_url("estado", ESTADOS) or "confirmada")

    desde = fecha_de_url("fechaDesde")
    hasta = fecha_de_url("fechaHasta")
    if desde or hasta:
        inicio, fin = rango_del_dia(desde or hasta, hasta or desde)
        consulta = consulta.filter(Venta.fecha_hora >= inicio, Venta.fecha_hora < fin)

    consulta = consulta.order_by(Venta.fecha_hora.desc(), Venta.venta_id.desc())
    return jsonify(paginar(consulta, lambda v: v.a_dic())), 200


@bp.get("/resumen")
@permitir(roles=[ADMIN], servicios=["reportes"])
def resumen():
    """GET /api/ventas/resumen  - totales por canal y medio de pago (RF24).

    Solo cuenta ventas confirmadas. Si no se envian fechas, toma el mes
    actual (del dia 1 hasta hoy, en hora de Colombia).
    """
    empresa_id = empresa_actual()
    hoy = ahora().date()
    hasta = fecha_de_url("fechaHasta", por_defecto=hoy)
    desde = fecha_de_url("fechaDesde", por_defecto=hasta.replace(day=1))
    if desde > hasta:
        raise DatosInvalidos("fechaDesde no puede ser posterior a fechaHasta")
    local_id = entero_de_url("localId")
    inicio, fin = rango_del_dia(desde, hasta)

    # Una sola consulta agrupada: MySQL hace las sumas, no Python.
    #   SELECT canal, medio_pago, SUM(total), COUNT(*) FROM ventas WHERE ... GROUP BY canal, medio_pago
    consulta = (db.session.query(Venta.canal, Venta.medio_pago, func.sum(Venta.total), func.count(Venta.venta_id))
                .filter(Venta.empresa_id == empresa_id, Venta.estado == "confirmada",
                        Venta.fecha_hora >= inicio, Venta.fecha_hora < fin))
    if local_id is not None:
        consulta = consulta.filter(Venta.local_id == local_id)

    por_canal = {canal: 0.0 for canal in CANALES}
    por_medio = {medio: 0.0 for medio in MEDIOS_PAGO}
    total, cantidad = 0.0, 0
    for canal, medio, suma, conteo in consulta.group_by(Venta.canal, Venta.medio_pago).all():
        suma = float(suma or 0)
        por_canal[canal] += suma
        por_medio[medio] += suma
        total += suma
        cantidad += conteo

    return jsonify({
        "fechaDesde": desde.isoformat(),
        "fechaHasta": hasta.isoformat(),
        "localId": local_id,
        "totalVentas": total,
        "cantidadVentas": cantidad,
        "porCanal": por_canal,
        "porMedioPago": por_medio,
    }), 200


def _buscar(venta_id):
    """Una venta de otra empresa responde 404, igual que una que no existe."""
    venta = Venta.query.filter_by(venta_id=venta_id, empresa_id=empresa_actual()).first()
    if venta is None:
        raise NoEncontrado("La venta {} no existe".format(venta_id))
    return venta


@bp.get("/<int:venta_id>")
@permitir(roles=[ADMIN, VENDEDOR], servicios=["reportes"])
def consultar(venta_id):
    """GET /api/ventas/{ventaId}"""
    return jsonify(_buscar(venta_id).a_dic()), 200


@bp.post("/<int:venta_id>/reintento-balance")
@permitir(roles=[ADMIN])
def reintentar_balance(venta_id):
    """POST /api/ventas/{ventaId}/reintento-balance  (administrador)

    Vuelve a mandar a Balance el ingreso de una venta confirmada que quedo
    "pendiente". Es seguro: Balance no duplica ingresos por ventaId.
    """
    venta = _buscar(venta_id)
    if venta.estado != "confirmada":
        raise Conflicto("La venta {} esta {}: no genera ingreso".format(venta_id, venta.estado),
                        error="VENTA_NO_CONFIRMADA")
    if venta.estado_balance == "registrado":
        raise Conflicto("El ingreso de la venta {} ya esta registrado en Balance Diario".format(venta_id),
                        error="BALANCE_YA_REGISTRADO")

    if not clientes.registrar_ingreso(venta):
        raise ServicioNoDisponible("Balance Diario sigue sin responder; la venta {} continua pendiente"
                                   .format(venta_id))
    venta.estado_balance = "registrado"
    db.session.commit()
    return jsonify(venta.a_dic()), 200
