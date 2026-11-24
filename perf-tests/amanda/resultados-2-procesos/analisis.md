# Análisis de los resultados

Dos corridas completas de las 15 pruebas, el 23 de noviembre de 2026, sobre
Inventario y Reposición con 500 productos sembrados y la base vacía al
empezar cada una.

- **Antes:** un proceso por contenedor (`gunicorn -w 1`) → `resultados-1-proceso/`
- **Después:** dos procesos por contenedor (`gunicorn -w 2`) → `resultados/`

---

## 1. Veredicto frente a los criterios

**Las 15 pruebas cumplen, en las dos configuraciones.** Cero errores en las
tres cargas, incluida la de estrés. Entre las dos corridas se hicieron unas
230.000 peticiones y ninguna falló.

El RNF06 exige responder las consultas en menos de 2 segundos. El peor p95
de todas las pruebas fue **220 ms**, en el descuento de stock bajo estrés.
Son **9 veces mejor** que el límite exigido.

| Escenario | Peor p95 (1 proceso) | Peor p95 (2 procesos) | Errores |
|---|---:|---:|---:|
| Carga normal (10 usuarios) | 23 ms | 22 ms | 0 % |
| Carga pico (50 usuarios) | 20 ms | 23 ms | 0 % |
| Estrés (150 usuarios) | 150 ms | 220 ms | 0 % |

---

## 2. El experimento: por qué se cambió el número de procesos

La primera corrida mostró que las lecturas no se degradaban con la carga y
las escrituras sí. La explicación más probable era que **el contenedor
atendía una petición a la vez**: Gunicorn corría con un solo proceso
trabajador, así que las peticiones hacían fila antes de entrar.

Los números apoyaban esa idea:

| | Trabajo por petición | Peticiones/s | Ocupación del proceso |
|---|---:|---:|---:|
| E1 lectura | ~4 ms | 146,1/s | 58 % |
| E3 escritura | ~7 ms | 134,1/s | 94 % |

Una escritura cuesta casi el doble que una lectura, porque además de
consultar actualiza el saldo e inserta la fila del kardex. Y una fila de
espera no crece proporcional: se dispara cerca del 100 %.

**Había un motivo para tener un solo proceso, y había que arreglarlo
primero.** Las tablas se creaban al arrancar la aplicación, y Gunicorn
ejecuta ese código una vez por proceso: con dos, los dos intentaban crear
las mismas tablas al tiempo y MySQL respondía
`(1050, "Table 'categorias' already exists")`.

Se corrigió separando los dos trabajos: `init_db.py` crea las tablas una
sola vez, antes de arrancar Gunicorn, y la aplicación ya no las crea
(`CREAR_TABLAS=false`). Con eso el número de procesos dejó de estar atado a
la base de datos.

**Hipótesis, escrita antes de medir:** el p95 de E3 bajo estrés debería
bajar de 150 ms a entre 30 y 60 ms.

---

## 3. Resultado: mejoró en casi todo, menos donde se esperaba

De las 15 pruebas, **el p95 mejoró en 12, se mantuvo en 1 y empeoró en 2**.
Las dos que empeoraron son las dos de E3 con más carga.

| Prueba | p95 antes | p95 después | |
|---|---:|---:|---|
| E1 estrés | 12 ms | 11 ms | mejor |
| E2 estrés | 16 ms | 13 ms | mejor |
| E4 estrés | 10 ms | 10 ms | igual |
| **E5 estrés** | **37 ms** | **15 ms** | **mejor, menos de la mitad** |
| **E3 pico** | **20 ms** | **23 ms** | **peor** |
| **E3 estrés** | **150 ms** | **220 ms** | **peor** |

Pero mirar solo el p95 de E3 engaña. Mirando la distribución completa:

| E3 bajo estrés | 1 proceso | 2 procesos | |
|---|---:|---:|---|
| p50, la petición típica | 65 ms | **16 ms** | **4 veces mejor** |
| p95 | 150 ms | 220 ms | peor |
| p99 | 450 ms | 1.500 ms | peor |
| p99,9 | 3.500 ms | 3.200 ms | igual |
| Throughput | 134,1/s | 137,6/s | algo mejor |

**La petición normal pasó de 65 ms a 16 ms, pero las peores empeoraron.**

---

## 4. Hallazgo principal: el cuello de botella se movió

Esto es lo más valioso de todo el ejercicio, y no es lo que esperábamos.

**Con un proceso,** las peticiones hacían fila *antes* de entrar a la
aplicación. Llegaban a la base de datos de una en una, así que nunca se
peleaban entre ellas: el cuello estaba en la aplicación.

**Con dos procesos,** las peticiones entran de a dos y llegan a la base al
mismo tiempo. Ahí aparece algo que antes estaba tapado: `POST
/stock/descuentos` bloquea la fila del stock con `SELECT ... FOR UPDATE`
para que dos ventas simultáneas no dejen el inventario en negativo. Cuando
los dos procesos piden el mismo producto, uno espera a que el otro suelte
la fila.

