# Sistema de Gestión de Inventarios — [Nombre de la empresa]

**Ingeniería de Software II — Entrega 1: Investigación y fundamentación**

| | |
|---|---|
| **Equipo** | [Nombre del equipo] |
| **Integrantes** | [Nombre 1], [Nombre 2], [Nombre 3], [Nombre 4] |
| **Fecha de entrega** | 28 de septiembre de 2026 |
| **Repositorio** | [enlace al repo de GitHub] |

---

## Tabla de contenido

1. [Presentación de la empresa](#1-presentación-de-la-empresa)
2. [Investigación de sistemas similares](#2-investigación-de-sistemas-similares)
3. [Definición del problema y alcance](#3-definición-del-problema-y-alcance)
4. [Justificación de la arquitectura de microservicios](#4-justificación-de-la-arquitectura-de-microservicios)
5. [Identificación preliminar de microservicios](#5-identificación-preliminar-de-microservicios)
6. [Requerimientos funcionales y no funcionales](#6-requerimientos-funcionales-y-no-funcionales)
7. [Bitácora de uso de IA](#7-bitácora-de-uso-de-ia)

---

## 1. Presentación de la empresa

> Empresa real o ficticia elegida, y por qué.

- **Nombre de la empresa:**
- **Sector / actividad económica:**
- **Tamaño (n.º de empleados, bodegas, sucursales, etc.):**
- **Situación actual del inventario:** (manual, hojas de cálculo, sistema obsoleto, etc.)
- **Por qué eligieron esta empresa como caso de estudio:**

---

## 2. Investigación de sistemas similares

> Mínimo 3 sistemas de gestión de inventarios existentes (comerciales, open source o corporativos).

### 2.1 Sistemas analizados

#### Sistema 1: [nombre]
- **Tipo:** (comercial / open source / corporativo)
- **Funcionalidades principales:**
- **Arquitectura (si es identificable):**
- **Fortalezas:**
- **Debilidades:**

#### Sistema 2: [nombre]
- **Tipo:**
- **Funcionalidades principales:**
- **Arquitectura (si es identificable):**
- **Fortalezas:**
- **Debilidades:**

#### Sistema 3: [nombre]
- **Tipo:**
- **Funcionalidades principales:**
- **Arquitectura (si es identificable):**
- **Fortalezas:**
- **Debilidades:**

### 2.2 Cuadro comparativo

| Criterio | Sistema 1 | Sistema 2 | Sistema 3 |
|---|---|---|---|
| Gestión de productos | | | |
| Control de stock multi-bodega | | | |
| Órdenes de compra | | | |
| Alertas de stock | | | |
| Reportes / dashboard | | | |
| Arquitectura identificada | | | |
| Experiencia de usuario | | | |

### 2.3 Conclusiones

> Qué aprendieron de esta investigación y cómo alimenta el alcance de su propio sistema.

---

## 3. Definición del problema y alcance

### 3.1 Problema

> Qué problema real tiene la empresa elegida con su manejo actual de inventario.

### 3.2 Alcance del sistema a construir

> Qué va a resolver el sistema (y qué explícitamente queda fuera de alcance para este semestre).

---

## 4. Justificación de la arquitectura de microservicios

> Comparación monolito vs. microservicios para este caso específico, con criterios técnicos explícitos (no genéricos).

| Criterio técnico | Monolito | Microservicios | Por qué pesa más para este caso |
|---|---|---|---|
| Escalabilidad | | | |
| Mantenibilidad | | | |
| Despliegue independiente | | | |
| Tolerancia a fallos | | | |
| Organización del equipo de trabajo | | | |

### Conclusión de la justificación

> Por qué microservicios es la decisión correcta para *este* problema particular (no una afirmación genérica).

---

## 5. Identificación preliminar de microservicios

> Dominios / bounded contexts identificados y su responsabilidad. Ajustar según la lista de RF de la sección 6.

| Microservicio | Responsabilidad / dominio |
|---|---|
| Productos | |
| Inventario / Stock | |
| Proveedores | |
| Órdenes de compra | |
| Usuarios / Autenticación | |
| Notificaciones | |
| Reportes | |

> Mecanismo de comunicación entre servicios previsto (REST síncrono, mensajería asíncrona, o ambos) y por qué.

---

## 6. Requerimientos funcionales y no funcionales

> Base tomada del enunciado del curso; ajustar/ampliar según la empresa elegida y justificar cualquier cambio.

### 6.1 Requerimientos funcionales (RF)

| ID | Descripción |
|---|---|
| RF01 | Gestión de productos (crear, consultar, actualizar, dar de baja) |
| RF02 | Gestión de categorías y subcategorías |
| RF03 | Gestión de proveedores |
| RF04 | Control de stock (entradas, salidas, ajustes, traslados) |
| RF05 | Gestión de almacenes/bodegas |
| RF06 | Órdenes de compra a proveedores |
| RF07 | Gestión de usuarios y roles |
| RF08 | Autenticación de usuarios |
| RF09 | Alertas de stock bajo umbral mínimo |
| RF10 | Trazabilidad y auditoría (kardex) |
| RF11 | Reportes (existencias, valorización, rotación) |
| RF12 | Búsqueda y filtrado de productos |
| RF13 | Gestión de devoluciones |
| RF14 | Panel de indicadores (dashboard) |

### 6.2 Requerimientos no funcionales (RNF)

| ID | Descripción |
|---|---|
| RNF01 | Arquitectura de microservicios |
| RNF02 | Persistencia independiente por microservicio |
| RNF03 | Contenerización con Docker |
| RNF04 | Orquestación con Kubernetes (obligatorio) |
| RNF05 | Escalabilidad independiente por servicio |
| RNF06 | Rendimiento: respuestas < 2 s bajo carga concurrente definida |
| RNF07 | Seguridad (JWT/OAuth2, cifrado de contraseñas) |
| RNF08 | Documentación de API (OpenAPI/Swagger) |
| RNF09 | API Gateway propio (sin Kong ni terceros) |
| RNF10 | Observabilidad (logging centralizado) |
| RNF11 | 15 pruebas de rendimiento por integrante |
| RNF12 | Control de versiones en GitHub con evidencia individual |
| RNF13 | Mantenibilidad (bajo acoplamiento, alta cohesión) |
| RNF14 | Portabilidad (Docker + Kubernetes) |
| RNF15 | Solo tecnologías vistas en clase |
| RNF16 | Uso documentado de IA (bitácora) |

---

## 7. Bitácora de uso de IA

| Proyecto | Sistema de Gestión de Inventarios – [Nombre de la empresa] |
|---|---|
| **Equipo / Integrantes** | [Nombres completos] |
| **Entrega N.°** | 1 |
| **Periodo cubierto** | [fecha inicial] – [fecha final] |

| Fecha | Integrante | Herramienta de IA | Tarea / actividad apoyada | Prompt utilizado (resumen) | Nivel de intervención humana | Resultado / aprendizaje |
|---|---|---|---|---|---|---|
| dd/mm/aaaa | | | | | Alto / Medio / Bajo | |
| dd/mm/aaaa | | | | | Alto / Medio / Bajo | |
| dd/mm/aaaa | | | | | Alto / Medio / Bajo | |

### Reflexión final de la fase

> Párrafo de 5–10 líneas: qué tareas delegaron a la IA y por qué, qué aprendieron, qué errores o limitaciones detectaron en las respuestas de la IA, y cómo verificaron o corrigieron lo generado.

[Escribir reflexión aquí]
