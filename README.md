# JAK Inventory

Sistema de gestión de inventarios con arquitectura de microservicios.
Proyecto Ingeniería de Software II.

**Equipo 6:** Jasmin Camila Gutierrez Maya · Luz Amanda Galeano Ceballos ·
Kevvin Estiben Hernandez Jaramillo

---

## Qué hay dentro

Siete microservicios, cada uno con su propia base de datos, más un API
Gateway construido por el equipo que es la única puerta de entrada al
sistema.

| Microservicio | Qué hace | Responsable |
|---|---|---|
| **API Gateway** | Única entrada. Valida el token y enruta hacia los demás | Kevin |
| Configuración | Empresas, locales, stock mínimo y alertas | Jasmin |
| Inventario | Productos, categorías, bodegas, existencias y kardex | Amanda |
| Reposición | Solicitudes de compra, órdenes y recepción de mercancía | Amanda |
| Ventas | Registro de ventas por local y canal | Jasmin |
| Balance Diario | Ingresos y egresos por local | Jasmin |
| Proveedores | Proveedores y qué productos surte cada uno | Kevin |
| Reportes | Dashboard e informes | Kevin |

**Solo el Gateway se expone hacia afuera**, en el puerto 8080. Los demás
servicios únicamente son alcanzables desde la red interna de Docker, así que
no hay forma de saltarse el Gateway (RNF09).

---

## Requisitos

- Docker y Docker Compose
- Python 3 con `requests` (`pip install requests`), solo para las pruebas

Comprueba que están:

```bash
docker --version
docker compose version
python3 --version
```

Si `docker` pide permisos, córrelo con `sudo` delante, o agrégate al grupo
una sola vez y vuelve a entrar a la sesión:

```bash
sudo usermod -aG docker $USER
```

---

## 1. Levantar todo el sistema

Desde la raíz del repositorio:

```bash
docker compose up -d --build
```

La primera vez tarda varios minutos porque construye las ocho imágenes. Las
siguientes son cuestión de segundos.

`-d` deja todo corriendo en segundo plano y te devuelve la terminal.

Comprueba que los once contenedores están arriba:

```bash
docker compose ps
```

Todos deben decir `running`. Las bases de datos además deben decir
`healthy`. Si alguno dice `restarting`, salta a la sección de problemas.

---

## 2. Comprobar que funciona

### El Gateway responde

```bash
curl http://localhost:8080/health
```

Debe responder algo como `{"servicio":"gateway","estado":"ok"}`.

### Cada microservicio responde por dentro

Como no publican puertos, se les pregunta desde dentro de su propio
contenedor:

```bash
for s in configuracion inventario reposicion ventas balance proveedores reportes; do
  printf "%-16s " "$s"
  docker compose exec -T $s python -c "import urllib.request;print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"
done
```

Los siete deben responder `"estado":"ok"`. **Este comando es buen material
para la demo**: demuestra de un golpe que los siete están sanos y que no son
accesibles desde afuera.

### Ver los logs

```bash
docker compose logs -f inventario     # uno en concreto, en vivo
docker compose logs --tail=50         # las últimas líneas de todos
```

Los logs salen en JSON, una línea por petición, con `servicio`, `nivel`,
`mensaje` y `requestId` (RNF10).

---

## 3. Prueba automática de todo el sistema

La forma más rápida de saber si todo está bien:

```bash
python3 tools/smoke_test.py --gateway http://localhost:8080
```

Crea una empresa, hace login y recorre el sistema de punta a punta. Si
termina sin fallos, los ocho servicios están hablando entre sí.

Cada microservicio tiene además su propia prueba de lógica, que corre sin
Docker y sin los demás servicios:

```bash
cd services/inventario && python3 pruebas/prueba_humo.py
cd services/reposicion && python3 pruebas/prueba_humo.py
```

---

## 4. Recorrido completo: el guion de la demo

Todo esto se hace desde la consola, contra `http://localhost:8080`. Cada
paso deja ver una parte distinta del sistema.

### Paso 1 — Registrar la empresa y entrar

```bash
curl -s -X POST http://localhost:8080/api/empresas/registro \
  -H "Content-Type: application/json" \
  -d '{"nombreEmpresa":"JAK Demo","nit":"900123456",
       "administrador":{"nombre":"Amanda","correo":"admin@jak.co","contrasena":"Clave1234"}}'
```

