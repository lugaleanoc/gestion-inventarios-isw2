"""Tabla de productos (RF01)."""

from ..extensiones import db


class Producto(db.Model):
    __tablename__ = "productos"
    __table_args__ = (
        # El codigo identifica al producto para la empresa: no se repite.
        db.UniqueConstraint("empresa_id", "codigo", name="uq_producto_empresa_codigo"),
        # Indice para que la busqueda por nombre (RF12) no recorra la tabla entera.
        db.Index("ix_producto_empresa_nombre", "empresa_id", "nombre"),
    )

    producto_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    empresa_id = db.Column(db.Integer, nullable=False, index=True)
    codigo = db.Column(db.String(50), nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.String(500), nullable=True)
    # La categoria si vive en esta base, asi que es llave foranea real.
    categoria_id = db.Column(
        db.Integer, db.ForeignKey("categorias.categoria_id"), nullable=False, index=True
    )
    unidad_medida = db.Column(db.String(30), nullable=False)
    # Numeric(12, 2) = hasta 12 digitos con 2 decimales. Para dinero nunca se
    # usa Float, porque pierde centavos al redondear.
    precio = db.Column(db.Numeric(12, 2), nullable=False)
    # Referencia logica: el proveedor vive en el microservicio de Proveedores.
    proveedor_id = db.Column(db.Integer, nullable=True, index=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)

    def a_dic(self):
        return {
            "productoId": self.producto_id,
            "empresaId": self.empresa_id,
            "codigo": self.codigo,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "categoriaId": self.categoria_id,
            "unidadMedida": self.unidad_medida,
            # float() porque Numeric devuelve un Decimal, que no es JSON.
            "precio": float(self.precio),
            "proveedorId": self.proveedor_id,
            "activo": self.activo,
        }
