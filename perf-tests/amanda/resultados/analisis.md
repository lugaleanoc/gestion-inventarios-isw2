# Análisis de los resultados

Tres corridas completas de las 15 pruebas, el 23 de noviembre de 2026,
sobre Inventario y Reposición con 500 productos sembrados y la base vacía al
empezar cada una.

| Carpeta | Carga | Procesos | Para qué |
|---|---|---|---|
| `resultados-1-proceso/` | 10 / 50 / 150 | 1 | Experimento de optimización: antes |
| `resultados-2-procesos/` | 10 / 50 / 150 | 2 | Experimento de optimización: después |
| **`resultados/`** | **20 / 100 / 300** | **2** | **Medición oficial, con los niveles acordados por el equipo** |

---

## 1. Veredicto frente a los criterios

**Las 15 pruebas cumplen.** Cero errores en las tres cargas, incluida la de
estrés con 300 usuarios: unas 110.000 peticiones y ninguna falló.

El RNF06 exige responder las consultas en menos de 2 segundos. El peor p95
de toda la corrida fue **490 ms**, en el descuento de stock bajo estrés.
Sigue estando **4 veces por debajo** del límite exigido.

| Escenario | Peor p95 | Peor máximo | Errores |
|---|---:|---:|---:|
| Carga normal (20 usuarios) | 21 ms | 96 ms | 0 % |
| Carga pico (100 usuarios) | 18 ms | 122 ms | 0 % |
| Estrés (300 usuarios) | 490 ms | 576 ms | 0 % |

---

## 2. Hallazgo principal: se encontró el límite del sistema

Con 150 usuarios el servicio nunca llegó a saturarse. Con 300 sí, y solo en
un endpoint. La prueba está en cómo responde el throughput al duplicar los
usuarios:

| Endpoint | Tipo | 150 usuarios | 300 usuarios | Subida |
|---|---|---:|---:|---:|
| E1 consulta de stock | lectura | 146,0/s | 287,5/s | **+97 %** |
| E2 búsqueda | lectura | 145,6/s | 285,4/s | **+96 %** |
| E4 resumen | lectura | 146,4/s | 288,1/s | **+97 %** |
| E5 solicitud automática | escritura | 143,9/s | 280,8/s | **+95 %** |
| **E3 descuento de stock** | **escritura** | **137,6/s** | **214,7/s** | **+56 %** |

Cuatro endpoints doblaron su throughput al doblar los usuarios: siguen
teniendo capacidad de sobra. **El descuento de stock no pudo: se quedó en
+56 %.** Ese es el límite del sistema, y está en unas **215 peticiones por
segundo** para esa operación.

### Cómo se ve la saturación en los tiempos

| E3 descuento de stock | 150 usuarios | 300 usuarios |
|---|---:|---:|
| p50 | 16 ms | 410 ms |
| p95 | 220 ms | 490 ms |
| p99 | 1.500 ms | 530 ms |
| Máximo | 3.366 ms | 576 ms |

Fíjate en la forma, que es lo interesante: con 150 usuarios los tiempos
estaban muy separados (16 ms la petición típica, 1.500 ms la peor); con 300
están todos juntos entre 410 y 576 ms.

**Eso es exactamente cómo se ve una fila saturada.** Cuando un servicio
todavía tiene capacidad, la mayoría pasa rápido y solo unas pocas esperan.
Cuando se satura, todas hacen la misma fila y todas esperan casi lo mismo.
Es la diferencia entre llegar a un banco con dos personas delante y llegar
cuando ya hay fila: ahí todos esperan igual.

### Por qué se satura justo ese endpoint

`POST /stock/descuentos` es el único que **bloquea la fila del stock** con
`SELECT ... FOR UPDATE`, para que dos ventas simultáneas no dejen el
inventario en negativo. Mientras una petición tiene la fila tomada, las
demás que quieren ese producto esperan turno. Con 300 usuarios pidiendo
sobre 500 productos, la coincidencia deja de ser rara y se vuelve constante.

**Ese bloqueo no es un defecto, es la protección funcionando.** El precio de
que el stock nunca quede negativo es que las escrituras hagan fila. La
prueba le pone número a ese precio: el sistema aguanta unas 215 ventas por
segundo antes de que la fila se note.

