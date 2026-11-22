import hashlib
import re
import secrets
import string

from werkzeug.security import check_password_hash, generate_password_hash

METODO_HASH = "pbkdf2:sha256:150000"
ALFABETO_CODIGO = string.ascii_uppercase + string.digits

_hash_falso = None


def hashear(valor):
    return generate_password_hash(valor, method=METODO_HASH)


def coincide(hash_guardado, valor):
    return check_password_hash(hash_guardado, valor)


def hash_para_comparar_sin_usuario():
    global _hash_falso
    if _hash_falso is None:
        _hash_falso = hashear("contrasena-falsa-1")
    return _hash_falso


def contrasena_debil(valor):
    return not (
        isinstance(valor, str)
        and 8 <= len(valor) <= 128
        and re.search(r"[A-Za-z]", valor)
        and re.search(r"\d", valor)
    )


def generar_codigo():
    return "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(8))


def hash_codigo(codigo):
    return hashlib.sha256(codigo.strip().upper().encode()).hexdigest()


def generar_cliente_id():
    return "tw_" + secrets.token_hex(8)


def generar_clave_secreta():
    return secrets.token_urlsafe(24)
