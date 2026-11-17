# Microservicio de Reposicion

Gestiona las solicitudes de reposicion (automaticas y manuales), su
aprobacion, las ordenes de compra y la recepcion de mercancia.
Responsable: Amanda.

Contrato: `docs/reposicion-openapi.yaml` (el mismo de la Entrega 2).
Requerimientos cubiertos: RF06, RF18, RF19, RF20.

## El ciclo completo

```
Inventario avisa (stock bajo)
        v
   solicitud pendiente --rechazo--> rechazada
        |
    aprobacion
        v
     aprobada --se emite la orden--> en_orden
                                        |
                             llega la mercancia
                                        v
                                    recibida   -> Inventario sube el stock
```

Si la orden se cancela, la solicitud vuelve a `aprobada`, no a
`pendiente`: ya alguien la autorizo, lo que se cayo fue la compra.

## Como correrlo

```bash
cd services/reposicion
cp .env.ejemplo .env
python -m venv .venv && source .venv/bin/activate   # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
python wsgi.py
```

Con Docker, desde la raiz del repositorio: `docker compose up reposicion`.
Queda en http://localhost:8002 y el Swagger en http://localhost:8002/docs/

## Probar sin los demas servicios

```bash
python pruebas/prueba_humo.py
```

Recorre el ciclo completo con SQLite en memoria, reemplazando las
llamadas a Inventario, Proveedores y Configuracion por funciones falsas.
No necesita MySQL ni que los companeros hayan terminado.

Para probarlo a mano, con las cabeceras que normalmente pone el Gateway:

```bash
curl -X POST http://localhost:8002/api/reposicion/solicitudes \
  -H "X-Empresa-Id: 1" -H "X-Usuario-Id: 1" -H "X-Rol: administrador" \
  -H "Content-Type: application/json" \
  -d '{"productoId": 105, "cantidadSugerida": 20}'
```

## Decisiones que vale la pena recordar para la sustentacion

- **No se abren dos solicitudes del mismo producto al tiempo.** Mientras
  una siga pendiente, aprobada o con orden, un nuevo aviso de stock bajo
  devuelve la que ya existe (200) en vez de crear otra.
- **La cantidad sugerida se calcula**, no la inventa el usuario: se repone
  hasta tres veces el stock minimo, para no quedar justo en el umbral y
  volver a disparar la alerta enseguida.
- **En la recepcion, el orden de los pasos importa.** Primero se escribe el
  cambio sin confirmar, despues se le avisa a Inventario, y solo si
  Inventario respondio bien se confirma. Si se hiciera al reves quedaria
  una orden recibida con el stock sin subir.
- **La llamada a Inventario al recibir es obligatoria** (si falla, 503 y la
  orden sigue emitida), mientras que las de Proveedores y Configuracion no
  lo son: una solicitud se puede crear sin saber el proveedor.
- **Los archivos de apoyo estan repetidos en cada microservicio a
  proposito**: no se comparte una libreria comun, para que cada servicio se
  pueda cambiar y desplegar solo (RNF01, RNF13).
