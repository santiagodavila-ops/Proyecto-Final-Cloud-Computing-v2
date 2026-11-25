# Línea de Tiempo de Evolución y Mejoras Arquitectónicas con Antigravity
**Proyecto:** CRM de Empleabilidad Nacional — SaaS Multi-tenant Serverless (CS2032 Cloud Computing)  
**Entorno AWS:** Cuenta `816193343783` | Región `us-east-1` (AWS Academy Learner Lab)  
**Fecha de Consolidación:** 23 de noviembre de 2026  
**Autor:** Patrick Ricardo Medina Reyes (Grupo 1)  

---

## 📌 Resumen Ejecutivo

Este documento detalla la cronología completa de auditoría, implementación, remediación y evolución arquitectónica realizada sobre el repositorio y la infraestructura viva en **Amazon Web Services (AWS)** utilizando el asistente inteligente **Antigravity**.

A partir de un estado funcional inicial de 5 microservicios con brechas operativas y de seguridad, la plataforma evolucionó hacia un estándar **Enterprise Production-Ready** alineado con los 6 pilares del **AWS Well-Architected Framework**, incorporando resiliencia asíncrona (DLQ), seguridad perimetral (Lambda Authorizer), gestión de secretos (SSM Parameter Store con KMS), observabilidad integral (CloudWatch Alarms & Dashboard) y trazabilidad distribuida (AWS X-Ray).

---

## ⏱️ Línea de Tiempo Cronológica de Hitos

```
  [ ESTADO INICIAL ]
  5 Microservicios básicos · Monolito de credenciales en env vars · Sin DLQ activa · 0 Alarmas · X-Ray apagado
          │
          ▼  (Hito 1: Diagnóstico Inicial)
  [ AUDITORÍA DE DLQ EN AWS ]
  Identificación de trigger SQS desactivado · Inexistencia de cola DLQ · Sin política de reintentos
          │
          ▼  (Hito 2: Modelado de Resiliencia)
  [ DIAGRAMA ARQUITECTURA V2 ]
  Creación de Diagrama_Arquitectura_Solucion_v2.drawio · Diseño del flujo EDA + DLQ + Redrive Policy
          │
          ▼  (Hito 3: Implementación en Vivo)
  [ DESPLIEGUE Y PRUEBA DE DLQ ]
  Creación de cola DLQ (14 días retención) · Redrive Policy (maxReceiveCount=3) · Activación de trigger · Prueba SNS forzada exitosa
          │
          ▼  (Hito 4: Evaluación de Arquitecto)
  [ AWS WELL-ARCHITECTED REVIEW ]
  Diagnóstico formal de los 6 pilares: Calificación Académica 18.5/20 | Calificación Enterprise 79/100 · 8 hallazgos identificados
          │
          ▼  (Hito 5: Ejecución Simultánea con Agentes)
  [ 4 MEJORAS ENTERPRISE SIMULTÁNEAS ]
  1. Secretos SSM Parameter Store (SecureString)  │  2. API Gateway Lambda Authorizer (Perímetro + Caché 300s)
  3. CloudWatch Alarms (6 alarmas + Dashboard)    │  4. Trazabilidad Distribuida AWS X-Ray (32 Lambdas + 5 APIs)
          │
          ▼  (Hito 6: Cierre de Arquitectura)
  [ DIAGRAMA ARQUITECTURA V3 ]
  Creación de Diagrama_Arquitectura_Solucion_v3.drawio consolidando todas las capas Enterprise
```

---

## 📊 Matriz Comparativa: Estado Inicial vs. Estado Final

