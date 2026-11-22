from flask import Blueprint, g, jsonify, request

from .config import ROL_ADMIN, ROLES_USUARIO
from .db import errores_integridad, get_db
from .errores import ApiError
from .seguridad import generar_clave_secreta, generar_cliente_id, hashear
from .serializadores import tienda_json, usuario_json
from .sesion import requiere_sesion
from .validar import (
    booleano_consulta,
    correo_valido,
    cuerpo_json,
    invalido,
    paginacion,
    texto,
)
from .routes_auth import exigir_contrasena_fuerte

bp = Blueprint("admin", __name__, url_prefix="/api")

SOLO_ADMIN = (ROL_ADMIN,)


def rol_valido(valor):
    if valor not in ROLES_USUARIO:
        raise invalido("El campo rol debe ser administrador, vendedor o encargado_bodega")
    return valor


def usuario_o_404(db, usuario_id):
    fila = db.fila(
        "SELECT * FROM usuarios WHERE usuario_id = %s AND empresa_id = %s", (usuario_id, g.empresa_id)
    )
    if fila is None:
        raise ApiError(404, "USUARIO_NO_ENCONTRADO", f"No existe el usuario {usuario_id}")
    return fila


def correo_duplicado():
    return ApiError(409, "CORREO_DUPLICADO", "Ya existe un usuario con ese correo")


def crear_usuario(db, empresa_id, nombre, correo, contrasena, rol):
    if db.fila("SELECT usuario_id FROM usuarios WHERE correo = %s", (correo,)):
        raise correo_duplicado()
    try:
        nuevo_id = db.ejecutar(
            "INSERT INTO usuarios (empresa_id, nombre, correo, contrasena_hash, rol, activo) VALUES (%s, %s, %s, %s, %s, 1)",
            (empresa_id, nombre, correo, hashear(contrasena), rol),
        )
        db.commit()
    except errores_integridad():
        db.rollback()
        raise correo_duplicado()
    return db.fila("SELECT * FROM usuarios WHERE usuario_id = %s", (nuevo_id,))


@bp.get("/usuarios")
@requiere_sesion(SOLO_ADMIN, solo_usuarios=True)
def listar_usuarios():
    pagina, por_pagina = paginacion()
    condiciones = ["empresa_id = %s"]
    params = [g.empresa_id]
    rol = request.args.get("rol")
    if rol:
        condiciones.append("rol = %s")
        params.append(rol_valido(rol))
    activo = booleano_consulta("activo")
    if activo is not None:
        condiciones.append("activo = %s")
        params.append(1 if activo else 0)
    where = " AND ".join(condiciones)
    db = get_db()
    total = db.fila(f"SELECT COUNT(*) AS total FROM usuarios WHERE {where}", params)["total"]
    filas = db.filas(
        f"SELECT * FROM usuarios WHERE {where} ORDER BY nombre, usuario_id LIMIT %s OFFSET %s",
        params + [por_pagina, (pagina - 1) * por_pagina],
    )
    return jsonify(
        {
            "datos": [usuario_json(f) for f in filas],
            "paginacion": {
                "pagina": pagina,
                "porPagina": por_pagina,
                "total": total,
                "totalPaginas": -(-total // por_pagina),
            },
        }
    )


@bp.post("/usuarios")
@requiere_sesion(SOLO_ADMIN, solo_usuarios=True)
def crear_usuario_endpoint():
    datos = cuerpo_json()
    nombre = texto(datos, "nombre", 150, obligatorio=True)
    correo = correo_valido(datos, "correo")
    contrasena = datos.get("contrasena")
    exigir_contrasena_fuerte(contrasena)
    rol = rol_valido(datos.get("rol"))
    usuario = crear_usuario(get_db(), g.empresa_id, nombre, correo, contrasena, rol)
    return jsonify(usuario_json(usuario)), 201


@bp.get("/usuarios/<int:usuario_id>")
@requiere_sesion(SOLO_ADMIN, solo_usuarios=True)
def obtener_usuario(usuario_id):
    return jsonify(usuario_json(usuario_o_404(get_db(), usuario_id)))


@bp.put("/usuarios/<int:usuario_id>")
@requiere_sesion(SOLO_ADMIN, solo_usuarios=True)
def actualizar_usuario(usuario_id):
    datos = cuerpo_json()
    db = get_db()
    usuario = usuario_o_404(db, usuario_id)
    nombre = texto(datos, "nombre", 150) or usuario["nombre"]
    rol = rol_valido(datos["rol"]) if datos.get("rol") is not None else usuario["rol"]
    db.ejecutar(
        "UPDATE usuarios SET nombre = %s, rol = %s WHERE usuario_id = %s AND empresa_id = %s",
        (nombre, rol, usuario_id, g.empresa_id),
    )
    db.commit()
    return jsonify(usuario_json(usuario_o_404(db, usuario_id)))


@bp.delete("/usuarios/<int:usuario_id>")
@requiere_sesion(SOLO_ADMIN, solo_usuarios=True)
def dar_de_baja_usuario(usuario_id):
    db = get_db()
    usuario_o_404(db, usuario_id)
    if usuario_id == g.sujeto_id:
        raise ApiError(409, "USUARIO_PROPIO", "No puedes dar de baja tu propio usuario")
    db.ejecutar(
        "UPDATE usuarios SET activo = 0 WHERE usuario_id = %s AND empresa_id = %s", (usuario_id, g.empresa_id)
    )
    db.commit()
    return jsonify(usuario_json(usuario_o_404(db, usuario_id)))


@bp.get("/tiendas-web")
@requiere_sesion(SOLO_ADMIN, solo_usuarios=True)
def listar_tiendas():
    filas = get_db().filas(
        "SELECT * FROM tiendas_web WHERE empresa_id = %s ORDER BY nombre, tienda_id", (g.empresa_id,)
    )
    return jsonify([tienda_json(f) for f in filas])


@bp.post("/tiendas-web")
@requiere_sesion(SOLO_ADMIN, solo_usuarios=True)
def registrar_tienda():
    datos = cuerpo_json()
    nombre = texto(datos, "nombre", 150, obligatorio=True)
    cliente_id = generar_cliente_id()
    clave = generar_clave_secreta()
    db = get_db()
    nuevo_id = db.ejecutar(
        "INSERT INTO tiendas_web (empresa_id, nombre, cliente_id, clave_secreta_hash, activo) VALUES (%s, %s, %s, %s, 1)",
        (g.empresa_id, nombre, cliente_id, hashear(clave)),
    )
    db.commit()
    tienda = db.fila("SELECT * FROM tiendas_web WHERE tienda_id = %s", (nuevo_id,))
    respuesta = tienda_json(tienda)
    respuesta["claveSecreta"] = clave
    return jsonify(respuesta), 201


@bp.delete("/tiendas-web/<int:tienda_id>")
@requiere_sesion(SOLO_ADMIN, solo_usuarios=True)
def dar_de_baja_tienda(tienda_id):
    db = get_db()
    tienda = db.fila(
        "SELECT * FROM tiendas_web WHERE tienda_id = %s AND empresa_id = %s", (tienda_id, g.empresa_id)
    )
    if tienda is None:
        raise ApiError(404, "TIENDA_NO_ENCONTRADA", f"No existe la tienda web {tienda_id}")
    db.ejecutar("UPDATE tiendas_web SET activo = 0 WHERE tienda_id = %s", (tienda_id,))
    db.commit()
    return jsonify(tienda_json(db.fila("SELECT * FROM tiendas_web WHERE tienda_id = %s", (tienda_id,))))
