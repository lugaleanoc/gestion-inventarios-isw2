# Sistema de Gestión de Inventarios — [Nombre de la empresa]

**Ingeniería de Software II — Entrega 1: Investigación y fundamentación**

| | |
|---|---|
| **Equipo** | 6 |
| **Integrantes** | Kevvin Estiben Hernandez jaramillo, Jasmin Camila Gutierrez Maya, Luz Amanda Galeano Ceballos|
| **Fecha de entrega** | 28 de septiembre de 2026 |
| **Repositorio** | https://github.com/lugaleanoc/gestion-inventarios-isw2.git |

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

#### Sistema 3: Oracle SCM Cloud
- **Tipo:** Corporativo / Empresarial
- **Funcionalidades principales:**
  - Seguimiento del ciclo completo de suministros y reabastecimiento en múltiples bodegas.
  - Automatización de pedidos de compra basados en demanda y niveles mínimos de inventario.
  - Auditoría y trazabilidad detallada de la mercancía (números de lote y fechas de vencimiento).
  - Consolidación de métricas e indicadores operativos para la toma de decisiones directivas.
- **Arquitectura (si es identificable):** Arquitectura orientada a servicios (SOA) en la nube corporativa de Oracle.
- **Fortalezas:**
  - Alta capacidad para gestionar grandes volúmenes de datos y múltiples ubicaciones en tiempo real.
  - Estándares estrictos de seguridad, auditoría y control financiero a nivel empresarial.
  - Integración directa con otros sistemas de finanzas, ventas y logística.
- **Debilidades:**
  - Costos de implementación y licencias muy elevados.
  - Proceso de configuración inicial extenso y dependiente de personal especializado.
  - Curva de aprendizaje compleja para los usuarios finales.

### 2.2 Cuadro comparativo

| Criterio | Sistema 1 (Código Abierto) | Sistema 2 (Comercial) | Sistema 3 (Corporativo - Oracle SCM) |
|---|---|---|---|
| **Gestión de productos** | [Completar con tu compañero] | [Completar con tu compañero] | Control avanzado por variantes, lotes, números de serie y estado del producto. |
| **Órdenes de compra** | [Completar con tu compañero] | [Completar con tu compañero] | Generación automática basada en proyecciones de consumo y stock mínimo. |
| **Alertas de stock** | [Completar con tu compañero] | [Completar con tu compañero] | Notificaciones automáticas por desabastecimiento o riesgo de sobrecosto. |
| **Reportes / dashboard** | [Completar con tu compañero] | [Completar con tu compañero] | Paneles analíticos empresariales con indicadores de gestión en tiempo real. |
| **Arquitectura identificada** | [Completar con tu compañero] | [Completar con tu compañero] | Servicios en la nube distribuida (Cloud SOA). |
| **Experiencia de usuario** | [Completar con tu compañero] | [Completar con tu compañero] | Funcional y estructurada para procesos corporativos, requiere capacitación previa. |

### 2.3 Conclusiones

> Qué aprendieron de esta investigación y cómo alimenta el alcance de su propio sistema.
El análisis del sistema corporativo (Oracle SCM) nos permite entender cómo las grandes empresas aseguran la trazabilidad de sus productos y evitan pérdidas mediante la automatización. Aunque su costo y complejidad exceden las necesidades de una PYME, esta investigación nos da las bases para diseñar un sistema propio que tome sus mejores prácticas (alertas automáticas y auditoría de inventario), pero implementado en una arquitectura de microservicios más liviana, ágil y económica.
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
| **Equipo / Integrantes** | Kevvin Estiben Hernandez jaramillo, Jasmin Camila Gutierrez Maya, Luz Amanda Galeano Ceballos |
| **Entrega N.°** | 1 |
| **Periodo cubierto** | 28 de septiembre – 12 de diciembre |

| Fecha | Integrante | Herramienta de IA | Tarea / actividad apoyada | Prompt utilizado (resumen) | Nivel de intervención humana | Resultado / aprendizaje |
|---|---|---|---|---|---|---|
| dd/mm/aaaa | | | | | Alto / Medio / Bajo | |
| dd/mm/aaaa | | | | | Alto / Medio / Bajo | |
| dd/mm/aaaa | | | | | Alto / Medio / Bajo | |

### Reflexión final de la fase

> Párrafo de 5–10 líneas: qué tareas delegaron a la IA y por qué, qué aprendieron, qué errores o limitaciones detectaron en las respuestas de la IA, y cómo verificaron o corrigieron lo generado.

[Escribir reflexión aquí]