**El cuello de botella pasó de la aplicación a la base de datos.** Por eso
la petición típica mejoró cuatro veces (ya no hace fila para entrar) y las
peores empeoraron (ahora sí compiten por la misma fila).

La prueba de que es el bloqueo y no otra cosa: **E3 es el único endpoint que
bloquea filas, y es el único que empeoró.** E5, que también escribe pero no
bloquea nada, mejoró a menos de la mitad (37 ms → 15 ms).

### La predicción falló, y eso también se explica

Habíamos predicho que el p95 de E3 bajaría a 30-60 ms. **No pasó: subió a
220 ms.** La predicción acertó en la causa que había medido —el proceso
único— pero no contaba con que al quitarla aparecería otra que estaba
escondida detrás.

Es lo normal al optimizar: quitar un cuello de botella no hace el sistema
infinitamente más rápido, solo deja ver el siguiente.

### Los picos de 3,4 segundos no cambiaron, y eso dice de dónde vienen

En las dos corridas, E3 y E5 tienen peticiones sueltas de unos 3,4
segundos, y el número **casi no se movió** al duplicar los procesos
(3.527 → 3.366 ms en E3; 3.478 → 2.329 ms en E5).

Si fueran por falta de procesos, habrían bajado. Como no bajaron, la causa
es otra, y encaja con una sola cosa: **E3 y E5 son los dos únicos endpoints
que llaman a Configuración y a Proveedores, que no están levantados**. El
timeout de esas llamadas es de 3 segundos. Cada 30 segundos el circuit
breaker deja pasar una petición para comprobar si el servicio revivió, y esa
petición paga el timeout completo.

O sea: **esos picos desaparecen solos cuando los ocho servicios estén
arriba**, y no son un problema de nuestros servicios. Los tres endpoints que
no llaman a nadie (E1, E2, E4) nunca pasaron de 138 ms en ninguna corrida.

---

## 5. Decisión: se queda con dos procesos

Aunque el p95 de E3 empeoró, la configuración de dos procesos es mejor:

- **El p95 mejoró en 12 de las 15 pruebas.**
- **La petición típica de E3 es 4 veces más rápida** (65 → 16 ms).
- **E5 bajo estrés mejoró a menos de la mitad** (37 → 15 ms).
- El throughput subió un poco en las dos escrituras.
- Con un solo proceso, el servicio **no puede atender dos peticiones a la
  vez**, lo cual es una mala propiedad en sí misma, al margen de los números.

Lo que empeoró afecta al 5 % peor de un solo endpoint, bajo una carga que
está por encima de la esperada, y sigue nueve veces por debajo del límite
del RNF06.

**Y la optimización que sigue ya no es poner más procesos.** Para la cola de
E3 habría que atacar el bloqueo: que la fila del stock esté retenida el
menor tiempo posible. Poner cuatro procesos probablemente empeoraría el p95
todavía más, porque habría cuatro peleando por la misma fila en vez de dos.

---

## 6. Lo que estas pruebas NO demostraron

Hay que decirlo, porque un resultado donde todo pasa suele significar que no
se apretó lo suficiente.

**No se encontró el límite del sistema.** El throughput medido fue el que la
propia prueba permitía, no el que el servicio aguanta. Cada usuario virtual
espera entre 0,5 y 1,5 segundos entre peticiones, así que 150 usuarios no
pueden generar más de unas 148 peticiones por segundo por rápido que sea el
servidor. El servicio entregó el 98-100 % de ese tope en las dos corridas.

Si el throughput se hubiera quedado estancado por debajo del tope, ahí sí
habría saturación. No la hubo en ninguna de las dos configuraciones.

**Segunda observación honesta:** esperábamos que la búsqueda de E2 saliera
claramente más lenta, porque `LIKE '%texto%'` obliga a recorrer la tabla
entera. Salió apenas 2 ms por encima de E1. La razón es que **500 productos
son muy pocos**: recorrer 500 filas no le cuesta nada a MySQL. El problema
aparecería con 100.000 productos.

---

## 7. Qué queda para la Entrega 4

- **Encontrar el límite de verdad**, quitando la pausa entre peticiones o
  subiendo mucho los usuarios, hasta que aparezcan errores.
- **Atacar la cola de E3**, que es el único cuello real que quedó, reduciendo
  el tiempo que la fila de stock está bloqueada.
- **Repetir E2 con 100.000 productos**, que es donde el `LIKE` debería doler,
  y ahí sí validar el índice FULLTEXT.
- **Medir con los ocho servicios arriba**, para confirmar que los picos de
  3,4 segundos desaparecen.
- **Medir a través del API Gateway**, para saber cuánto agrega él.
