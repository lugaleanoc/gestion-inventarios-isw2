from datetime import date, datetime, timedelta, timezone

from flask import current_app, request

from .errores import ApiError


def invalido(detalle):
    return ApiError(400, "DATOS_INVALIDOS", detalle)


def hoy():
    desfase = current_app.config["ZONA_HORARIA_HORAS"]
    return (datetime.now(timezone.utc) + timedelta(hours=desfase)).date()


def entero_positivo(nombre):
    bruto = request.args.get(nombre)
    if bruto is None or bruto == "":
        return None
    if not bruto.strip().isdigit() or int(bruto) < 1:
        raise invalido(f"El parámetro {nombre} debe ser un entero positivo")
    return int(bruto)


def fecha(nombre):
    bruto = request.args.get(nombre)
    if bruto is None or bruto == "":
        return None
    try:
        return date.fromisoformat(bruto.strip())
    except ValueError:
        raise invalido(f"El parámetro {nombre} debe tener el formato AAAA-MM-DD")


def refrescar():
    bruto = request.args.get("refrescar")
    if bruto is None or bruto == "":
        return False
    minusculas = bruto.strip().lower()
    if minusculas in ("true", "1"):
        return True
    if minusculas in ("false", "0"):
        return False
    raise invalido("El parámetro refrescar debe ser true o false")


class Periodo:
    def __init__(self, local_id, desde, hasta):
        self.local_id = local_id
        self.desde = desde
        self.hasta = hasta

    @property
    def clave(self):
        return {
            "localId": self.local_id,
            "fechaDesde": self.desde.isoformat(),
            "fechaHasta": self.hasta.isoformat(),
        }

    def consulta(self, con_local=True):
        datos = {"fechaDesde": self.desde.isoformat(), "fechaHasta": self.hasta.isoformat()}
        if con_local and self.local_id is not None:
            datos["localId"] = self.local_id
        return datos


def periodo_desde_consulta(local_id=None, dias_por_defecto=29):
    desde = fecha("fechaDesde")
    hasta = fecha("fechaHasta")
    if hasta is None:
        hasta = hoy()
    if desde is None:
        desde = hasta - timedelta(days=dias_por_defecto)
    if desde > hasta:
        raise invalido("fechaDesde no puede ser posterior a fechaHasta")
    return Periodo(local_id, desde, hasta)