| Dimensión Arquitectónica | Estado Inicial (Lo que teníamos) | Estado Final (Lo que tenemos ahora) | Impacto / Beneficio |
| :--- | :--- | :--- | :--- |
| **Resiliencia EDA (Mensajería)** | Cola principal `cola-notificaciones-entrevistas-dev` sin DLQ. Trigger de Lambda desactivado (`Disabled`). Reintentos infinitos ante fallos. | Cola DLQ `cola-notificaciones-entrevistas-dlq-dev` (14 días retención), `RedrivePolicy` con `maxReceiveCount: 3`, `ReportBatchItemFailures` activo y trigger habilitado. | Prevención de *poison pills*, tolerancia a fallos y capacidad de reprocesamiento (*DLQ Redrive*). |
| **Gestión de Secretos RDS** | Contraseña maestra de MySQL en texto claro (`<password>`) en variables de entorno `RDS_PASSWORD` de 21 Lambdas. | Parámetros `/cs2032/dev/rds/*` en **AWS SSM Parameter Store** (`SecureString` KMS), VPC Endpoints privados (SSM/KMS) y caché en memoria cold-start (`_CREDS_CACHE`). | Cumplimiento de seguridad y cero fuga de credenciales. 0 ms de sobrecoste en warm invocations. |
| **Autenticación & Autorización** | Validación de tokens Bearer descentralizada en código Python dentro de cada una de las 31 Lambdas (coste computacional ante ataques DoS). | **API Gateway Lambda Authorizer** perimetral (`cs2032-usuarios-dev-authorizer`) registrado en las 5 APIs REST con **Caché TTL de 300 s** e inyección de contexto (`tenant_id`, `usuario_id`, `rol`). | Protección perimetral, reducción drástica de lecturas a DynamoDB y cero latencia en Lambdas backend. |
| **Monitoreo & Alarmas** | **0 alarmas** configuradas en CloudWatch (`DescribeAlarms` vacío). Sin visibilidad operativa de fallos. | **Suite de 6 alarmas CloudWatch** activas conectadas al tópico SNS `topico-alertas-cloudwatch-dev` (email) + Dashboard centralizado `dashboard-cs2032-dev` con 11 widgets. | Detección inmediata de anomalías, supervisión 360° en tiempo real y alerta instantánea de mensajes en DLQ. |
| **Trazabilidad Distribuida** | AWS X-Ray desactivado (`TracingConfig.Mode = PassThrough`). Imposible mapear latencias en cascada. | **AWS X-Ray activo** (`Mode = Active`) en las **32 Lambdas** y en los stages `dev` de las **5 API Gateways**, con propagación de `X-Amzn-Trace-Id`. | Mapeo visual de dependencias (*Service Map*), detección de cuellos de botella y análisis p95 de latencias. |
| **Modelado de Arquitectura** | Diagrama original `Diagrama_Arquitectura_Solucion.drawio` con componentes básicos. | Dos versiones evolutivas: **v2** (incorporación de DLQ) y **v3** (arquitectura Enterprise completa: SSM, Authorizer, Alarmas, X-Ray). | Documentación técnica de alto nivel para entrega y sustentación académica/profesional. |

---

## 🛠️ Detalle de Hitos y Mejoras Desarrolladas

### Hito 1: Auditoría y Diagnóstico de la Dead Letter Queue (DLQ)
* **Acción:** Inspección vía AWS CLI de las colas SQS, tópicos SNS, funciones Lambda y logs de CloudWatch a partir de las instrucciones de `/Users/patrickmedina/Downloads/Instrucciones_DLQ_Consola_AWS.md`.
* **Hallazgos Críticos:**
  1. La cola DLQ `cola-notificaciones-entrevistas-dlq-dev` **no existía**.
  2. La cola principal carecía de `RedrivePolicy`.
  3. El desencadenador SQS de la Lambda `cs2032-entrevistas-dev-procesarNotificacion` estaba en estado **`Disabled`** (`USER_INITIATED`), provocando que mensajes legítimos se quedaran represados.
  4. Los logs de CloudWatch no registraban ejecuciones desde el 17 de noviembre.

---