```bash
TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"correo":"admin@jak.co","contrasena":"Clave1234"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

echo $TOKEN
```

A partir de aquí todas las peticiones llevan `-H "Authorization: Bearer $TOKEN"`.

**Qué mostrar:** el token es lo único que viaja desde afuera. El Gateway lo
valida y hacia adentro reenvía solo tres cabeceras con la empresa, el
usuario y el rol.

### Paso 2 — El Gateway bloquea las rutas internas

```bash
curl -i -X POST http://localhost:8080/api/inventario/stock/descuentos \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"ventaId":1,"items":[]}'
```

Debe responder **403**. Esa ruta solo la puede llamar el servicio de Ventas
por la red interna. Es la demostración de que el Gateway no es solo un
reenviador.

### Paso 3 — Configuración: crear un local

```bash
curl -s -X POST http://localhost:8080/api/configuracion/locales \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"nombre":"Local Centro","ciudad":"Manizales"}'
```

Anota el `localId` que devuelve.

### Paso 4 — Proveedores: crear un proveedor

```bash
curl -s -X POST http://localhost:8080/api/proveedores \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"nombre":"Papelera del Eje","nit":"800999111"}'
```

Anota el `proveedorId`.

### Paso 5 — Inventario: categoría, bodega y producto

```bash
curl -s -X POST http://localhost:8080/api/inventario/categorias \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"nombre":"Cuadernos"}'

curl -s -X POST http://localhost:8080/api/inventario/bodegas \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"nombre":"Bodega principal","localId":1}'

curl -s -X POST http://localhost:8080/api/inventario/productos \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"codigo":"CUA-100","nombre":"Cuaderno 100 hojas","categoriaId":1,
       "unidadMedida":"unidad","precio":12500,"proveedorId":1}'
```

**Qué mostrar:** al crear el producto, Inventario llama a Proveedores por
REST para comprobar que ese proveedor existe, porque está en otra base de
datos y MySQL no puede verificarlo.

### Paso 6 — Entrada de mercancía y kardex

```bash
curl -s -X POST http://localhost:8080/api/inventario/movimientos \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"tipo":"entrada","productoId":1,"bodegaId":1,"cantidad":12,
       "motivo":"Compra inicial"}'

curl -s "http://localhost:8080/api/inventario/movimientos?productoId=1" \
  -H "Authorization: Bearer $TOKEN"
```

**Qué mostrar:** cada movimiento queda con quién lo hizo y cuándo, y el
kardex no se edita ni se borra nunca (RNF20).

### Paso 7 — Fijar el stock mínimo

```bash
curl -s -X PUT http://localhost:8080/api/configuracion/stock-minimo/1 \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"stockMinimo":10}'
```

### Paso 8 — Una venta que recorre tres servicios

```bash
curl -s -X POST http://localhost:8080/api/ventas \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"localId":1,"bodegaId":1,"canal":"tienda_fisica","medioPago":"efectivo",
       "items":[{"productoId":1,"cantidad":5}]}'
```

Esa sola petición hace tres cosas:

```bash
curl -s "http://localhost:8080/api/inventario/stock/productos/1" \
  -H "Authorization: Bearer $TOKEN"          # el stock bajó de 12 a 7

curl -s "http://localhost:8080/api/balance/diario?localId=1" \
  -H "Authorization: Bearer $TOKEN"          # el ingreso quedó registrado

curl -s http://localhost:8080/api/inventario/alertas \
  -H "Authorization: Bearer $TOKEN"          # 7 está bajo el mínimo de 10
```

### Paso 9 — El sistema reacciona solo

Al quedar bajo el mínimo, Inventario le avisó a Reposición **sin que nadie
lo pidiera**:

```bash
curl -s http://localhost:8080/api/reposicion/solicitudes \
  -H "Authorization: Bearer $TOKEN"
```

Debe haber una solicitud `pendiente` de origen `automatica`, creada por
`inventario`. Es el momento más vistoso de la demo.

