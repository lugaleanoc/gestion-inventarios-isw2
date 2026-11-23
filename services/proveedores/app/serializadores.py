def numero(valor):
    return None if valor is None else float(valor)


def proveedor_json(fila):
    return {
        "nombre": fila["nombre"],
        "nit": fila["nit"],
        "contacto": {
            "nombre": fila["contacto_nombre"],
            "telefono": fila["contacto_telefono"],
            "correo": fila["contacto_correo"],
        },
        "condiciones": {
            "plazoEntregaDias": fila["plazo_entrega_dias"],
            "formaPago": fila["forma_pago"],
            "pedidoMinimo": numero(fila["pedido_minimo"]),
        },
        "proveedorId": fila["proveedor_id"],
        "empresaId": fila["empresa_id"],
        "activo": bool(fila["activo"]),
    }


def asociacion_json(fila):
    return {
        "proveedorId": fila["proveedor_id"],
        "productoId": fila["producto_id"],
        "principal": bool(fila["principal"]),
        "precioCompra": numero(fila["precio_compra"]),
        "activo": bool(fila["activo"]),
    }


def proveedor_de_producto_json(fila):
    datos = proveedor_json(fila)
    datos["principal"] = bool(fila["principal"])
    datos["precioCompra"] = numero(fila["precio_compra"])
    return datos
