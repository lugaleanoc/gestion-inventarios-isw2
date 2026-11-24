# Reportes y Dashboard (reportes-service)

Flask + MySQL, puerto 8000, base de datos `reportes_db` (solo la caché `cache_reportes`). Ruta base `/api/reportes`.

## Endpoints

| Ruta | Roles |
|---|---|
| GET /dashboard (?localId, fechaDesde, fechaHasta, refrescar) | Todos |
| GET /ventas-por-canal (?localId, fechaDesde, fechaHasta, refrescar) | ADM, VEN |
| GET /inventario (?localId, fechaDesde, fechaHasta, refrescar) | ADM, BOD |
| GET /productos-agotados (?refrescar) | ADM, BOD |
| GET /reposiciones (?refrescar) | ADM, BOD |
| GET /balance (?localId, fechaDesde, fechaHasta, refrescar) | ADM, VEN |
| GET /locales/{localId} (?fechaDesde, fechaHasta, refrescar) | ADM |

Toda respuesta trae `generadoEn`, `desdeCache` y `fuentesNoDisponibles`, más los datos del reporte.

## De dónde sale cada dato

| Reporte | Consulta a |
|---|---|
| Dashboard | Configuración `/dashboard` (qué métricas y preferencias) y, según las métricas elegidas, Ventas, Inventario, Reposición y Balance |
| Ventas por canal | Ventas `/resumen` |
| Inventario y productos agotados | Inventario `/indicadores` |
| Reposiciones | Reposición `/resumen` |
| Balance | Balance `/reporte` (y `/diario` en el dashboard) |
| Local | Configuración `/locales/{id}` (404 si no existe) más Ventas, Inventario y Balance |

Las llamadas llevan `X-Servicio-Origen: reportes` y `X-Empresa-Id`.

## Reporte parcial y caché

- Si un servicio no responde, da error o devuelve algo ilegible, el reporte sale igual con esa parte en `null` y el servicio en `fuentesNoDisponibles`.
- La caché vive en MySQL, por empresa, tipo de reporte y parámetros. Dura 60 segundos (`CACHE_TTL_SEGUNDOS`); un reporte parcial dura 10 (`CACHE_TTL_PARCIAL_SEGUNDOS`). `refrescar=true` la salta.
- Si la base de la caché falla, el reporte se genera igual, sin caché.
- Sin fechas, el periodo son los últimos 30 días; las fechas usan la hora de Colombia (UTC-5).

## Cómo decide el acceso

Solo lo llaman usuarios, a través del Gateway: headers `X-Empresa-Id`, `X-Usuario-Id` y `X-Rol`. Sin `X-Empresa-Id` o `X-Rol`: `401 FALTAN_HEADERS`. Rol sin permiso para ese reporte: `403 SIN_PERMISO`. Ningún servicio puede llamarlo: con `X-Servicio-Origen` responde `403 SIN_PERMISO`.
No maneja tokens.

## Probarlo

Sin Docker ni MySQL (SQLite):

    cd services/reportes
    python -m unittest discover -s tests -t .

Con Docker Compose: pegar `docker-compose.snippet.yml` dentro de `services:` y agregar el volumen `reportes_data:`. Este servicio no publica puerto; se prueba por el Gateway (`http://localhost:8080/api/reportes/...`, con token) o, para pruebas de carga directas, con `perf-tests/kevin/docker-compose.pruebas.yml` (abre el 8003 solo mientras pruebas).

## Variables de entorno

DB_HOST (reportes-db), DB_PORT, DB_NAME (reportes_db), DB_USER, DB_PASSWORD, CACHE_TTL_SEGUNDOS (60), CACHE_TTL_PARCIAL_SEGUNDOS (10), TIMEOUT_CONEXION (2), TIMEOUT_LECTURA (4), ZONA_HORARIA_HORAS (-5). Resiliencia: REINTENTOS (3), REINTENTO_ESPERA (0.2 s, se duplica en cada reintento), CIRCUITO_FALLAS (3), CIRCUITO_SEGUNDOS (5): tras 3 fallas seguidas el circuito de ese servicio se abre 5 s y no se consulta y esa fuente sale en fuentesNoDisponibles. Direcciones de los servicios: CONFIGURACION_URL, INVENTARIO_URL, VENTAS_URL, REPOSICION_URL, BALANCE_URL (por defecto `http://<nombre>-service:8000`).

## Supuestos que hay que confirmar con Amanda y Jasmin

El contrato de la Entrega 2 no detalla la forma exacta de algunas respuestas, así que el servicio acepta varias:

- Inventario `/indicadores`: `productosAgotados` y `productosBajoMinimo` pueden ser un número o una lista de `{productoId, nombre, stockTotal}`. Para que `/productos-agotados` muestre nombres, `productosAgotados` debe ser una lista.
- Reposición `/resumen`: un objeto con el conteo por estado, por ejemplo `{"pendiente": 2, "aprobada": 1}` (también acepta `{"porEstado": {...}}` o una lista de `{estado, cantidad}`).
- Balance `/reporte`: una lista de balances diarios (o un objeto con `balances`/`datos`), cada uno con `disponible` como `{efectivo, tarjeta, qr, total}`.
- Balance `/diario`: `ingresos`, `egresos` y `disponible` con esa misma forma.
- Configuración `/dashboard`: `metricas` como lista de nombres y `preferencias.periodoPorDefecto` con valores como `hoy`, `ultimos_7_dias` o `ultimos_30_dias` (si no lo reconoce usa 30 días).
