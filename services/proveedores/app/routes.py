from flask import Blueprint, g, jsonify

from .auth import ADM, ADM_BOD, TODOS, requiere
from .db import errores_integridad, get_db
from .errores import ApiError
from .serializadores import asociacion_json, proveedor_de_producto_json, proveedor_json
from .validar import (
    booleano,
    booleano_consulta,
    cuerpo_json,
    datos_proveedor,
    entero,
    decimal,
    paginacion,
)
from flask import request

bp = Blueprint("proveedores", __name__, url_prefix="/api/proveedores")

ORIGENES_CONSULTA = ("reposicion", "inventario")

COLUMNAS_PROVEEDOR = (
    "nombre",
    "nit",
    "contacto_nombre",
    "contacto_telefono",
    "contacto_correo",
    "plazo_entrega_dias",
    "forma_pago",
    "pedido_minimo",
)


def proveedor_o_404(db, proveedor_id):
    fila = db.fila(
        "SELECT * FROM proveedores WHERE proveedor_id = %s AND empresa_id = %s",
        (proveedor_id, g.empresa_id),
    )
    if fila is None:
        raise ApiError(404, "PROVEEDOR_NO_ENCONTRADO", f"No existe el proveedor {proveedor_id}")
    return fila


def asociacion(db, proveedor_id, producto_id):
    return db.fila(
        "SELECT * FROM proveedor_producto WHERE proveedor_id = %s AND producto_id = %s",
        (proveedor_id, producto_id),
    )


def nit_duplicado():
    return ApiError(409, "NIT_DUPLICADO", "Ya existe un proveedor con ese NIT en la empresa")


@bp.get("/")
@requiere(TODOS, ORIGENES_CONSULTA)
def listar():
    pagina, por_pagina = paginacion()
    condiciones = ["empresa_id = %s"]
    params = [g.empresa_id]
    busqueda = request.args.get("q", "").strip()
    if busqueda:
        patron = f"%{busqueda}%"
        condiciones.append("(nombre LIKE %s OR nit LIKE %s)")
        params += [patron, patron]
    activo = booleano_consulta("activo")
    condiciones.append("activo = %s")
    params.append(0 if activo is False else 1)
    where = " AND ".join(condiciones)
    db = get_db()
    total = db.fila(f"SELECT COUNT(*) AS total FROM proveedores WHERE {where}", params)["total"]
    filas = db.filas(
        f"SELECT * FROM proveedores WHERE {where} ORDER BY nombre, proveedor_id LIMIT %s OFFSET %s",
        params + [por_pagina, (pagina - 1) * por_pagina],
    )
    return jsonify(
        {
            "datos": [proveedor_json(f) for f in filas],
            "paginacion": {
                "pagina": pagina,
                "porPagina": por_pagina,
                "total": total,
            },
        }
    )


@bp.post("/")
@requiere(ADM_BOD)
def crear():
    datos = datos_proveedor(cuerpo_json())
    db = get_db()
    if db.fila(
        "SELECT proveedor_id FROM proveedores WHERE empresa_id = %s AND nit = %s",
        (g.empresa_id, datos["nit"]),
    ):
        raise nit_duplicado()
    columnas = ("empresa_id",) + COLUMNAS_PROVEEDOR
    marcas = ", ".join(["%s"] * len(columnas))
    try:
        nuevo_id = db.ejecutar(
            f"INSERT INTO proveedores ({', '.join(columnas)}) VALUES ({marcas})",
            [g.empresa_id] + [datos[c] for c in COLUMNAS_PROVEEDOR],
        )
        db.commit()
    except errores_integridad():
        db.rollback()
        raise nit_duplicado()
    return jsonify(proveedor_json(proveedor_o_404(db, nuevo_id))), 201


@bp.get("/<int:proveedor_id>")
@requiere(TODOS, ORIGENES_CONSULTA)
def obtener(proveedor_id):
    return jsonify(proveedor_json(proveedor_o_404(get_db(), proveedor_id)))


@bp.put("/<int:proveedor_id>")
@requiere(ADM_BOD)
def actualizar(proveedor_id):
    datos = datos_proveedor(cuerpo_json())
    db = get_db()
    proveedor_o_404(db, proveedor_id)
    if db.fila(
        "SELECT proveedor_id FROM proveedores WHERE empresa_id = %s AND nit = %s AND proveedor_id <> %s",
        (g.empresa_id, datos["nit"], proveedor_id),
    ):
        raise nit_duplicado()
    asignaciones = ", ".join(f"{c} = %s" for c in COLUMNAS_PROVEEDOR)
    try:
        db.ejecutar(
            f"UPDATE proveedores SET {asignaciones} WHERE proveedor_id = %s AND empresa_id = %s",
            [datos[c] for c in COLUMNAS_PROVEEDOR] + [proveedor_id, g.empresa_id],
        )
        db.commit()
    except errores_integridad():
        db.rollback()
        raise nit_duplicado()
    return jsonify(proveedor_json(proveedor_o_404(db, proveedor_id)))


