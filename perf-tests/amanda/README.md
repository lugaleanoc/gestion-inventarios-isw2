# Pruebas de rendimiento — Amanda

Plan y ejecución de las 15 pruebas de rendimiento sobre los microservicios
de **Inventario** y **Reposición** (RNF11).

Herramienta: **Locust**, la acordada por el equipo.

---

## 1. Qué se mide y por qué

| Métrica | Qué significa | Por qué se mide |
|---|---|---|
| **Tiempo de respuesta p50** | La mitad de las peticiones responde más rápido que esto | Es lo que siente un usuario normal |
| **Tiempo de respuesta p95** | El 95 % responde más rápido que esto | Es la métrica que importa: el promedio esconde los casos lentos |
| **Tiempo de respuesta p99** | El 99 % responde más rápido que esto | Muestra los peores casos, los que generan quejas |
| **Throughput** | Peticiones atendidas por segundo | Cuánto aguanta el servicio |
| **Tasa de error** | Porcentaje de peticiones fallidas | Un servicio rápido que falla no sirve |

**Por qué p95 y no el promedio.** Si 99 peticiones responden en 10 ms y una
en 5 segundos, el promedio da 60 ms y parece excelente, pero hubo un
usuario esperando 5 segundos. El p95 no se deja engañar por eso.

## 2. Criterios de aceptación

Salen del RNF06 del documento de requerimientos, que exige responder las
consultas en menos de 2 segundos bajo una carga definida por el equipo.

- **p95 por debajo de 2000 ms** en carga normal y en carga pico.
- **Tasa de error por debajo del 1 %** en carga normal y en carga pico.

En la prueba de **estrés no se exige cumplir**: el objetivo de esa prueba
es justamente encontrar el punto donde el servicio deja de cumplir. Una
prueba de estrés en la que nada falla no enseña nada.

## 3. Los tres escenarios

| Escenario | Usuarios | Rampa | Duración | Qué representa |
|---|---:|---:|---|---|
| Carga normal | 20 | 5/s | 1 min | Un día común de la empresa |
| Carga pico | 100 | 25/s | 1 min | Hora de más ventas |
| Estrés | 300 | 50/s | 1 min | Buscar dónde empieza a fallar |

Estos niveles los acordó el equipo el 23 de noviembre, para que los tres
integrantes midan con los mismos números y los resultados se puedan
comparar entre sí.

Cada usuario simulado espera entre 0,5 y 1,5 segundos entre una petición y
la siguiente, como haría una persona que lee la pantalla antes de volver a
hacer clic. Sin esa pausa, 10 usuarios pegarían como 200 y el número no
representaría nada real.

## 4. Las 15 pruebas

Cinco endpoints, cada uno en los tres escenarios. Los endpoints se
escogieron para cubrir los dos microservicios, lecturas y escrituras, y
consultas de distinto peso.

| # | ID | Endpoint | Servicio | Tipo | Por qué este |
|---:|---|---|---|---|---|
| 1 | E1-normal | `GET /api/inventario/stock/productos/{id}` | Inventario | Lectura | El endpoint más usado: cada venta lo consulta |
| 2 | E1-pico | " | " | " | " |
| 3 | E1-estres | " | " | " | " |
| 4 | E2-normal | `GET /api/inventario/productos?q=` | Inventario | Lectura | Búsqueda con `LIKE`, que no aprovecha bien los índices |
| 5 | E2-pico | " | " | " | " |
| 6 | E2-estres | " | " | " | " |
| 7 | E3-normal | `POST /api/inventario/stock/descuentos` | Inventario | Escritura | Bloquea la fila de stock y escribe el kardex |
| 8 | E3-pico | " | " | " | " |
| 9 | E3-estres | " | " | " | " |
| 10 | E4-normal | `GET /api/reposicion/resumen` | Reposición | Lectura | Consulta con dos `GROUP BY` |
| 11 | E4-pico | " | " | " | " |
| 12 | E4-estres | " | " | " | " |
| 13 | E5-normal | `POST /api/reposicion/solicitudes/automaticas` | Reposición | Escritura | Escritura con comprobación previa de duplicados |
| 14 | E5-pico | " | " | " | " |
| 15 | E5-estres | " | " | " | " |

**Qué esperamos de cada uno, antes de medir.** Escribir esto antes sirve
para saber si el resultado tiene sentido o si algo está mal montado:

- **E1** debería ser el más rápido: una consulta filtrada por índice.
- **E2** más lento que E1, porque `LIKE '%texto%'` obliga a recorrer la tabla.
- **E3** el más lento de todos bajo carga alta: escribe y bloquea la fila,
  así que los usuarios tienen que hacer fila para el mismo producto.
- **E4** rápido, aunque agrupa, porque la tabla es pequeña.
- **E5** intermedio: consulta antes de insertar.

