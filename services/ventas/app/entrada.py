"""Lectura y validacion del cuerpo JSON de las peticiones.

Flask entrega el JSON tal como llego. Estas funciones comprueban que estan
los campos obligatorios y que los valores tienen sentido, para que las
rutas no se llenen de ifs repetidos.
"""

from flask import request

from .errores import DatosInvalidos


def cuerpo_json(*obligatorios):
    """Devuelve el cuerpo de la peticion como diccionario.

    obligatorios: nombres de campos que no pueden faltar ni venir vacios.
    """
    # silent=True evita que Flask lance su propio error si el cuerpo no es
    # JSON valido; asi respondemos nosotros con el formato del contrato.
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise DatosInvalidos("El cuerpo de la peticion debe ser un objeto JSON")

    faltantes = [campo for campo in obligatorios
                 if datos.get(campo) is None or datos.get(campo) == ""]
    if faltantes:
        raise DatosInvalidos("Faltan campos obligatorios: {}".format(", ".join(faltantes)))
    return datos


def texto(datos, campo, maximo=None, obligatorio=False):
    """Lee un campo de texto, quitandole los espacios de los extremos."""
    valor = datos.get(campo)
    if valor is None:
        if obligatorio:
            raise DatosInvalidos("Falta el campo '{}'".format(campo))
        return None
    valor = str(valor).strip()
    if obligatorio and not valor:
        raise DatosInvalidos("El campo '{}' no puede estar vacio".format(campo))
    if maximo and len(valor) > maximo:
        raise DatosInvalidos(
            "El campo '{}' no puede superar {} caracteres".format(campo, maximo)
        )
    return valor


def entero(datos, campo, obligatorio=False, minimo=None):
    """Lee un campo numerico entero."""
    valor = datos.get(campo)
    if valor is None:
        if obligatorio:
            raise DatosInvalidos("Falta el campo '{}'".format(campo))
        return None
    try:
        # int(str(...)) acepta tanto 5 como "5", que es lo que suele llegar
        # desde un formulario o desde Postman.
        valor = int(str(valor))
    except (TypeError, ValueError):
        raise DatosInvalidos("El campo '{}' debe ser un numero entero".format(campo))
    if minimo is not None and valor < minimo:
        raise DatosInvalidos("El campo '{}' debe ser mayor o igual a {}".format(campo, minimo))
    return valor


def decimal(datos, campo, obligatorio=False, minimo=None):
    """Lee un campo numerico con decimales, como el precio."""
    valor = datos.get(campo)
    if valor is None:
        if obligatorio:
            raise DatosInvalidos("Falta el campo '{}'".format(campo))
        return None
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        raise DatosInvalidos("El campo '{}' debe ser un numero".format(campo))
    if minimo is not None and valor < minimo:
        raise DatosInvalidos("El campo '{}' debe ser mayor o igual a {}".format(campo, minimo))
    return valor


def booleano(datos, campo, obligatorio=False):
    """Lee un campo que debe ser true o false (sin aceptar "si", 1, etc.)."""
    valor = datos.get(campo)
    if valor is None:
        if obligatorio:
            raise DatosInvalidos("Falta el campo '{}'".format(campo))
        return None
    if not isinstance(valor, bool):
        raise DatosInvalidos("El campo '{}' debe ser true o false".format(campo))
    return valor
