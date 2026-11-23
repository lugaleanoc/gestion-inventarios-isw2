def usuario_json(fila):
    return {
        "usuarioId": fila["usuario_id"],
        "empresaId": fila["empresa_id"],
        "nombre": fila["nombre"],
        "correo": fila["correo"],
        "rol": fila["rol"],
        "activo": bool(fila["activo"]),
    }


def tienda_json(fila):
    return {
        "tiendaId": fila["tienda_id"],
        "nombre": fila["nombre"],
        "clienteId": fila["cliente_id"],
        "activo": bool(fila["activo"]),
    }