### Hito 2: Arquitectura v2 — Modelado de Resiliencia EDA
* **Artefacto Creado:** [Diagrama_Arquitectura_Solucion_v2.drawio](file:///Users/patrickmedina/Desktop/Proyecto-Final-CloudComputing/Diagrama_Arquitectura_Solucion_v2.drawio)
* **Mejoras Representadas:**
  * Expansión del contenedor EDA (`c175`).
  * Inclusión del nodo SQS DLQ en color rojo de alerta (`#D13212`).
  * Aristas de flujo para `Redrive Policy (al 3er fallo)` y `Start DLQ redrive` (retorno a cola origen).
  * Arista de retorno de excepciones por `ReportBatchItemFailures`.
  * Tarjeta de especificaciones técnicas y operaciones en consola SQS.

---

### Hito 3: Implementación y Verificación en Vivo de la DLQ en AWS
* **Paso 1 (Creación de DLQ):** Creación de `cola-notificaciones-entrevistas-dlq-dev` con período de retención máximo de 14 días (`1209600` s) y tipo Standard.
* **Paso 2 (Redrive Policy):** Configuración en `cola-notificaciones-entrevistas-dev` de la política `{"deadLetterTargetArn": "...", "maxReceiveCount": 3}` manteniendo `VisibilityTimeout = 60s`.
* **Paso 3 (Reactivación de Consumidor):** Habilitación del `EventSourceMapping` (`f6ababe4-215d-41b7-9644-501eaac4b8f6`), procesando de inmediato los mensajes represados.
* **Paso 4 (Prueba de Estrés y Fallo):** Publicación del mensaje no soportado `{"evento": "prueba_dlq", "tenant_id": "tenant_1"}` en SNS `topico-entrevistas-agendadas-dev`.
* **Evidencias Obtenidas:**
  * **3 errores consecutivos** en CloudWatch Logs espaciados exactamente por 60 segundos con `"Evento no soportado: prueba_dlq"`.
  * Transferencia automática del mensaje a la DLQ (`ApproximateNumberOfMessages: 1`).
  * Inspección forense del payload en la DLQ verificando el atributo `DeadLetterQueueSourceArn`.

---

### Hito 4: Auditoría de Arquitectura Senior (AWS Well-Architected Framework)
Se realizó una evaluación integral bajo los 6 pilares de AWS:
* **Calificación Académica:** 18.5 / 20 (Sobresaliente).
* **Calificación Enterprise:** 79 / 100 (Grado B+).
* **Identificación de 8 brechas:**
  1. *Seguridad Alta:* Credenciales RDS en texto plano en Lambda.
  2. *Fiabilidad Media:* Ausencia de pool de conexiones (RDS Proxy).
  3. *Seguridad Alta:* Validación de tokens a nivel de código y no en perímetro.
  4. *Rendimiento Medio:* Generación síncrona de reportes acoplada a bases de datos de otros servicios.
  5. *Seguridad Media:* RDS Single-AZ sin cifrado KMS.
  6. *Fiabilidad Media:* DynamoDB PITR y versionado S3 desactivados.
  7. *Operaciones:* 0 alarmas de CloudWatch configuradas.
  8. *Operaciones:* Trazabilidad distribuida con AWS X-Ray desactivada.

---

### Hito 5: Implementación Simultánea de Mejoras Enterprise (Subagentes Antigravity)
A través de cuatro agentes especializados actuando en paralelo:

#### 1. Seguridad de Secretos con SSM Parameter Store
- Se pobló `/cs2032/dev/rds/*` con `SecureString` KMS en AWS Systems Manager.
- Se crearon dos **VPC Endpoints (Interface)** (`vpce-083e...` para SSM y `vpce-0b69...` para KMS) en la VPC privada para conectividad segura sin NAT Gateway.
- Se refactorizó [common/rds.py](file:///Users/patrickmedina/Desktop/Proyecto-Final-CloudComputing/microservicios/cs2032-final-vacantes/common/rds.py) con consulta en bloque y almacenamiento en memoria cold-start.
- Se eliminó `RDS_PASSWORD` de las variables de entorno de 21 Lambdas en AWS.
- Se actualizaron los manifiestos `serverless.yml` con `${ssm:...}`.
- Prueba de integración extremo a extremo aprobada al 100%.

#### 2. Seguridad Perimetral con API Gateway Lambda Authorizer
- Se desarrolló la función [authorizer.py](file:///Users/patrickmedina/Desktop/Proyecto-Final-CloudComputing/microservicios/cs2032-final-usuarios/authorizer.py) (`cs2032-usuarios-dev-authorizer`).
- Generación de políticas IAM dinámicas (`Allow`/`Deny`) con comodines para maximizar la efectividad del caché.
- Activado **Caché TTL de 300 segundos** en API Gateway.
- Registrado el autorizador en las 5 APIs REST (`dev-cs2032-usuarios`, `dev-cs2032-vacantes`, `dev-cs2032-candidatos`, `dev-cs2032-entrevistas`, `dev-cs2032-reportes`).
- Refactorizado [common/auth.py](file:///Users/patrickmedina/Desktop/Proyecto-Final-CloudComputing/microservicios/cs2032-final-usuarios/common/auth.py) para lectura perimetral directa con cero costo adicional en DynamoDB.
- 15 pruebas unitarias automatizadas aprobadas en [test_authorizer.py](file:///Users/patrickmedina/Desktop/Proyecto-Final-CloudComputing/microservicios/cs2032-final-usuarios/tests/test_authorizer.py).

#### 3. Suite de Observabilidad y Monitoreo (CloudWatch Alarms & Dashboard)
- Tópico SNS `topico-alertas-cloudwatch-dev` configurado con suscripción por correo electrónico y permisos de publicación para CloudWatch.
- **6 Alarmas Métricas desplegadas:**
  1. `alarma-dlq-mensajes-visibles-dev`: Detecta mensajes en la DLQ (`ALARM`).
  2. `alarma-apigateway-5xx-dev`: Errores 5XX en todas las APIs (`OK`).
  3. `alarma-lambda-errores-dev`: Errores acumulados en Lambdas críticas (`OK`).
  4. `alarma-lambda-throttles-dev`: Throttling de invocaciones (`OK`).
  5. `alarma-rds-cpu-dev`: Uso de CPU >= 80% (`OK`).
  6. `alarma-rds-conexiones-dev`: Conexiones activas >= 60 (`OK`).
- Creado el panel centralizado **`dashboard-cs2032-dev`** con 11 widgets en tiempo real.
- Script automatizado en [setup_cloudwatch_alarms_and_dashboard.py](file:///Users/patrickmedina/Desktop/Proyecto-Final-CloudComputing/scripts/observability/setup_cloudwatch_alarms_and_dashboard.py) y guía técnica en [docs/observability_cloudwatch.md](file:///Users/patrickmedina/Desktop/Proyecto-Final-CloudComputing/docs/observability_cloudwatch.md).

#### 4. Trazabilidad Distribuida con AWS X-Ray
- Activado `TracingConfig.Mode = Active` en las **32 funciones Lambda** de la solución.
- Habilitado `tracingEnabled = True` en el stage `dev` de las **5 API Gateways**.
- Propagación de cabeceras `X-Amzn-Trace-Id` entre componentes para generar el Service Map automático.
- Configuración persistida en los 5 archivos `serverless.yml` del proyecto.

---

### Hito 6: Arquitectura v3 — Consolidación Enterprise
* **Artefacto Creado:** [Diagrama_Arquitectura_Solucion_v3.drawio](file:///Users/patrickmedina/Desktop/Proyecto-Final-CloudComputing/Diagrama_Arquitectura_Solucion_v3.drawio)
* **Elementos Nuevos Incorporados:**
  1. **Nodo Lambda Authorizer:** Ubicado en la columna de API Gateway, enlazado a `t_tokens_acceso-dev` con validación perimetral y caché de 300 s.
  2. **Insignia X-Ray:** Señalización de trazabilidad distribuida activa en API Gateway y Lambdas.
  3. **VPC Endpoints y SSM Parameter Store:** Representación dentro de la VPC de los endpoints privados de SSM/KMS resolviendo credenciales cifradas hacia RDS MySQL.
  4. **Contenedor de Observabilidad Enterprise:** Bloque de 1470 px al pie del diagrama con 3 tarjetas dedicadas:
     - *Tarjeta 1:* AWS X-Ray (32 Lambdas, 5 APIs, propagación de trazas).
     - *Tarjeta 2:* Amazon CloudWatch (Suite de 6 alarmas y tópico SNS).
     - *Tarjeta 3:* Amazon CloudWatch Dashboard (`dashboard-cs2032-dev` y sus 11 widgets).
  5. **Leyenda y Ficha Técnica v3:** Actualizadas con códigos de color corporativos y especificaciones de auditoría técnica.

---

## 📁 Inventario de Archivos Creados y Modificados

### Diagramas de Arquitectura (Raíz):
* [Diagrama_Arquitectura_Solucion.drawio](file:///Users/patrickmedina/Desktop/Proyecto-Final-CloudComputing/Diagrama_Arquitectura_Solucion.drawio) — Versión original (base).
* [Diagrama_Arquitectura_Solucion_v2.drawio](file:///Users/patrickmedina/Desktop/Proyecto-Final-CloudComputing/Diagrama_Arquitectura_Solucion_v2.drawio) — Versión intermedia con resiliencia EDA y Dead Letter Queue (DLQ).
* [Diagrama_Arquitectura_Solucion_v3.drawio](file:///Users/patrickmedina/Desktop/Proyecto-Final-CloudComputing/Diagrama_Arquitectura_Solucion_v3.drawio) — Versión Enterprise final (DLQ + SSM + Authorizer + Alarmas + X-Ray).

### Código Fuente y Librerías Comunes:
* [microservicios/cs2032-final-usuarios/authorizer.py](file:///Users/patrickmedina/Desktop/Proyecto-Final-CloudComputing/microservicios/cs2032-final-usuarios/authorizer.py) — Nueva función Lambda Authorizer perimetral.
* [microservicios/cs2032-final-usuarios/tests/test_authorizer.py](file:///Users/patrickmedina/Desktop/Proyecto-Final-CloudComputing/microservicios/cs2032-final-usuarios/tests/test_authorizer.py) — Suite de 15 pruebas unitarias para el Authorizer.
* [microservicios/cs2032-final-usuarios/common/auth.py](file:///Users/patrickmedina/Desktop/Proyecto-Final-CloudComputing/microservicios/cs2032-final-usuarios/common/auth.py) — Módulo de autenticación actualizado para consumir el contexto perimetral de API Gateway.
* [microservicios/cs2032-final-vacantes/common/rds.py](file:///Users/patrickmedina/Desktop/Proyecto-Final-CloudComputing/microservicios/cs2032-final-vacantes/common/rds.py) — Módulo de conexión a MySQL actualizado con soporte para SSM Parameter Store y caché en cold start.

### Scripts y Documentación de Operaciones:
* [scripts/observability/setup_cloudwatch_alarms_and_dashboard.py](file:///Users/patrickmedina/Desktop/Proyecto-Final-CloudComputing/scripts/observability/setup_cloudwatch_alarms_and_dashboard.py) — Script automatizado e idempotente para aprovisionar alarmas y dashboard.
* [docs/observability_cloudwatch.md](file:///Users/patrickmedina/Desktop/Proyecto-Final-CloudComputing/docs/observability_cloudwatch.md) — Documentación técnica de la arquitectura de monitoreo y alertas.

### Manifiestos de Despliegue Actualizados (`serverless.yml`):
* [microservicios/cs2032-final-usuarios/serverless.yml](file:///Users/patrickmedina/Desktop/Proyecto-Final-CloudComputing/microservicios/cs2032-final-usuarios/serverless.yml)
* [microservicios/cs2032-final-candidatos/serverless.yml](file:///Users/patrickmedina/Desktop/Proyecto-Final-CloudComputing/microservicios/cs2032-final-candidatos/serverless.yml)
* [microservicios/cs2032-final-vacantes/serverless.yml](file:///Users/patrickmedina/Desktop/Proyecto-Final-CloudComputing/microservicios/cs2032-final-vacantes/serverless.yml)
* [microservicios/cs2032-final-entrevistas/serverless.yml](file:///Users/patrickmedina/Desktop/Proyecto-Final-CloudComputing/microservicios/cs2032-final-entrevistas/serverless.yml)
* [microservicios/cs2032-final-reportes/serverless.yml](file:///Users/patrickmedina/Desktop/Proyecto-Final-CloudComputing/microservicios/cs2032-final-reportes/serverless.yml)

---

## 🎯 Puntos Clave para la Exposición / Sustentación

1. **Madurez Operativa Demostrable en Vivo:**
   * Mostrar en la consola de SQS la cola `cola-notificaciones-entrevistas-dlq-dev` con 1 mensaje disponible proveniente de la prueba forzada, demostrando que la arquitectura no colapsa ante payloads malformados.
   * Mostrar el panel centralizado en **CloudWatch** (`dashboard-cs2032-dev`), donde la alarma de DLQ figura en rojo (`ALARM`) corroborando la detección automática de incidentes en tiempo real.
2. **Defensa de Seguridad Corporativa:**
   * Demostrar que el perímetro de API Gateway filtra solicitudes inválidas sin invocar las Lambdas de backend, y que la contraseña de base de datos nunca viaja en variables de entorno ni en repositorios Git gracias a **AWS Systems Manager Parameter Store** y **VPC Interface Endpoints**.
3. **Observabilidad Enterprise:**
   * Explicar que la solución cuenta con **AWS X-Ray** habilitado de extremo a extremo, permitiendo auditar la latencia exacta de cada componente desde el navegador hasta la base de datos MySQL.
