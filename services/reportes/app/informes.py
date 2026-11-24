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


ESTADOS_REPOSICION = ("pendiente", "aprobada", "en_orden", "recibida", "rechazada")


def ventas(f, p):
    d = f.datos("ventas", "/api/ventas/resumen", p.consulta())
    d = d if isinstance(d, dict) else {}
    return {
        "porCanal": d.get("porCanal") or {"tienda_fisica": 0, "tienda_web": 0},
        "porMedioPago": d.get("porMedioPago") or {"efectivo": 0, "tarjeta": 0, "qr": 0},
        "totalVentas": d.get("totalVentas") or 0,
        "cantidadVentas": d.get("cantidadVentas") or 0,
    }


def indicadores(f, p):
    d = f.datos("inventario", "/api/inventario/indicadores", p.consulta())
    return d if isinstance(d, dict) else {}


def inventario(f, p):
    d = indicadores(f, p)
    return {
        "valorTotal": d.get("valorTotal") or 0,
        "cantidadProductos": d.get("cantidadProductos") or 0,
        "mayorRotacion": lista_productos(d.get("mayorRotacion"), CLAVES_VALOR_ROTACION, 0),
        "menorRotacion": lista_productos(d.get("menorRotacion"), CLAVES_VALOR_ROTACION, 0),
    }


def productos_agotados(f, p):
    d = indicadores(f, p)
    return {
        "agotados": lista_productos(d.get("productosAgotados"), CLAVES_VALOR_AGOTADO, 0),
        "bajoMinimo": lista_productos(d.get("productosBajoMinimo"), CLAVES_VALOR_AGOTADO, 0),
    }


def reposiciones(f):
    d = f.datos("reposicion", "/api/reposicion/resumen")
    estados = por_estado(d)
    resultado = {estado: estados.get(estado, 0) for estado in ESTADOS_REPOSICION}
    resultado.update({k: v for k, v in estados.items() if k not in resultado})
    return {"porEstado": resultado}


def totales_vacios():
    return {"efectivo": 0, "tarjeta": 0, "qr": 0, "total": 0}


def dia_de(balance_diario):
    return str(balance_diario.get("fecha", "")) if isinstance(balance_diario, dict) else ""


def balance(f, p):
    d = f.datos("balance", "/api/balance/reporte", p.consulta())
    balances = [b for b in lista_balances(d) if isinstance(b, dict)]
    ultimo_por_local = {}
    for b in sorted(balances, key=dia_de):
        ultimo_por_local[b.get("localId")] = b
    return {
        "ingresos": sumar_totales([b.get("ingresos") for b in balances]),
        "egresos": sumar_totales([b.get("egresos") for b in balances]),
        "disponible": sumar_totales([b.get("disponible") for b in ultimo_por_local.values()]),
    }


def balance_del_dia(f, p):
    params = {"fecha": p.hasta.isoformat()}
    if p.local_id is not None:
        params["localId"] = p.local_id
    d = f.datos("balance", "/api/balance/diario", params)
    return d if isinstance(d, dict) else {}


def metrica(nombre, f, p):
    if nombre == "ventas_por_canal":
        return ventas(f, p)["porCanal"]
    if nombre == "productos_baja_rotacion":
        return inventario(f, p)["menorRotacion"]
    if nombre == "productos_agotados":
        return len(productos_agotados(f, p)["agotados"])
    if nombre == "estado_reposiciones":
        return reposiciones(f)["porEstado"]
    if nombre == "balance_diario":
        return balance_del_dia(f, p)
    if nombre == "ingresos_egresos":
        d = balance_del_dia(f, p)
        return {"ingresos": d.get("ingresos") or totales_vacios(), "egresos": d.get("egresos") or totales_vacios()}
    if nombre == "valor_inventario":
        return inventario(f, p)["valorTotal"]
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
    estado, _ = f.consultar("configuracion", f"/api/configuracion/locales/{local_id}")
    if estado == NO_ENCONTRADO:
        return None
    v = ventas(f, p)
    i = indicadores(f, p)
    b = balance(f, p)
    return {
        "localId": local_id,
        "inventario": {
            "valorTotal": i.get("valorTotal") or 0,
            "productosAgotados": len(lista_productos(i.get("productosAgotados"), CLAVES_VALOR_AGOTADO, 0)),
        },
        "ventas": {"totalVentas": v["totalVentas"], "cantidadVentas": v["cantidadVentas"]},
        "balance": {
            "ingresos": b["ingresos"]["total"],
            "egresos": b["egresos"]["total"],
            "disponible": b["disponible"]["total"],
        },
    }
