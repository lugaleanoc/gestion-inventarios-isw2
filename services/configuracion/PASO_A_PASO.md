# Microservicio de Configuración: paso a paso

Guía para entender (y sustentar) cómo se construyó este servicio. Usa la
misma plantilla base que Inventario y Reposición, y que Ventas y Balance
Diario: si entiendes uno, entiendes los demás.

---

## 1. Qué hace este servicio

Guarda los **datos y las reglas de cada empresa**:

- **Empresas**: las crea el API Gateway cuando una empresa se registra. Cada
  empresa trae su `stockMinimoPorDefecto`.
- **Locales**: las sedes de la empresa ("Sede Centro"). Configuración es el
  *dueño* de los locales; Inventario, Ventas y Balance solo guardan el número
  (`localId`).
- **Stock mínimo por producto (RF26)**: cuántas unidades mínimas debe haber.
  Inventario y Reposición lo preguntan aquí.
- **Alertas (RF27)** y **dashboard (RF28)**: qué alertas se muestran y qué
  métricas ve la empresa.

Este servicio **no llama a ningún otro**: solo lo llaman a él.

---

## 2. Paso a paso de lo que se hizo

### Paso 1: la base común de la plantilla

| Archivo | Para qué sirve |
|---------|----------------|
| `app/extensiones.py` | Crea `db`, el objeto de SQLAlchemy para hablar con MySQL |
| `app/errores.py` | Convierte los errores en `{"error": "...", "detalle": "..."}` |
| `app/seguridad.py` | Lee `X-Empresa-Id`, `X-Usuario-Id`, `X-Rol`, `X-Servicio-Origen` y revisa permisos |
| `app/entrada.py` | Valida el JSON que llega (campos obligatorios, números, textos, booleanos) |
| `app/fechas.py` | Fechas en hora de Colombia (`America/Bogota`) |
| `app/rutas/salud.py` | `GET /health`: responde si el servicio y su base están bien |
| `wsgi.py` | Punto de entrada: gunicorn busca aquí la variable `app` |
| `Dockerfile` | Receta de la imagen (`python:3.12-slim`, gunicorn en `0.0.0.0:8000`, HEALTHCHECK) |

> Para la sustentación: "Reutilizamos la misma base en todos los servicios
> para que los errores, la seguridad y los logs se comporten igual en todo
> el sistema."

### Paso 2: la configuración (`app/config.py`)

Lee todo de **variables de entorno** (`DB_HOST`, `DB_NOMBRE`...). La misma
imagen sirve en local y en Docker; solo cambian las variables (RNF14).

### Paso 3: los modelos, o sea las tablas (`app/modelos/`)

| Tabla | Columnas principales | Nota |
|-------|----------------------|------|
| `empresas` | empresa_id, nombre, nit (único), stock_minimo_por_defecto, activa, fecha_creacion | La crea el Gateway |
| `locales` | local_id, empresa_id, nombre (único por empresa), direccion, ciudad, activo | Baja lógica: nunca se borra la fila |
| `stock_minimo` | empresa_id, producto_id, stock_minimo | Solo los productos con valor propio |
| `config_alertas` | empresa_id (PK), stock_minimo, producto_agotado, reposicion_pendiente | Una fila por empresa |
| `config_dashboard` | empresa_id (PK), metricas (JSON), local_por_defecto, periodo_por_defecto | Una fila por empresa |

> **Referencia lógica (RNF02):** `producto_id` no es llave foránea, porque
> el producto vive en *otra base de datos* (la de Inventario). Cada servicio
> tiene su propia base y su propio usuario de MySQL, que no puede entrar a
> las demás.

### Paso 4: las rutas (`app/rutas/`)

Cada ruta dice **quién** puede llamarla con el decorador `permitir`:

```python
@bp.get("/<int:producto_id>")
@permitir(roles=TODOS_LOS_ROLES, servicios=("inventario", "reposicion", "reportes"))
def consultar(producto_id): ...

@bp.put("/<int:producto_id>")
@permitir(roles=[ADMIN])          # sin "servicios": ningún microservicio puede
def definir(producto_id): ...
```

| Archivo | Rutas |
|---------|-------|
| `empresas.py` | `POST /empresas` (solo Gateway), `GET`/`PUT /empresa` |
| `locales.py` | `GET`/`POST /locales`, `GET`/`PUT`/`DELETE /locales/{id}` |
| `stock_minimo.py` | `GET /stock-minimo`, `GET`/`PUT /stock-minimo/{id}` |
| `preferencias.py` | `GET`/`PUT /alertas`, `GET`/`PUT /dashboard` |

Detalle de `GET /stock-minimo/{id}`: si el producto **no** tiene un mínimo
propio, no responde 404. Devuelve el `stockMinimoPorDefecto` de la empresa
con `"origen": "por_defecto"`. Así Inventario siempre recibe un número.

`POST /empresas` es especial: no lleva `X-Empresa-Id` (la empresa todavía no
existe), solo `X-Servicio-Origen: gateway`. Al crearla también se crean sus
alertas y su dashboard con valores por defecto.

### Paso 5: armar la aplicación (`app/__init__.py`)

La "fábrica" `crear_app()`:
1. Carga la configuración.
2. Conecta la base (`db.init_app`).
3. Registra los manejadores de error.
4. Antes de cada petición, lee la identidad de los headers.
5. Después de cada petición, escribe una línea de log en JSON a la salida
   estándar (se ve con `docker compose logs`).
6. Registra las rutas, publica Swagger en `/docs/` y crea las tablas.

**Crear las tablas reintentando:** al hacer `docker compose up`, el servicio
puede arrancar antes de que MySQL acepte conexiones. Por eso `db.create_all()`
se intenta cada 3 segundos hasta 30 veces. Esto también resuelve que los 2
workers de gunicorn intenten crear las tablas al mismo tiempo.

