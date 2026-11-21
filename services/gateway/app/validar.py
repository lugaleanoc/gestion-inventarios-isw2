import re

from flask import request

from .errores import ApiError

CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def invalido(detalle):
    return ApiError(400, "DATOS_INVALIDOS", detalle)


def cuerpo_json():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise invalido("El cuerpo debe ser un objeto JSON")
    return datos


def objeto_opcional(datos, campo):
    valor = datos.get(campo)
    if valor is None:
        return {}
    if not isinstance(valor, dict):
        raise invalido(f"El campo {campo} debe ser un objeto")
    return valor


def texto(datos, campo, maximo, obligatorio=False, etiqueta=None):
    etiqueta = etiqueta or campo
    valor = datos.get(campo)
    if valor is None:
        if obligatorio:
            raise invalido(f"El campo {etiqueta} es obligatorio")
        return None
    if not isinstance(valor, str):
        raise invalido(f"El campo {etiqueta} debe ser texto")
    valor = valor.strip()
    if not valor:
        if obligatorio:
            raise invalido(f"El campo {etiqueta} es obligatorio")
        return None
    if len(valor) > maximo:
        raise invalido(f"El campo {etiqueta} admite máximo {maximo} caracteres")
    return valor


def entero(datos, campo, minimo=0, obligatorio=False, etiqueta=None):
    etiqueta = etiqueta or campo
    valor = datos.get(campo)
    if valor is None:
        if obligatorio:
            raise invalido(f"El campo {etiqueta} es obligatorio")
        return None
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise invalido(f"El campo {etiqueta} debe ser un entero")
    if valor < minimo:
        raise invalido(f"El campo {etiqueta} debe ser mayor o igual a {minimo}")
    return valor


def decimal(datos, campo, etiqueta=None):
    etiqueta = etiqueta or campo
    valor = datos.get(campo)
    if valor is None:
        return None
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise invalido(f"El campo {etiqueta} debe ser numérico")
    if valor < 0:
        raise invalido(f"El campo {etiqueta} no puede ser negativo")
    return round(float(valor), 2)


def booleano(datos, campo):
    valor = datos.get(campo)
    if valor is None:
        return None
    if not isinstance(valor, bool):
        raise invalido(f"El campo {campo} debe ser verdadero o falso")
    return valor


def booleano_consulta(nombre):
    bruto = request.args.get(nombre)
    if bruto is None or bruto == "":
        return None
    minusculas = bruto.strip().lower()
    if minusculas in ("true", "1"):
        return True
    if minusculas in ("false", "0"):
        return False
    raise invalido(f"El parámetro {nombre} debe ser true o false")


def paginacion():
    def leer(nombre, defecto):
        bruto = request.args.get(nombre)
        if bruto is None or bruto == "":
            return defecto
        if not bruto.strip().isdigit() or int(bruto) < 1:
            raise invalido(f"El parámetro {nombre} debe ser un entero positivo")
        return int(bruto)

    pagina = leer("pagina", 1)
    por_pagina = min(leer("porPagina", 20), 100)
    return pagina, por_pagina


def correo_valido(datos, campo, etiqueta=None, obligatorio=True):
    etiqueta = etiqueta or campo
    valor = texto(datos, campo, 150, obligatorio=obligatorio, etiqueta=etiqueta)
    if valor is None:
        return None
    valor = valor.lower()
    if not CORREO.match(valor):
        raise invalido(f"El campo {etiqueta} no tiene un formato válido")
    return valor


def objeto_obligatorio(datos, campo):
    valor = datos.get(campo)
    if not isinstance(valor, dict):
        raise invalido(f"El campo {campo} es obligatorio y debe ser un objeto")
    return valor
