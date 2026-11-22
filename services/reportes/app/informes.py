from .config import METRICAS, PERIODO_POR_DEFECTO_DIAS, PERIODOS_DIAS
from .fuentes import NO_ENCONTRADO

CLAVES_VALOR_ROTACION = ("unidadesSalidas", "valor", "cantidad")
CLAVES_VALOR_AGOTADO = ("stockTotal", "valor", "cantidad")


def producto_reporte(item, claves_valor, por_defecto=None):
    if not isinstance(item, dict):
        return None
    valor = por_defecto
    for clave in claves_valor:
        if item.get(clave) is not None:
            valor = item[clave]
            break
    return {"productoId": item.get("productoId"), "nombre": item.get("nombre"), "valor": valor}


def lista_productos(valor, claves_valor, por_defecto=None):
    if not isinstance(valor, list):
        return []
    productos = [producto_reporte(item, claves_valor, por_defecto) for item in valor]
    return [p for p in productos if p is not None]


def conteo(valor):
    if isinstance(valor, list):
        return len(valor)
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return int(valor)
    return None


def es_numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def sumar_totales(items):
    totales = {"efectivo": 0, "tarjeta": 0, "qr": 0, "total": 0}
    for item in items:
        if isinstance(item, dict):
            for clave in totales:
                if es_numero(item.get(clave)):
                    totales[clave] += item[clave]
    return totales


def por_estado(datos):
    if isinstance(datos, dict):
        for clave in ("porEstado", "conteo", "estados"):
            if isinstance(datos.get(clave), dict):
                return {k: v for k, v in datos[clave].items() if es_numero(v)}
        return {k: v for k, v in datos.items() if es_numero(v)}
    if isinstance(datos, list):
        resultado = {}
        for item in datos:
            if isinstance(item, dict) and "estado" in item:
                cantidad = item.get("cantidad", item.get("total"))
                if es_numero(cantidad):
                    resultado[item["estado"]] = cantidad
        return resultado
    return {}


def lista_balances(datos):
    if isinstance(datos, list):
        return datos
    if isinstance(datos, dict):
        for clave in ("balances", "datos", "dias"):
            if isinstance(datos.get(clave), list):
                return datos[clave]
    return []


def ventas(f, p):
    d = f.datos("ventas", "/api/ventas/resumen", p.consulta())
    base = {"localId": p.local_id, "fechaDesde": p.desde.isoformat(), "fechaHasta": p.hasta.isoformat()}
    if not isinstance(d, dict):
        return {**base, "totalVentas": None, "cantidadVentas": None, "porCanal": None, "porMedioPago": None}
    return {
        **base,
        "totalVentas": d.get("totalVentas"),
        "cantidadVentas": d.get("cantidadVentas"),
        "porCanal": d.get("porCanal"),
        "porMedioPago": d.get("porMedioPago"),
    }


def indicadores(f, p):
    d = f.datos("inventario", "/api/inventario/indicadores", p.consulta())
    return d if isinstance(d, dict) else None


def inventario(f, p):
    base = {"localId": p.local_id, "fechaDesde": p.desde.isoformat(), "fechaHasta": p.hasta.isoformat()}
    d = indicadores(f, p)
    if d is None:
        return {
            **base,
            "valorTotal": None,
            "cantidadProductos": None,
            "productosAgotados": None,
            "productosBajoMinimo": None,
            "mayorRotacion": [],
            "menorRotacion": [],
        }
    return {
        **base,
        "valorTotal": d.get("valorTotal"),
        "cantidadProductos": d.get("cantidadProductos"),
        "productosAgotados": conteo(d.get("productosAgotados")),
        "productosBajoMinimo": conteo(d.get("productosBajoMinimo")),
        "mayorRotacion": lista_productos(d.get("mayorRotacion"), CLAVES_VALOR_ROTACION),
        "menorRotacion": lista_productos(d.get("menorRotacion"), CLAVES_VALOR_ROTACION),
    }


def productos_agotados(f, p):
    d = indicadores(f, p)
    if d is None:
        return {"total": None, "productos": []}
    agotados = d.get("productosAgotados")
    return {
        "total": conteo(agotados),
        "productos": lista_productos(agotados, CLAVES_VALOR_AGOTADO, por_defecto=0),
    }


def reposiciones(f):
    d = f.datos("reposicion", "/api/reposicion/resumen")
    if d is None:
        return {"porEstado": None, "total": None}
    estados = por_estado(d)
    return {"porEstado": estados, "total": sum(estados.values())}


def balance(f, p):
    base = {"localId": p.local_id, "fechaDesde": p.desde.isoformat(), "fechaHasta": p.hasta.isoformat()}
    d = f.datos("balance", "/api/balance/reporte", p.consulta())
    if d is None:
        return {**base, "balances": None, "disponible": None}
    balances = lista_balances(d)
    return {
        **base,
        "balances": balances,
        "disponible": sumar_totales([b.get("disponible") for b in balances if isinstance(b, dict)]),
    }


def balance_del_dia(f, p):
    params = {"fecha": p.hasta.isoformat()}
    if p.local_id is not None:
        params["localId"] = p.local_id
    d = f.datos("balance", "/api/balance/diario", params)
    return d if isinstance(d, dict) else None


def metrica(nombre, f, p):
    if nombre == "ventas_por_canal":
        return ventas(f, p)
    if nombre == "productos_baja_rotacion":
        d = indicadores(f, p)
        return {"productos": lista_productos(d.get("menorRotacion"), CLAVES_VALOR_ROTACION) if d else []}
    if nombre == "productos_agotados":
        return productos_agotados(f, p)
    if nombre == "estado_reposiciones":
        return reposiciones(f)
    if nombre == "balance_diario":
        return balance_del_dia(f, p)
    if nombre == "ingresos_egresos":
        d = balance_del_dia(f, p)
        return None if d is None else {"ingresos": d.get("ingresos"), "egresos": d.get("egresos")}
    if nombre == "valor_inventario":
        d = indicadores(f, p)
        return None if d is None else {"valorTotal": d.get("valorTotal")}
    return None


def configuracion_dashboard(f):
    estado, d = f.consultar("configuracion", "/api/configuracion/dashboard")
    if not isinstance(d, dict):
        return list(METRICAS), {}
    elegidas = d.get("metricas")
    elegidas = [m for m in elegidas if m in METRICAS] if isinstance(elegidas, list) else list(METRICAS)
    preferencias = d.get("preferencias") if isinstance(d.get("preferencias"), dict) else {}
    return elegidas, preferencias


def dias_del_periodo(preferencias):
    return PERIODOS_DIAS.get(str(preferencias.get("periodoPorDefecto", "")).lower(), PERIODO_POR_DEFECTO_DIAS)


def local_por_defecto(preferencias):
    valor = preferencias.get("localPorDefecto")
    return valor if isinstance(valor, int) and not isinstance(valor, bool) and valor > 0 else None


def reporte_de_local(f, p, local_id):
    estado, local = f.consultar("configuracion", f"/api/configuracion/locales/{local_id}")
    if estado == NO_ENCONTRADO:
        return None
    return {
        "local": local,
        "fechaDesde": p.desde.isoformat(),
        "fechaHasta": p.hasta.isoformat(),
        "ventas": ventas(f, p),
        "inventario": inventario(f, p),
        "balance": balance(f, p),
    }
