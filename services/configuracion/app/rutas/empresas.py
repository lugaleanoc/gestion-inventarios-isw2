"""Empresas.

    POST /api/configuracion/empresas   crear una empresa (interna, solo la llama el Gateway)
    GET  /api/configuracion/empresa    consultar la empresa actual (la del header X-Empresa-Id)
    PUT  /api/configuracion/empresa    cambiar nombre o stock minimo por defecto (administrador)
"""

from flask import Blueprint, current_app, jsonify

from ..entrada import cuerpo_json, entero, texto
from ..errores import Conflicto, NoEncontrado, SinPermiso
from ..extensiones import db
from ..modelos import ConfigAlertas, ConfigDashboard, Empresa
from ..modelos.preferencias import METRICAS_POR_DEFECTO
from ..seguridad import ADMIN, TODOS_LOS_ROLES, empresa_actual, identidad, permitir

bp = Blueprint("empresas", __name__, url_prefix="/api/configuracion")

# Microservicios que pueden consultar la empresa por la red interna.
SERVICIOS_QUE_CONSULTAN = ("gateway", "inventario", "reposicion", "reportes")


@bp.post("/empresas")
def crear():
    """POST /api/configuracion/empresas

    Solo acepta X-Servicio-Origen: gateway. No lleva X-Empresa-Id porque
    la empresa todavia no existe: por eso no usa el decorador permitir().
    """
    if identidad().servicio != "gateway":
        raise SinPermiso("Solo el API Gateway puede crear empresas (X-Servicio-Origen: gateway)")

    datos = cuerpo_json("nombre", "nit")
    nombre = texto(datos, "nombre", maximo=150, obligatorio=True)
    nit = texto(datos, "nit", maximo=30, obligatorio=True)

    if Empresa.query.filter_by(nit=nit).first():
        raise Conflicto("Ya existe una empresa con el NIT {}".format(nit), error="NIT_REPETIDO")

    empresa = Empresa(
        nombre=nombre,
        nit=nit,
        stock_minimo_por_defecto=current_app.config["STOCK_MINIMO_POR_DEFECTO"],
    )
    db.session.add(empresa)
    db.session.flush()  # flush pide a MySQL el empresa_id sin cerrar la transaccion

    # "Empresa creada con configuracion por defecto": alertas y dashboard.
    db.session.add(ConfigAlertas(empresa_id=empresa.empresa_id))
    db.session.add(ConfigDashboard(empresa_id=empresa.empresa_id, metricas=METRICAS_POR_DEFECTO))
    db.session.commit()

    current_app.logger.info("Empresa %s creada (NIT %s)", empresa.empresa_id, nit)
    return jsonify(empresa.a_dic()), 201


def buscar_empresa(empresa_id):
    """Devuelve la empresa o responde 404."""
    empresa = db.session.get(Empresa, empresa_id)
    if empresa is None:
        raise NoEncontrado("La empresa {} no existe".format(empresa_id))
    return empresa


@bp.get("/empresa")
@permitir(roles=TODOS_LOS_ROLES, servicios=SERVICIOS_QUE_CONSULTAN)
def consultar():
    """GET /api/configuracion/empresa"""
    return jsonify(buscar_empresa(empresa_actual()).a_dic()), 200


@bp.put("/empresa")
@permitir(roles=[ADMIN])
def actualizar():
    """PUT /api/configuracion/empresa  (rol administrador). Los campos son opcionales."""
    empresa = buscar_empresa(empresa_actual())
    datos = cuerpo_json()

    if "nombre" in datos:
        empresa.nombre = texto(datos, "nombre", maximo=150, obligatorio=True)

    minimo = entero(datos, "stockMinimoPorDefecto", minimo=0)
    if minimo is not None:
        empresa.stock_minimo_por_defecto = minimo

    db.session.commit()
    return jsonify(empresa.a_dic()), 200
