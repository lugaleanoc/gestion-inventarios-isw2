import hashlib
import json
import logging
from datetime import datetime, timedelta

from flask import current_app

from .db import errores_integridad, get_db
from .tiempo import ahora, iso, para_bd

registro = logging.getLogger("reportes.cache")


def huella(parametros):
    return hashlib.sha256(json.dumps(parametros, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def a_iso(valor):
    if isinstance(valor, datetime):
        return iso(valor)
    return str(valor).replace(" ", "T")[:19] + "Z"


def buscar(empresa_id, tipo, parametros):
    try:
        fila = get_db().fila(
            "SELECT datos, fuentes_no_disponibles, generado_en FROM cache_reportes "
            "WHERE empresa_id = %s AND tipo_reporte = %s AND parametros_hash = %s AND expira_en > %s",
            (empresa_id, tipo, huella(parametros), para_bd(ahora())),
        )
        if fila is None:
            return None
        fuentes = [f for f in fila["fuentes_no_disponibles"].split(",") if f]
        return json.loads(fila["datos"]), fuentes, a_iso(fila["generado_en"])
    except Exception:
        registro.exception("No se pudo leer la caché")
        return None


def guardar(empresa_id, tipo, parametros, cuerpo, fuentes_no_disponibles, generado):
    cfg = current_app.config
    segundos = cfg["CACHE_TTL_PARCIAL_SEGUNDOS"] if fuentes_no_disponibles else cfg["CACHE_TTL_SEGUNDOS"]
    if segundos <= 0:
        return
    try:
        db = get_db()
        clave = (empresa_id, tipo, huella(parametros))
        db.ejecutar("DELETE FROM cache_reportes WHERE expira_en <= %s", (para_bd(ahora()),))
        db.ejecutar(
            "DELETE FROM cache_reportes WHERE empresa_id = %s AND tipo_reporte = %s AND parametros_hash = %s",
            clave,
        )
        db.ejecutar(
            "INSERT INTO cache_reportes (empresa_id, tipo_reporte, parametros_hash, datos, fuentes_no_disponibles, "
            "generado_en, expira_en) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            clave
            + (
                json.dumps(cuerpo, ensure_ascii=False),
                ",".join(fuentes_no_disponibles),
                para_bd(generado),
                para_bd(generado + timedelta(seconds=segundos)),
            ),
        )
        db.commit()
    except errores_integridad():
        get_db().rollback()
    except Exception:
        registro.exception("No se pudo guardar en la caché")
        try:
            get_db().rollback()
        except Exception:
            pass