```bash
curl -s -X POST http://localhost:8080/api/reposicion/solicitudes/1/aprobacion \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{}'

curl -s -X POST http://localhost:8080/api/reposicion/ordenes \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"solicitudId":1}'

curl -s -X POST http://localhost:8080/api/reposicion/ordenes/1/recepcion \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"bodegaId":1,"cantidadRecibida":30}'

curl -s "http://localhost:8080/api/inventario/stock/productos/1" \
  -H "Authorization: Bearer $TOKEN"          # el stock subió a 37
```

El círculo se cierra: una venta terminó en una orden de compra recibida.

### Paso 10 — Reportes y aislamiento de fallos

```bash
curl -s http://localhost:8080/api/reportes/dashboard \
  -H "Authorization: Bearer $TOKEN"
```

Ahora se apaga un servicio y se vuelve a pedir el reporte:

```bash
docker compose stop balance

curl -s http://localhost:8080/api/reportes/dashboard \
  -H "Authorization: Bearer $TOKEN"
```

Responde igual, con el campo `fuentesNoDisponibles` indicando que Balance no
contestó. **La caída de un servicio no tumba el sistema** (RNF18).

```bash
docker compose start balance
```

### Paso 11 — Escalar un servicio

```bash
docker compose up -d --scale inventario=3
docker compose ps
```

Tres copias de Inventario atendiendo, sin tocar a los demás (RNF05).

```bash
docker compose up -d --scale inventario=1
```

---

## 5. Ver la documentación de las APIs

Cada servicio publica su contrato OpenAPI en `/docs`, pero como no están
expuestos hay que abrirles el puerto. Para eso está el archivo de apoyo:

```bash
docker compose -f docker-compose.yml -f docker-compose.pruebas.yml up -d
```

| Servicio | Swagger |
|---|---|
| Inventario | http://localhost:8001/docs/ |
| Reposición | http://localhost:8002/docs/ |
| Configuración | http://localhost:8003/docs/ |
| Ventas | http://localhost:8004/docs/ |
| Balance Diario | http://localhost:8005/docs/ |

Los contratos en texto están en `docs/api/`.

Para volver a la configuración normal, sin puertos abiertos:

```bash
docker compose down && docker compose up -d
```

---

## 6. Apagar

```bash
docker compose down        # apaga todo, conserva los datos
docker compose down -v     # apaga y BORRA las bases de datos
```

---

## 7. Pruebas de rendimiento

Cada integrante tiene las suyas en `perf-tests/<nombre>/`, con su plan, su
locustfile y sus resultados. Las instrucciones están en el README de cada
carpeta, por ejemplo `perf-tests/amanda/README.md`.

---

## 8. Si algo falla

**Un contenedor dice `restarting`.** Mira por qué:

```bash
docker compose logs --tail=40 <servicio>
```

**El puerto 8080 está ocupado.** Mira quién lo tiene con
`sudo lsof -i :8080`, o cambia el puerto del Gateway en `docker-compose.yml`
por `"8081:8000"`.

**Un servicio no encuentra su base de datos.** Suele ser que la base todavía
no terminó de arrancar. Espera unos segundos y revisa `docker compose ps`:
las bases deben decir `healthy`.

**Cambié código y no se ve el cambio.** Hay que reconstruir la imagen:

```bash
docker compose up -d --build <servicio>
```

**Quiero empezar de cero.**

```bash
docker compose down -v
docker compose up -d --build
```

**Un script `.sh` no corre en Linux** y dice `bad interpreter` o termina en
`^M`: el archivo quedó con finales de línea de Windows. Se arregla con:

```bash
sed -i 's/\r$//' tools/levantar_local.sh tools/apagar_local.sh
```

---

## Estructura del repositorio

```
services/<servicio>/     código, Dockerfile y pruebas de cada microservicio
docs/api/                los ocho contratos OpenAPI
docs/entrega3/           documento de la entrega
k8s/                     manifiestos de Kubernetes (previstos para la Entrega 4)
perf-tests/<nombre>/     pruebas de rendimiento de cada integrante
tools/                   utilidades: prueba de humo del sistema, mocks, Postman
bitacora/                bitácora de uso de IA
docker-compose.yml       levanta todo el sistema
docker-compose.pruebas.yml  abre puertos, solo para medir y ver los Swagger
```
