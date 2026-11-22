import logging

from flask import Blueprint, current_app, g, jsonify

from .db import errores_integridad, get_db
from .errores import ApiError
from .seguridad import (
    coincide,
    contrasena_debil,
    generar_codigo,
    hash_codigo,
    hash_para_comparar_sin_usuario,
    hashear,
)
from .serializadores import usuario_json
from .sesion import emitir_token, requiere_sesion
from .tiempo import ahora, desde_epoch, en_minutos, para_bd
from .validar import correo_valido, cuerpo_json, invalido, texto

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
registro = logging.getLogger("gateway.auth")


def exigir_contrasena_fuerte(valor):
    if contrasena_debil(valor):
        raise ApiError(
            400,
            "CONTRASENA_DEBIL",
            "La contraseña debe tener entre 8 y 128 caracteres, con al menos una letra y un número",
        )


@bp.post("/login")
def login():
    datos = cuerpo_json()
    correo = correo_valido(datos, "correo")
    contrasena = datos.get("contrasena")
    if not isinstance(contrasena, str) or not contrasena:
        raise invalido("El campo contrasena es obligatorio")
    db = get_db()
    usuario = db.fila("SELECT * FROM usuarios WHERE correo = %s", (correo,))
    hash_guardado = usuario["contrasena_hash"] if usuario else hash_para_comparar_sin_usuario()
    correcta = coincide(hash_guardado, contrasena)
    if usuario is None or not correcta or not usuario["activo"]:
        raise ApiError(401, "CREDENCIALES_INVALIDAS", "Correo o contraseña incorrectos")
    token, expira_en = emitir_token("usuario", usuario["usuario_id"], usuario["empresa_id"], usuario["rol"])
    return jsonify({"token": token, "expiraEn": expira_en, "usuario": usuario_json(usuario)})


@bp.post("/logout")
@requiere_sesion()
def logout():
    db = get_db()
    expira = desde_epoch(g.claims["exp"])
    try:
        db.ejecutar("DELETE FROM tokens_revocados WHERE expira_en < %s", (para_bd(ahora()),))
        db.ejecutar(
            "INSERT INTO tokens_revocados (jti, expira_en) VALUES (%s, %s)",
            (g.claims["jti"], para_bd(expira)),
        )
        db.commit()
    except errores_integridad():
        db.rollback()
    return "", 204


@bp.post("/recuperacion")
def recuperacion():
    datos = cuerpo_json()
    correo = correo_valido(datos, "correo")
    db = get_db()
    usuario = db.fila("SELECT * FROM usuarios WHERE correo = %s", (correo,))
    respuesta = {"mensaje": "Si el correo existe, se generó un código de recuperación"}
    if usuario is not None and usuario["activo"]:
        codigo = generar_codigo()
        db.ejecutar("UPDATE codigos_recuperacion SET usado = 1 WHERE usuario_id = %s", (usuario["usuario_id"],))
        db.ejecutar(
            "INSERT INTO codigos_recuperacion (usuario_id, codigo_hash, expira_en, usado) VALUES (%s, %s, %s, 0)",
            (
                usuario["usuario_id"],
                hash_codigo(codigo),
                para_bd(en_minutos(current_app.config["CODIGO_RECUPERACION_MINUTOS"])),
            ),
        )
        db.commit()
        registro.warning("Código de recuperación para %s: %s", correo, codigo)
        if current_app.config["EXPONER_CODIGO_RECUPERACION"]:
            respuesta["codigoRecuperacion"] = codigo
    return jsonify(respuesta), 202


@bp.post("/restablecimiento")
def restablecimiento():
    datos = cuerpo_json()
    codigo = texto(datos, "codigoRecuperacion", 40, obligatorio=True)
    nueva = datos.get("nuevaContrasena")
    exigir_contrasena_fuerte(nueva)
    db = get_db()
    fila = db.fila(
        "SELECT codigo_id, usuario_id FROM codigos_recuperacion WHERE codigo_hash = %s AND usado = 0 AND expira_en > %s",
        (hash_codigo(codigo), para_bd(ahora())),
    )
    if fila is None:
        raise ApiError(400, "CODIGO_INVALIDO", "El código de recuperación es inválido o está vencido")
    db.ejecutar("UPDATE usuarios SET contrasena_hash = %s WHERE usuario_id = %s", (hashear(nueva), fila["usuario_id"]))
    db.ejecutar("UPDATE codigos_recuperacion SET usado = 1 WHERE codigo_id = %s", (fila["codigo_id"],))
    db.commit()
    return "", 204


@bp.put("/contrasena")
@requiere_sesion(solo_usuarios=True)
def cambiar_contrasena():
    datos = cuerpo_json()
    actual = datos.get("contrasenaActual")
    nueva = datos.get("nuevaContrasena")
    if not isinstance(actual, str) or not actual:
        raise invalido("El campo contrasenaActual es obligatorio")
    db = get_db()
    usuario = db.fila("SELECT * FROM usuarios WHERE usuario_id = %s", (g.sujeto_id,))
    if not coincide(usuario["contrasena_hash"], actual):
        raise ApiError(401, "CREDENCIALES_INVALIDAS", "La contraseña actual es incorrecta")
    exigir_contrasena_fuerte(nueva)
    db.ejecutar("UPDATE usuarios SET contrasena_hash = %s WHERE usuario_id = %s", (hashear(nueva), g.sujeto_id))
    db.commit()
    return "", 204


@bp.post("/token-tienda")
def token_tienda():
    datos = cuerpo_json()
    cliente_id = texto(datos, "clienteId", 40, obligatorio=True)
    clave = datos.get("claveSecreta")
    if not isinstance(clave, str) or not clave:
        raise invalido("El campo claveSecreta es obligatorio")
    db = get_db()
    tienda = db.fila("SELECT * FROM tiendas_web WHERE cliente_id = %s", (cliente_id,))
    hash_guardado = tienda["clave_secreta_hash"] if tienda else hash_para_comparar_sin_usuario()
    correcta = coincide(hash_guardado, clave)
    if tienda is None or not correcta or not tienda["activo"]:
        raise ApiError(401, "CREDENCIALES_INVALIDAS", "Credenciales inválidas o tienda dada de baja")
    token, expira_en = emitir_token("tienda", tienda["tienda_id"], tienda["empresa_id"], "tienda_web")
    return jsonify({"token": token, "expiraEn": expira_en})
