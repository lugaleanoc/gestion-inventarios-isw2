"""Categorias y subcategorias (RF02).

Ruta base: /api/inventario/categorias
Roles: administrador y encargado_bodega pueden crear y editar;
       cualquier usuario autenticado puede consultar.
"""

from flask import Blueprint, jsonify

from ..entrada import cuerpo_json, entero, texto
from ..errores import Conflicto, NoEncontrado
from ..extensiones import db
from ..modelos import Categoria
from ..paginacion import booleano_de_url, entero_de_url
from ..seguridad import ADMIN, BODEGA, empresa_actual, roles_permitidos

# url_prefix hace que todas las rutas de este archivo empiecen por ahi.
bp = Blueprint("categorias", __name__, url_prefix="/api/inventario/categorias")


def _buscar(categoria_id, empresa_id):
    """Trae una categoria de ESTA empresa, o lanza 404.

    El filtro por empresa_id va siempre: sin el, cambiando el numero de la
    URL se podrian ver datos de otra empresa (RNF19).
    """
    categoria = Categoria.query.filter_by(
        categoria_id=categoria_id, empresa_id=empresa_id
    ).first()
    if categoria is None:
        raise NoEncontrado("La categoria {} no existe".format(categoria_id))
    return categoria


@bp.get("")
def listar():
    """GET /api/inventario/categorias  -> lista de categorias."""
    empresa_id = empresa_actual()
    consulta = Categoria.query.filter_by(empresa_id=empresa_id)

    # ?categoriaPadreId=8 lista las subcategorias de la categoria 8.
    padre = entero_de_url("categoriaPadreId")
    if padre is not None:
        consulta = consulta.filter_by(categoria_padre_id=padre)

    # Por defecto solo las activas, como dice el contrato.
    activo = booleano_de_url("activo", True)
    if activo is not None:
        consulta = consulta.filter_by(activo=activo)

    categorias = consulta.order_by(Categoria.nombre).all()
    return jsonify([c.a_dic() for c in categorias]), 200


@bp.post("")
@roles_permitidos(ADMIN, BODEGA)
def crear():
    """POST /api/inventario/categorias  -> crea una categoria o subcategoria."""
    empresa_id = empresa_actual()
    datos = cuerpo_json("nombre")
    nombre = texto(datos, "nombre", maximo=100, obligatorio=True)
    padre_id = entero(datos, "categoriaPadreId")

    # Si dice ser subcategoria, el padre debe existir y ser de esta empresa.
    if padre_id is not None:
        _buscar(padre_id, empresa_id)

    # Nombre repetido dentro de la empresa -> 409, no 400: los datos estan
    # bien escritos, lo que pasa es que chocan con lo que ya existe.
    if Categoria.query.filter_by(empresa_id=empresa_id, nombre=nombre).first():
        raise Conflicto("Ya existe una categoria llamada '{}'".format(nombre))

    categoria = Categoria(empresa_id=empresa_id, nombre=nombre, categoria_padre_id=padre_id)
    db.session.add(categoria)   # la prepara para guardar
    db.session.commit()         # la escribe en MySQL
    return jsonify(categoria.a_dic()), 201


@bp.get("/<int:categoria_id>")
def consultar(categoria_id):
    """GET /api/inventario/categorias/{id}"""
    return jsonify(_buscar(categoria_id, empresa_actual()).a_dic()), 200


@bp.put("/<int:categoria_id>")
@roles_permitidos(ADMIN, BODEGA)
def actualizar(categoria_id):
    """PUT /api/inventario/categorias/{id}  -> cambia nombre o categoria padre."""
    empresa_id = empresa_actual()
    categoria = _buscar(categoria_id, empresa_id)
    datos = cuerpo_json("nombre")

    nombre = texto(datos, "nombre", maximo=100, obligatorio=True)
    padre_id = entero(datos, "categoriaPadreId")

    # Una categoria no puede ser su propia subcategoria.
    if padre_id == categoria_id:
        raise Conflicto("Una categoria no puede ser subcategoria de si misma")
    if padre_id is not None:
        _buscar(padre_id, empresa_id)

    repetida = Categoria.query.filter(
        Categoria.empresa_id == empresa_id,
        Categoria.nombre == nombre,
        Categoria.categoria_id != categoria_id,
    ).first()
    if repetida:
        raise Conflicto("Ya existe otra categoria llamada '{}'".format(nombre))

    categoria.nombre = nombre
    categoria.categoria_padre_id = padre_id
    db.session.commit()
    return jsonify(categoria.a_dic()), 200


@bp.delete("/<int:categoria_id>")
@roles_permitidos(ADMIN)
def dar_de_baja(categoria_id):
    """DELETE /api/inventario/categorias/{id}  -> baja logica.

    No se borra la fila (decision 8): se marca inactiva. Asi los productos
    que ya la usaban siguen teniendo su categoria y no se rompe el historial.
    """
    empresa_id = empresa_actual()
    categoria = _buscar(categoria_id, empresa_id)

    # No se puede dar de baja si todavia tiene subcategorias activas.
    hijas = Categoria.query.filter_by(
        empresa_id=empresa_id, categoria_padre_id=categoria_id, activo=True
    ).count()
    if hijas:
        raise Conflicto("La categoria tiene {} subcategorias activas".format(hijas))

    # Importacion local para no crear una importacion circular entre modulos.
    from ..modelos import Producto

    productos = Producto.query.filter_by(
        empresa_id=empresa_id, categoria_id=categoria_id, activo=True
    ).count()
    if productos:
        raise Conflicto("La categoria tiene {} productos activos".format(productos))

    categoria.activo = False
    db.session.commit()
    return jsonify(categoria.a_dic()), 200
