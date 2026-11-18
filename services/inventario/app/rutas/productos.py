"""Catalogo de productos (RF01) y busqueda (RF12).

Ruta base: /api/inventario/productos
"""

from flask import Blueprint, jsonify, request

from ..clientes import proveedor_existe
from ..entrada import cuerpo_json, decimal, entero, texto
from ..errores import Conflicto, DatosInvalidos, NoEncontrado
from ..extensiones import db
from ..modelos import Categoria, Producto
from ..paginacion import booleano_de_url, entero_de_url, paginar
from ..seguridad import ADMIN, BODEGA, empresa_actual, roles_permitidos

bp = Blueprint("productos", __name__, url_prefix="/api/inventario/productos")


def _buscar(producto_id, empresa_id):
    """Trae un producto de esta empresa, o lanza 404."""
    producto = Producto.query.filter_by(
        producto_id=producto_id, empresa_id=empresa_id
    ).first()
    if producto is None:
        raise NoEncontrado("El producto {} no existe".format(producto_id))
    return producto


def _leer_datos_producto(empresa_id):
    """Valida el cuerpo de un POST o PUT de producto y devuelve los campos.

    Es la misma validacion para crear y para actualizar, por eso esta aparte.
    """
    datos = cuerpo_json("codigo", "nombre", "categoriaId", "unidadMedida", "precio")

    campos = {
        "codigo": texto(datos, "codigo", maximo=50, obligatorio=True),
        "nombre": texto(datos, "nombre", maximo=150, obligatorio=True),
        "descripcion": texto(datos, "descripcion", maximo=500),
        "categoria_id": entero(datos, "categoriaId", obligatorio=True),
        "unidad_medida": texto(datos, "unidadMedida", maximo=30, obligatorio=True),
        "precio": decimal(datos, "precio", obligatorio=True, minimo=0),
        "proveedor_id": entero(datos, "proveedorId"),
    }

    # La categoria vive en esta misma base: se comprueba aqui.
    categoria = Categoria.query.filter_by(
        categoria_id=campos["categoria_id"], empresa_id=empresa_id, activo=True
    ).first()
    if categoria is None:
        raise DatosInvalidos(
            "La categoria {} no existe o esta inactiva".format(campos["categoria_id"])
        )

    # El proveedor vive en OTRO microservicio: hay que preguntarle (decision 6).
    # Si Proveedores no responde, proveedor_existe lanza un 503 y el producto
    # no se crea, para no guardar un proveedorId que quiza no exista.
    if campos["proveedor_id"] is not None and not proveedor_existe(campos["proveedor_id"]):
        raise DatosInvalidos(
            "El proveedor {} no existe".format(campos["proveedor_id"]),
            error="PROVEEDOR_NO_EXISTE",
        )

    return campos


@bp.get("")
def listar():
    """GET /api/inventario/productos  -> lista paginada, con filtros.

    Filtros del contrato: ?q (texto libre), categoriaId, proveedorId, activo.
    """
    empresa_id = empresa_actual()
    consulta = Producto.query.filter_by(empresa_id=empresa_id)

    # Busqueda por nombre o codigo (RF12).
    q = (request.args.get("q") or "").strip()
    if q:
        # ilike = compara sin distinguir mayusculas. El % significa
        # "cualquier cosa antes o despues", asi "cua" encuentra "Cuaderno".
        patron = "%{}%".format(q)
        consulta = consulta.filter(
            db.or_(Producto.nombre.ilike(patron), Producto.codigo.ilike(patron))
        )

    categoria_id = entero_de_url("categoriaId")
    if categoria_id is not None:
        consulta = consulta.filter_by(categoria_id=categoria_id)

    proveedor_id = entero_de_url("proveedorId")
    if proveedor_id is not None:
        consulta = consulta.filter_by(proveedor_id=proveedor_id)

    activo = booleano_de_url("activo", True)
    if activo is not None:
        consulta = consulta.filter_by(activo=activo)

    consulta = consulta.order_by(Producto.nombre)
    return jsonify(paginar(consulta, lambda p: p.a_dic())), 200


@bp.post("")
@roles_permitidos(ADMIN, BODEGA)
def crear():
    """POST /api/inventario/productos"""
    empresa_id = empresa_actual()
    campos = _leer_datos_producto(empresa_id)

    # El codigo identifica al producto dentro de la empresa.
    if Producto.query.filter_by(empresa_id=empresa_id, codigo=campos["codigo"]).first():
        raise Conflicto("Ya existe un producto con el codigo '{}'".format(campos["codigo"]))

    producto = Producto(empresa_id=empresa_id, **campos)
    db.session.add(producto)
    db.session.commit()
    return jsonify(producto.a_dic()), 201


@bp.get("/<int:producto_id>")
def consultar(producto_id):
    """GET /api/inventario/productos/{id}"""
    return jsonify(_buscar(producto_id, empresa_actual()).a_dic()), 200


@bp.put("/<int:producto_id>")
@roles_permitidos(ADMIN, BODEGA)
def actualizar(producto_id):
    """PUT /api/inventario/productos/{id}"""
    empresa_id = empresa_actual()
    producto = _buscar(producto_id, empresa_id)
    campos = _leer_datos_producto(empresa_id)

    # El codigo nuevo no puede ser el de OTRO producto.
    repetido = Producto.query.filter(
        Producto.empresa_id == empresa_id,
        Producto.codigo == campos["codigo"],
        Producto.producto_id != producto_id,
    ).first()
    if repetido:
        raise Conflicto("Ya existe otro producto con el codigo '{}'".format(campos["codigo"]))

    # setattr asigna campo por campo: equivale a producto.nombre = ...,
    # producto.precio = ..., para cada clave del diccionario.
    for nombre_campo, valor in campos.items():
        setattr(producto, nombre_campo, valor)
    db.session.commit()
    return jsonify(producto.a_dic()), 200


@bp.delete("/<int:producto_id>")
@roles_permitidos(ADMIN)
def dar_de_baja(producto_id):
    """DELETE /api/inventario/productos/{id}  -> baja logica.

    El producto se marca inactivo pero no se borra, porque sus movimientos
    siguen en el kardex y las ventas viejas lo siguen nombrando (RNF20).
    """
    producto = _buscar(producto_id, empresa_actual())
    producto.activo = False
    db.session.commit()
    return jsonify(producto.a_dic()), 200