**Por qué no se mide a través del API Gateway.** Las peticiones van
directo a cada servicio, mandando a mano las cabeceras que normalmente
pondría el Gateway. Si el Gateway estuviera en el medio, estaríamos
midiendo dos servicios a la vez y no sabríamos cuál de los dos es el
lento. Medir una pieza a la vez es lo correcto.

---

## 5. Cómo ejecutarlas

### Antes de empezar

```bash
pip install locust requests
```

### Paso 1 — Levantar los servicios

Desde la raíz del repositorio:

```bash
docker compose -f docker-compose.yml -f docker-compose.pruebas.yml up -d inventario reposicion
docker compose ps          # los dos deben decir "running"
```

Los dos archivos: el `docker-compose.yml` normal **no publica ningún
puerto**, porque al sistema solo se entra por el API Gateway (RNF09).
`docker-compose.pruebas.yml` los abre solo mientras se mide, porque Locust
corre fuera de Docker y necesita alcanzar los servicios.

Inventario queda en `http://localhost:8001` y Reposición en `http://localhost:8002`.

Al terminar de medir, para volver a la configuración normal:

```bash
docker compose down && docker compose up -d
```

### Paso 2 — Sembrar datos

```bash
cd perf-tests/amanda
python datos_de_prueba.py --productos 500
```

Medir sobre una base vacía no sirve: cualquier consulta es instantánea
porque no hay nada que buscar. Esto crea 500 productos con existencias y
guarda sus ids en `datos_sembrados.json`.

### Paso 3 — Ejecutar

```bash
python ejecutar.py
```

Son unos 20 minutos y no hay que hacer nada mientras tanto. Opciones
útiles si algo sale mal o quieres ir por partes:

```bash
python ejecutar.py --escenario normal   # solo las 5 de carga normal
python ejecutar.py --solo E3            # los 3 escenarios de un endpoint
python ejecutar.py --prueba E3-estres   # una sola
```

### Paso 4 — Armar la tabla de resultados

```bash
python resumen.py
```

Deja `resultados/resumen.md` con las tablas listas para pegar en el
informe, y el veredicto de cada prueba frente a los criterios.

---

## 6. Qué mirar en los resultados

1. **¿El p95 crece mucho entre normal y pico?** Si pasa de 20 ms a 1500 ms
   con solo cinco veces más usuarios, el servicio no escala bien y hay que
   decir por qué.
2. **¿Dónde aparece el primer error?** Ese es el límite del servicio y es
   el dato más valioso de toda la prueba.
3. **¿El throughput deja de subir?** Si con 50 usuarios atiende 40
   peticiones por segundo y con 150 sigue atendiendo 40, el servicio ya
   está saturado: los usuarios de más solo hacen fila.
4. **Las primeras peticiones de E5.** Este endpoint intenta llamar a
   Configuración y a Proveedores, que no están levantados. Las primeras
   peticiones serán lentas y luego se vuelven rápidas: es el **circuit
   breaker** abriéndose. Se ve en `resultados/E5-*_stats_history.csv` y es
   un buen detalle para mencionar en la sustentación.

---

## 7. Optimización propuesta

El enunciado pide proponer y validar optimizaciones. La más sencilla de
medir, y la que más suele rendir:

**Subir los procesos trabajadores de Gunicorn de 2 a 4.**

Hoy cada contenedor corre con `-w 2`, o sea dos procesos atendiendo
peticiones. Si la prueba de estrés muestra que el throughput se queda
estancado mientras la CPU no está al tope, significa que faltan procesos y
no potencia.

Cómo validarlo:

1. Guardar los resultados actuales (renombrar la carpeta `resultados` a `resultados-2workers`).
2. En `services/inventario/Dockerfile`, cambiar `-w 2` por `-w 4`.
3. `docker compose up -d --build inventario`
4. Repetir solo la prueba de estrés de E1 y E3: `python ejecutar.py --escenario estres --solo E1`
5. Comparar el throughput y el p95 de antes y después.

Segunda opción, si sobra tiempo: la búsqueda de E2 usa `LIKE '%texto%'`,
que obliga a MySQL a recorrer toda la tabla. Un índice **FULLTEXT** sobre
`nombre` permitiría usar `MATCH ... AGAINST` y debería mejorar mucho con
tablas grandes. Es más trabajo porque toca cambiar la consulta del
servicio, no solo la base.

---

## 8. Archivos de esta carpeta

| Archivo | Qué hace |
|---|---|
| `README.md` | Este plan |
| `datos_de_prueba.py` | Siembra productos, bodegas y existencias |
| `locustfile.py` | Define las 5 pruebas: a qué endpoint pega cada una |
| `ejecutar.py` | Corre las 15 pruebas y guarda los CSV |
| `resumen.py` | Lee los CSV y arma la tabla del informe |
| `resultados/` | Lo que produce Locust, más `resumen.md` |