### El sistema se degrada bien

Vale la pena señalarlo: al saturarse, el servicio **no falló, solo se puso
más lento**, y de forma pareja. Cero errores, cero peticiones perdidas, y
aun así cuatro veces por debajo del límite de 2 segundos. Un sistema que al
saturarse empieza a devolver errores es mucho peor que uno que se pone
lento de forma predecible.

---

## 3. La optimización que se propuso, se midió y se validó

Antes de la medición oficial se hizo un experimento, que explica por qué los
contenedores corren como corren hoy.

**El problema.** La primera corrida se hizo con un solo proceso por
contenedor (`gunicorn -w 1`), porque con dos fallaba el arranque: las tablas
se creaban al iniciar la aplicación, y Gunicorn ejecuta ese código una vez
por proceso, así que los dos intentaban crearlas al tiempo y MySQL respondía
`(1050, "Table 'categorias' already exists")`.

**La corrección.** Se separaron los dos trabajos: `init_db.py` crea las
tablas una sola vez antes de arrancar Gunicorn, y la aplicación ya no las
crea. Con eso el número de procesos dejó de depender de la base de datos y
se pudo volver a dos.

**El resultado**, midiendo las mismas 15 pruebas antes y después:

| | 1 proceso | 2 procesos | |
|---|---:|---:|---|
| p95, en cuántas pruebas mejoró | — | **12 de 15** | |
| E3, petición típica (p50) bajo estrés | 65 ms | **16 ms** | 4 veces mejor |
| E5, p95 bajo estrés | 37 ms | **15 ms** | menos de la mitad |
| E3, p95 bajo estrés | 150 ms | 220 ms | peor |

**La predicción falló, y eso también se explica.** Se había predicho que el
p95 de E3 bajaría a 30-60 ms. Bajó la petición típica, pero el p95 subió. La
razón: con un proceso las peticiones hacían fila *antes* de entrar a la
aplicación y llegaban a la base de una en una, así que nunca competían por
el bloqueo. Con dos, llegan a la vez y ahí aparece la competencia que antes
estaba tapada. **El cuello de botella se movió de la aplicación a la base de
datos**, y es el mismo cuello que la corrida oficial con 300 usuarios acabó
de confirmar.

La prueba de que es el bloqueo y no otra cosa: E3 es el único endpoint que
bloquea filas, y es el único que empeoró y el único que se satura. E5, que
también escribe pero no bloquea nada, mejoró y escala sin problema.

---

## 4. Otras observaciones

**Las lecturas no se inmutaron.** Con 300 usuarios, la consulta de stock
respondió en 11 ms de p95 y el resumen de reposición en 7 ms. Su límite está
por encima de lo que 300 usuarios simulados pueden pedirles.

**Los picos de 3,4 segundos desaparecieron.** En las corridas anteriores
aparecían peticiones sueltas de unos 3,4 s en E3 y E5, siempre el mismo
valor, causadas por el timeout de 3 segundos hacia Configuración y
Proveedores, que no estaban levantados: cada 30 segundos el circuit breaker
deja pasar una petición para comprobar si el servicio revivió. En esta
corrida no aparecen, porque las pruebas duran 1 minuto en vez de 3 y el
circuito pasa abierto casi todo el tiempo. El máximo de E3 fue 576 ms.

**La búsqueda sigue sin dolerle.** Esperábamos que E2 saliera claramente más
lenta, porque `LIKE '%texto%'` obliga a recorrer la tabla entera. Con 300
usuarios llegó a 22 ms de p95. La razón es que **500 productos son muy
pocos**: recorrer 500 filas no le cuesta nada a MySQL. El problema aparecería
con 100.000 productos.

---

## 5. Qué queda para la Entrega 4

- **Atacar la cola de E3**, que es el único cuello real: reducir el tiempo
  que la fila de stock está bloqueada. Poner más procesos ya no sirve, al
  contrario: habría más peticiones compitiendo por la misma fila.
- **Repetir E2 con 100.000 productos**, que es donde el `LIKE` debería doler,
  y ahí sí validar el índice FULLTEXT.
- **Medir con los ocho servicios arriba**, para confirmar que los picos del
  timeout no reaparecen.
- **Medir a través del API Gateway**, para saber cuánto agrega él.
