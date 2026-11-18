# Microservicio de Inventario

Administra productos, categorias y bodegas, controla las existencias y
mantiene el kardex. Responsable: Amanda.

Contrato: `docs/inventario-openapi.yaml` (el mismo de la Entrega 2).
Requerimientos cubiertos: RF01, RF02, RF04, RF05, RF09-RF14, RF17.

## Como correrlo en local

```bash
cd services/inventario
cp .env.ejemplo .env            # ajustar los datos de MySQL si hace falta
python -m venv .venv            # entorno virtual, para no ensuciar el Python del sistema
source .venv/bin/activate       # en Windows:  .venv\Scripts\activate
pip install -r requirements.txt
python wsgi.py
```

Queda en http://localhost:8000 y la documentacion en http://localhost:8000/docs/

## Como correrlo con Docker

```bash
docker build -t jak/inventario:1.0 .
docker run -p 8000:8000 --env-file .env jak/inventario:1.0
```

O, con la base de datos incluida, desde la raiz del repositorio:

```bash
docker compose up inventario-db inventario
```

## Probar sin el API Gateway

Mientras el Gateway no este listo, se llama al servicio directo mandando a
mano las cabeceras que normalmente pondria el Gateway:

```bash
curl http://localhost:8000/api/inventario/productos \
  -H "X-Empresa-Id: 1" -H "X-Usuario-Id: 1" -H "X-Rol: administrador"
```

Sin esas cabeceras la respuesta es 401, que es justamente lo que se quiere:
nadie entra sin identificarse.

## Estructura

```
app/
  __init__.py      fabrica de la aplicacion: arma todo y registra las rutas
  config.py        configuracion leida de variables de entorno
  extensiones.py   la instancia de SQLAlchemy (db)
  errores.py       excepciones propias -> respuestas {error, detalle}
  seguridad.py     identidad que manda el Gateway y permisos por rol
  entrada.py       validacion del cuerpo JSON de las peticiones
  paginacion.py    parametros de la URL y formato {datos, paginacion}
  operaciones.py   reglas de negocio del stock y del kardex
  modelos/         las tablas de MySQL
  rutas/           los endpoints, agrupados por tema
  clientes/        llamadas REST a Configuracion, Proveedores y Reposicion
```

## Decisiones que vale la pena recordar para la sustentacion

- **Este servicio no valida el token JWT.** Lo valida el Gateway y reenvia
  `X-Usuario-Id`, `X-Empresa-Id` y `X-Rol`. Evita repetir la logica ocho veces.
- **Todas las consultas filtran por `empresa_id`** (RNF19).
- **Los movimientos no se editan ni se borran** (RNF20): se corrigen con un
  movimiento de tipo `ajuste` que apunta al original.
- **No hay llaves foraneas hacia otros servicios** (RNF02): `localId` y
  `proveedorId` son referencias logicas y se validan por REST.
- **Las llamadas a otros servicios llevan timeout, reintentos y circuit
  breaker** (RF30), y las que no son criticas no tumban la operacion.
- **El stock se bloquea con `SELECT ... FOR UPDATE`** al descontar, para que
  dos ventas simultaneas no dejen el inventario en negativo.