@bp.delete("/<int:proveedor_id>")
@requiere(ADM)
def dar_de_baja(proveedor_id):
    db = get_db()
    proveedor_o_404(db, proveedor_id)
    db.ejecutar(
        "UPDATE proveedores SET activo = 0 WHERE proveedor_id = %s AND empresa_id = %s",
        (proveedor_id, g.empresa_id),
    )
    db.commit()
    return jsonify(proveedor_json(proveedor_o_404(db, proveedor_id)))


@bp.get("/<int:proveedor_id>/productos")
@requiere(TODOS, ORIGENES_CONSULTA)
def listar_asociaciones(proveedor_id):
    db = get_db()
    proveedor_o_404(db, proveedor_id)
    filas = db.filas(
        "SELECT * FROM proveedor_producto WHERE proveedor_id = %s AND activo = 1 ORDER BY producto_id",
        (proveedor_id,),
    )
    return jsonify([asociacion_json(f) for f in filas])


@bp.post("/<int:proveedor_id>/productos")
@requiere(ADM_BOD)
def asociar_producto(proveedor_id):
    cuerpo = cuerpo_json()
    producto_id = entero(cuerpo, "productoId", minimo=1, obligatorio=True)
    principal = booleano(cuerpo, "principal")
    precio = decimal(cuerpo, "precioCompra")
    db = get_db()
    proveedor = proveedor_o_404(db, proveedor_id)
    if not proveedor["activo"]:
        raise ApiError(409, "PROVEEDOR_INACTIVO", "El proveedor está dado de baja")
    existente = asociacion(db, proveedor_id, producto_id)
    if existente is not None and existente["activo"]:
        raise ApiError(409, "ASOCIACION_DUPLICADA", "El producto ya está asociado a este proveedor")
    principal = bool(principal)
    try:
        if principal:
            db.ejecutar(
                "UPDATE proveedor_producto SET principal = 0 WHERE producto_id = %s AND proveedor_id <> %s "
                "AND proveedor_id IN (SELECT proveedor_id FROM proveedores WHERE empresa_id = %s)",
                (producto_id, proveedor_id, g.empresa_id),
            )
        if existente is None:
            db.ejecutar(
                "INSERT INTO proveedor_producto (proveedor_id, producto_id, principal, precio_compra, activo) "
                "VALUES (%s, %s, %s, %s, 1)",
                (proveedor_id, producto_id, 1 if principal else 0, precio),
            )
        else:
            db.ejecutar(
                "UPDATE proveedor_producto SET principal = %s, precio_compra = %s, activo = 1 "
                "WHERE proveedor_id = %s AND producto_id = %s",
                (1 if principal else 0, precio, proveedor_id, producto_id),
            )
        db.commit()
    except errores_integridad():
        db.rollback()
        raise ApiError(409, "ASOCIACION_DUPLICADA", "El producto ya está asociado a este proveedor")
    return jsonify(asociacion_json(asociacion(db, proveedor_id, producto_id))), 201


@bp.delete("/<int:proveedor_id>/productos/<int:producto_id>")
@requiere(ADM_BOD)
def quitar_producto(proveedor_id, producto_id):
    db = get_db()
    proveedor_o_404(db, proveedor_id)
    if asociacion(db, proveedor_id, producto_id) is None:
        raise ApiError(404, "ASOCIACION_NO_ENCONTRADA", "El producto no está asociado a este proveedor")
    db.ejecutar(
        "UPDATE proveedor_producto SET activo = 0, principal = 0 WHERE proveedor_id = %s AND producto_id = %s",
        (proveedor_id, producto_id),
    )
    db.commit()
    return jsonify(asociacion_json(asociacion(db, proveedor_id, producto_id)))


@bp.get("/por-producto/<int:producto_id>")
@requiere(TODOS, ORIGENES_CONSULTA)
def proveedores_de_producto(producto_id):
    filas = get_db().filas(
        "SELECT p.*, pp.principal, pp.precio_compra FROM proveedor_producto pp "
        "JOIN proveedores p ON p.proveedor_id = pp.proveedor_id "
        "WHERE pp.producto_id = %s AND pp.activo = 1 AND p.activo = 1 AND p.empresa_id = %s "
        "ORDER BY pp.principal DESC, p.nombre, p.proveedor_id",
        (producto_id, g.empresa_id),
    )
    if not filas:
        raise ApiError(
            404, "PRODUCTO_SIN_PROVEEDORES", f"El producto {producto_id} no tiene proveedores asociados"
        )
    return jsonify([proveedor_de_producto_json(f) for f in filas])
