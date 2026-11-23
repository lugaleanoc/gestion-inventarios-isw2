from flask import Blueprint, g, jsonify

from .auth import ADM, TODOS, requiere
from .db import get_db
from .validar import cuerpo_json, paginacion, texto

bp = Blueprint("plantilla", __name__, url_prefix="/api/plantilla")


def ejemplo_json(fila):
    return {
        "ejemploId": fila["ejemplo_id"],
        "empresaId": fila["empresa_id"],
        "nombre": fila["nombre"],
        "activo": bool(fila["activo"]),
    }


@bp.get("/")
@requiere(TODOS, ("reportes",))
def listar():
    pagina, por_pagina = paginacion()
    db = get_db()
    total = db.fila("SELECT COUNT(*) AS total FROM ejemplos WHERE empresa_id = %s", (g.empresa_id,))["total"]
    filas = db.filas(
        "SELECT * FROM ejemplos WHERE empresa_id = %s ORDER BY ejemplo_id LIMIT %s OFFSET %s",
        (g.empresa_id, por_pagina, (pagina - 1) * por_pagina),
    )
    return jsonify(
        {
            "datos": [ejemplo_json(f) for f in filas],
            "paginacion": {
                "pagina": pagina,
                "porPagina": por_pagina,
                "total": total,
                "totalPaginas": -(-total // por_pagina),
            },
        }
    )


@bp.post("/")
@requiere(ADM)
def crear():
    nombre = texto(cuerpo_json(), "nombre", 150, obligatorio=True)
    db = get_db()
    nuevo_id = db.ejecutar("INSERT INTO ejemplos (empresa_id, nombre, activo) VALUES (%s, %s, 1)", (g.empresa_id, nombre))
    db.commit()
    return jsonify(ejemplo_json(db.fila("SELECT * FROM ejemplos WHERE ejemplo_id = %s", (nuevo_id,)))), 201
