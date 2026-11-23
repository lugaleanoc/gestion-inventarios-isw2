"""Locales de la empresa.

Ruta base: /api/configuracion/locales

    GET    ""        listar (cualquier rol o interno)
    POST   ""        crear (administrador)
    GET    /{id}     consultar (cualquier rol o interno)
    PUT    /{id}     actualizar (administrador)
    DELETE /{id}     baja logica: activo = false (administrador)
"""

from flask import Blueprint, jsonify, request

from ..entrada import cuerpo_json, texto
from ..errores import Conflicto, NoEncontrado
from ..extensiones import db
from ..modelos import Local
from ..seguridad import ADMIN, TODOS_LOS_ROLES, empresa_actual, permitir

bp = Blueprint("locales", __name__, url_prefix="/api/configuracion/locales")

# Microservicios que consultan los locales (por ejemplo Inventario, para sus bodegas).
SERVICIOS_QUE_CONSULTAN = ("gateway", "inventario", "reposicion", "reportes")


def _buscar(local_id):
    """Busca un local de la empresa actual. Uno de otra empresa responde 404,
    igual que uno que no existe: quien pregunta no debe saber que existe."""
    local = Local.query.filter_by(local_id=local_id, empresa_id=empresa_actual()).first()
    if local is None:
        raise NoEncontrado("El local {} no existe".format(local_id))
    return local


def _nombre_libre(nombre, menos_id=None):
    """Lanza 409 si otro local de la empresa ya usa ese nombre."""
    consulta = Local.query.filter_by(empresa_id=empresa_actual(), nombre=nombre)
    if menos_id is not None:
        consulta = consulta.filter(Local.local_id != menos_id)
    if consulta.first():
        raise Conflicto("Ya existe un local llamado '{}'".format(nombre), error="LOCAL_REPETIDO")


@bp.get("")
@permitir(roles=TODOS_LOS_ROLES, servicios=SERVICIOS_QUE_CONSULTAN)
def listar():
    """GET /api/configuracion/locales?activo=true  -> arreglo de locales.

    El contrato define la respuesta como un arreglo, sin paginacion: una
    empresa tiene pocos locales.
    """
    # En una URL todo es texto: ?activo=false llega como la cadena "false".
    activo = request.args.get("activo", "true").lower() in ("true", "1", "si", "sí")
    consulta = Local.query.filter_by(empresa_id=empresa_actual(), activo=activo)
    return jsonify([l.a_dic() for l in consulta.order_by(Local.nombre).all()]), 200


@bp.post("")
@permitir(roles=[ADMIN])
def crear():
    """POST /api/configuracion/locales  (rol administrador)"""
    datos = cuerpo_json("nombre")
    nombre = texto(datos, "nombre", maximo=100, obligatorio=True)
    _nombre_libre(nombre)

    local = Local(
        empresa_id=empresa_actual(),
        nombre=nombre,
        direccion=texto(datos, "direccion", maximo=200),
        ciudad=texto(datos, "ciudad", maximo=100),
    )
    db.session.add(local)
    db.session.commit()
    return jsonify(local.a_dic()), 201


@bp.get("/<int:local_id>")
@permitir(roles=TODOS_LOS_ROLES, servicios=SERVICIOS_QUE_CONSULTAN)
def consultar(local_id):
    """GET /api/configuracion/locales/{id}"""
    return jsonify(_buscar(local_id).a_dic()), 200


@bp.put("/<int:local_id>")
@permitir(roles=[ADMIN])
def actualizar(local_id):
    """PUT /api/configuracion/locales/{id}  (rol administrador)"""
    local = _buscar(local_id)
    datos = cuerpo_json("nombre")
    nombre = texto(datos, "nombre", maximo=100, obligatorio=True)
    _nombre_libre(nombre, menos_id=local_id)

    local.nombre = nombre
    local.direccion = texto(datos, "direccion", maximo=200)
    local.ciudad = texto(datos, "ciudad", maximo=100)
    db.session.commit()
    return jsonify(local.a_dic()), 200


@bp.delete("/<int:local_id>")
@permitir(roles=[ADMIN])
def dar_de_baja(local_id):
    """DELETE /api/configuracion/locales/{id}  (rol administrador)

    Baja logica (decision 8): la fila NO se borra, queda activo = false.
    Asi se conservan las ventas y balances que apuntan a ese local.
    """
    local = _buscar(local_id)
    local.activo = False
    db.session.commit()
    return jsonify(local.a_dic()), 200
