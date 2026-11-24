import base64
import hashlib
import hmac
import json
import time


class TokenError(Exception):
    def __init__(self, codigo, detalle):
        super().__init__(detalle)
        self.codigo = codigo
        self.detalle = detalle


def _b64(datos):
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode()


def _b64_inverso(texto):
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def _firma(mensaje, secreto):
    return hmac.new(secreto.encode(), mensaje.encode(), hashlib.sha256).digest()


def firmar(claims, secreto):
    encabezado = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    cuerpo = _b64(json.dumps(claims, separators=(",", ":")).encode())
    mensaje = f"{encabezado}.{cuerpo}"
    return f"{mensaje}.{_b64(_firma(mensaje, secreto))}"


def verificar(token, secreto, ahora=None):
    partes = token.split(".")
    if len(partes) != 3:
        raise TokenError("TOKEN_INVALIDO", "El token no tiene el formato esperado")
    try:
        encabezado = json.loads(_b64_inverso(partes[0]))
        recibida = _b64_inverso(partes[2])
        claims = json.loads(_b64_inverso(partes[1]))
    except (ValueError, UnicodeDecodeError):
        raise TokenError("TOKEN_INVALIDO", "El token no se pudo leer")
    if not isinstance(encabezado, dict) or encabezado.get("alg") != "HS256" or not isinstance(claims, dict):
        raise TokenError("TOKEN_INVALIDO", "El token no es válido")
    esperada = _firma(f"{partes[0]}.{partes[1]}", secreto)
    if not hmac.compare_digest(esperada, recibida):
        raise TokenError("TOKEN_INVALIDO", "La firma del token no es válida")
    exp = claims.get("exp")
    if not isinstance(exp, int) or exp <= (ahora if ahora is not None else int(time.time())):
        raise TokenError("TOKEN_EXPIRADO", "El token expiró")
    for campo in ("usuarioId", "empresaId", "rol", "tipo", "jti"):
        if campo not in claims:
            raise TokenError("TOKEN_INVALIDO", "El token no tiene los datos necesarios")
    return claims