### Paso 6: Docker Compose (en la raíz)

- `docker-compose.yml`: cada integrante **agrega** su bloque sin cambiar el de
  los demás. Arriba están Inventario y Reposición (Amanda), cada uno con su
  propio MySQL. Abajo está lo mío: el contenedor `mysql` compartido (con
  `docker/mysql/init.sql`, que crea una base y un usuario por servicio) y
  Configuración, Ventas y Balance. **Mis servicios no publican puertos**:
  desde afuera solo se entrará por el API Gateway (8080).
- Redes: los servicios de Amanda usan la red `default` del proyecto; los míos
  están en `default` (para que Ventas llame a `inventario-service`) y en `jak-red`.
- `docker-compose.pruebas.yml`: publica mis puertos para probar sin Gateway:
  Configuración **8003**, Ventas 8004, Balance 8005. No se usan 8001 y 8002
  porque ya los publica Amanda (Inventario y Reposición).

### Paso 7: pruebas

- **Prueba de humo** (`pruebas/prueba_humo.py`): comprueba la lógica con
  SQLite en memoria, sin MySQL. Revisa permisos, errores y que una empresa
  no vea los datos de otra.
- **Locust** (`perf-tests/jasmin`): E1 y E2 son de este servicio.

---

## 3. Recorrido de una petición (para explicarlo en la sustentación)

Inventario pregunta: "¿cuál es el stock mínimo del producto 105?"

```
Inventario --GET /api/configuracion/stock-minimo/105-->  Configuración
           headers: X-Empresa-Id: 1, X-Servicio-Origen: inventario

1. before_request  -> seguridad.leer_identidad() guarda empresa=1, servicio=inventario
2. @permitir       -> ¿llegó X-Empresa-Id? (si no: 401 FALTAN_HEADERS)
                      ¿"inventario" está en la lista de servicios? (si no: 403 SIN_PERMISO)
3. stock_minimo.consultar(105)
4. SELECT * FROM stock_minimo WHERE empresa_id=1 AND producto_id=105
5a. hay fila -> {"productoId":105, "stockMinimo":10, "origen":"producto"}
5b. no hay   -> {"productoId":105, "stockMinimo":5,  "origen":"por_defecto"}   (el de la empresa)
6. after_request   -> log en JSON con el requestId
```

---

## 4. Cómo probarlo

```bash
# 1) Levantar (desde la raíz del repositorio)
docker compose -f docker-compose.yml -f docker-compose.pruebas.yml up -d --build
curl http://localhost:8003/health

# 2) Crear la empresa (como el Gateway)
curl -X POST http://localhost:8003/api/configuracion/empresas \
  -H "X-Servicio-Origen: gateway" -H "Content-Type: application/json" \
  -d '{"nombre":"Papelería La Estrella","nit":"900123456-7"}'

# 3) Crear un local y definir el stock mínimo del producto 105
curl -X POST http://localhost:8003/api/configuracion/locales \
  -H "X-Empresa-Id: 1" -H "X-Usuario-Id: 1" -H "X-Rol: administrador" \
  -H "Content-Type: application/json" -d '{"nombre":"Sede Centro","ciudad":"Manizales"}'
curl -X PUT http://localhost:8003/api/configuracion/stock-minimo/105 \
  -H "X-Empresa-Id: 1" -H "X-Usuario-Id: 1" -H "X-Rol: administrador" \
  -H "Content-Type: application/json" -d '{"stockMinimo":10}'

# 4) Consultarlo como lo hace Inventario
curl http://localhost:8003/api/configuracion/stock-minimo/105 \
  -H "X-Empresa-Id: 1" -H "X-Servicio-Origen: inventario"

# 5) Swagger en el navegador: http://localhost:8003/docs/

# 6) Prueba de humo (sin Docker)
cd services/configuracion && pip install -r requirements.txt && python pruebas/prueba_humo.py

# 7) Apagar
docker compose -f docker-compose.yml -f docker-compose.pruebas.yml down
```

---

## 5. Preguntas que te pueden hacer

**¿Por qué este servicio no valida el token JWT?**
Lo valida el API Gateway, una sola vez. Después reenvía quién es el usuario
en los headers `X-Usuario-Id`, `X-Empresa-Id` y `X-Rol`.

**¿Qué pasa si alguien llama sin pasar por el Gateway?**
No trae `X-Empresa-Id` y recibe `401 FALTAN_HEADERS`. Además, en
`docker-compose.yml` mis servicios no publican puertos: desde afuera solo se
entrará por el Gateway.

**¿Cómo evitas que una empresa vea los datos de otra (RNF19)?**
Todas las consultas filtran por `empresa_id`, que sale del header. Si pides
un local de otra empresa, recibes 404 como si no existiera.

**¿Por qué `producto_id` no es llave foránea?**
Porque el producto está en la base de Inventario. Cada microservicio tiene su
propia base y su propio usuario de MySQL (RNF02). Es una referencia lógica.

**¿Un microservicio puede cambiar el stock mínimo?**
No. Las rutas de escritura solo aceptan el rol `administrador`; si llega una
llamada interna, responde 403. Cada ruta lista qué servicios pueden llamarla.

**¿Quién puede cambiar la configuración (RF29)?**
Solo el rol `administrador`. Un vendedor que lo intente recibe 403 SIN_PERMISO.

**¿Por qué no se borran los locales?**
Por la baja lógica (decisión 8): se marca `activo = false`. Así no se pierden
las ventas y balances que apuntan a ese local.

**¿Por qué tzdata en requirements.txt?**
La imagen `python:3.12-slim` no trae las zonas horarias; sin `tzdata`,
`ZoneInfo("America/Bogota")` falla.
