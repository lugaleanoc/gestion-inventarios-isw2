"""Tabla de categorias y subcategorias (RF02)."""

from ..extensiones import db


class Categoria(db.Model):
    # Nombre real de la tabla en MySQL.
    __tablename__ = "categorias"
    __table_args__ = (
        # Dentro de una misma empresa no puede haber dos categorias con el
        # mismo nombre. En otra empresa si puede repetirse.
        db.UniqueConstraint("empresa_id", "nombre", name="uq_categoria_empresa_nombre"),
    )

    categoria_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # Referencia logica: la empresa vive en el servicio de Configuracion.
    empresa_id = db.Column(db.Integer, nullable=False, index=True)
    nombre = db.Column(db.String(100), nullable=False)
    # Una subcategoria apunta a su categoria padre. Como el padre esta en
    # esta misma tabla y base, aqui si se puede usar una llave foranea real.
    categoria_padre_id = db.Column(
        db.Integer, db.ForeignKey("categorias.categoria_id"), nullable=True
    )
    # Baja logica (decision 8): nunca se borra la fila, se marca inactiva,
    # asi los productos viejos siguen mostrando su categoria.
    activo = db.Column(db.Boolean, nullable=False, default=True)

    def a_dic(self):
        """Convierte la fila al JSON que define el contrato.

        Ojo: la base usa nombres con guion bajo (categoria_padre_id) y el
        contrato usa estilo camello (categoriaPadreId). La traduccion se
        hace aqui, en un solo lugar.
        """
        return {
            "categoriaId": self.categoria_id,
            "nombre": self.nombre,
            "categoriaPadreId": self.categoria_padre_id,
            "activo": self.activo,
        }
