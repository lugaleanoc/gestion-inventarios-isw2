# Microservicio de Configuración

Catálogo de empresas y locales, y reglas de cada empresa: stock mínimo,
alertas y dashboard (RF26, RF27, RF28). Responsable: Jasmin.

Contrato: `docs/configuracion-openapi.yaml` (copia de `docs/api/configuracion-openapi.yaml`, v1.1.0).
Swagger: `http://localhost:8003/docs/` con el compose de pruebas.

## Endpoints

| Método | Ruta | Quién puede |
|--------|------|-------------|
| GET | `/health` | público |
| POST | `/api/configuracion/empresas` | solo `X-Servicio-Origen: gateway` (sin `X-Empresa-Id`) |
| GET / PUT | `/api/configuracion/empresa` | GET: cualquier rol o interno · PUT: administrador |
| GET / POST | `/api/configuracion/locales` | GET: cualquier rol o interno · POST: administrador |
| GET / PUT / DELETE | `/api/configuracion/locales/{id}` | GET: cualquier rol o interno · PUT/DELETE (baja lógica): administrador |
| GET | `/api/configuracion/stock-minimo` | cualquier rol o interno |
| GET / PUT | `/api/configuracion/stock-minimo/{productoId}` | GET: cualquier rol o interno · PUT: administrador |
| GET / PUT | `/api/configuracion/alertas` | GET: cualquier rol o Inventario · PUT: administrador |
| GET / PUT | `/api/configuracion/dashboard` | GET: cualquier rol o Reportes · PUT: administrador |

- No valida JWT: lee `X-Empresa-Id`, `X-Usuario-Id` y `X-Rol` (los pone el Gateway).
- Falta `X-Empresa-Id` → `401 {"error": "FALTAN_HEADERS", ...}`.
- Rol o servicio sin permiso → `403 {"error": "SIN_PERMISO", ...}`. Un
  microservicio solo entra a las rutas donde el contrato lo permite.
- Si un producto no tiene stock mínimo propio, se devuelve el
  `stockMinimoPorDefecto` de la empresa con `origen = por_defecto`.

## Cómo correrlo

Desde la raíz del repositorio:

```bash
# Con los puertos de prueba publicados (8003 = Configuración)
docker compose -f docker-compose.yml -f docker-compose.pruebas.yml up -d --build
docker compose logs -f configuracion
```

Con solo `docker-compose.yml` el servicio no publica puertos: se llega a él
por la red interna (`http://configuracion-service:8000`) o, cuando exista,
por el API Gateway.

## Probarlo sin el Gateway

```bash
# Crear la empresa (como lo haría el Gateway)
curl -X POST http://localhost:8003/api/configuracion/empresas \
  -H "X-Servicio-Origen: gateway" -H "Content-Type: application/json" \
  -d '{"nombre": "Papelería La Estrella", "nit": "900123456-7"}'

H='-H X-Empresa-Id:1 -H X-Usuario-Id:1 -H X-Rol:administrador'

# Crear un local
curl -X POST http://localhost:8003/api/configuracion/locales $H \
  -H "Content-Type: application/json" -d '{"nombre": "Sede Centro", "ciudad": "Manizales"}'

# Definir el stock mínimo del producto 105
curl -X PUT http://localhost:8003/api/configuracion/stock-minimo/105 $H \
  -H "Content-Type: application/json" -d '{"stockMinimo": 10}'

# Consultarlo como lo hace Inventario (llamada interna)
curl http://localhost:8003/api/configuracion/stock-minimo/105 \
  -H "X-Empresa-Id: 1" -H "X-Servicio-Origen: inventario"
```

## Pruebas

```bash
cd services/configuracion
pip install -r requirements.txt
python pruebas/prueba_humo.py     # lógica completa, con SQLite en memoria (sin MySQL)
```

Rendimiento (RNF06) con Locust: `perf-tests/jasmin/PLAN_PRUEBAS.md`.
Explicación paso a paso para la sustentación: `PASO_A_PASO.md`.
