# CRM de Empleabilidad — Arquitectura Cloud Enterprise Multi-Tenant (CS2032)

Solución SaaS Serverless y orientada a eventos (EDA) desarrollada en **Amazon Web Services (AWS)** para la gestión integral de procesos de selección y empleabilidad empresarial. Diseñada bajo los principios del **AWS Well-Architected Framework**, incorporando aislamiento multi-tenant estricto, seguridad perimetral, resiliencia desacoplada y observabilidad distribuida.

Proyecto desarrollado para el curso **CS2032 Cloud Computing** — Universidad de Ingeniería y Tecnología (UTEC).

---

## 🏛️ Arquitectura de la Solución (v3 Enterprise)

La arquitectura implementa un modelo de microservicios desacoplados que combinan cómputo serverless, persistencia políglota y mensajería asíncrona:

```
                                  [ Usuario / Frontend SPA (Amplify) ]
                                                    │
                                                    ▼
                                  [ Amazon API Gateway (5 REST APIs) ]
                                                    │
                                     (Token Authorizer Lambda con TTL 300s)
                                                    │
             ┌──────────────────────┬───────────────┴──────────────┬──────────────────────┐
             ▼                      ▼                              ▼                      ▼
    [ cs2032-usuarios ]   [ cs2032-candidatos ]          [ cs2032-vacantes ]   [ cs2032-reportes ]
      (Amazon DynamoDB)     (DynamoDB + S3 CVs)         (Amazon RDS MySQL 8)     (DynamoDB + RDS)
                                                                   │
                                                                   ▼
                                                       [ cs2032-entrevistas ]
                                                          (Amazon DynamoDB)
                                                                   │
                                                                   ▼
                                                         [ Amazon SNS Topic ]
                                                                   │
                                                                   ▼
                                                         [ Amazon SQS Queue ]
                                                                   │ (maxReceiveCount: 3)
                                                                   ├──────────────► [ SQS Dead Letter Queue (DLQ) ]
                                                                   ▼
                                                   [ Lambda Worker Procesador ]
```

El diagrama editable completo se encuentra en [`diagramas/Diagrama_Arquitectura_Solucion_v3.drawio`](diagramas/Diagrama_Arquitectura_Solucion_v3.drawio).

---

## 🧩 Componentes y Microservicios

| Microservicio | Responsabilidad | Persistencia | Patrones Clave |
|---|---|---|---|
| **`cs2032-final-usuarios`** | Registro, inicio de sesión y emisión de tokens con PBKDF2/SHA-256. | Amazon DynamoDB | **API Gateway Lambda Authorizer** perimetral con caché de 300 s. |
| **`cs2032-final-candidatos`** | Perfiles de postulantes y generación de Presigned URLs para CVs. | Amazon DynamoDB + S3 | Carga directa segura a S3 sin pasar bytes por Lambda. |
| **`cs2032-final-vacantes`** | Publicación de vacantes y registro de postulaciones. | Amazon RDS MySQL 8.0 | Aislamiento multi-tenant mediante esquemas dedicados por tenant. |
| **`cs2032-final-entrevistas`** | Agendamiento y ciclo de entrevistas técnicas/RRHH. | Amazon DynamoDB + RDS | **EDA** vía SNS + SQS con **DLQ (Dead Letter Queue)** y reintentos. |
| **`cs2032-final-reportes`** | Agregaciones analíticas y métricas de contratación. | Amazon DynamoDB + RDS | Consultas de lectura agregadas con soporte multi-tenant. |
| **`cs2032-final-frontend`** | Interfaz web en Vue 3 con Vite y visor Swagger/OpenAPI. | AWS Amplify Hosting | Despliegue estático automatizado mediante archivo ZIP. |

---

## 🛡️ Alineación con el AWS Well-Architected Framework

### 1. Seguridad (Security)
- **Zero Hardcoded Secrets:** Ninguna función Lambda almacena contraseñas en variables de entorno. La contraseña de base de datos se almacena cifrada en **AWS Systems Manager Parameter Store** (`SecureString` KMS) y se recupera en tiempo de ejecución con caché en memoria cold-start.
- **Defensa en Profundidad de Red:** La base de datos MySQL reside en una VPC privada (`PubliclyAccessible=false`). El grupo de seguridad `cs2032-lambda-rds` autoriza tráfico exclusivamente desde sí mismo. El acceso administrativo temporal (`cs2032-rds-admin`) se revoca de inmediato al concluir las migraciones.
- **Autenticación Perimetral:** En las rutas protegidas que usan el autorizador, API Gateway valida el token antes de invocar la función de negocio. El alta de usuarios comprueba el token y el rol de administrador en su propia función.

### 2. Fiabilidad y Resiliencia (Reliability)
- **Tolerancia a Fallos y DLQ:** El flujo de notificaciones asíncronas implementa una cola de mensajes no procesables (`cola-notificaciones-entrevistas-dlq-dev`) con retención de 14 días y `maxReceiveCount: 3`.
- **Procesamiento Parcial:** El consumidor Lambda utiliza `ReportBatchItemFailures` para reenviar únicamente los mensajes individuales defectuosos sin descartar mensajes válidos del lote.

### 3. Rendimiento y Eficiencia (Performance Efficiency)
- **Conectividad Privada sin NAT:** Las Lambdas en VPC acceden a servicios AWS mediante **VPC Endpoints** privados (DynamoDB Gateway, SSM Interface, KMS Interface, SNS Interface), reduciendo la latencia y eliminando la necesidad de NAT Gateways costosos.
- **Gestión de Conexiones:** Control estricto de conexiones relacionales mediante bloques `finally: conn.close()`.

### 4. Excelencia Operativa (Operational Excellence)
- **Trazabilidad Distribuida:** **AWS X-Ray** habilitado en modo activo (`Mode: Active`) en las 32 funciones Lambda y en los 5 stages de API Gateway, generando el mapa visual de dependencias y análisis p95 de latencias.
- **Alarmas y Dashboard:** Suite de 6 alarmas CloudWatch configuradas para fallos de Lambdas, throttles, errores 5XX de API Gateway, mensajes en DLQ, consumo de CPU y conexiones de base de datos, conectadas a un tópico SNS de alertas y consolidadas en `dashboard-cs2032-dev`.

### 5. Optimización de Costes (Cost Optimization)
- **Operación Serverless por Demanda:** Cómputo facturado por milisegundo y tablas DynamoDB en modo `PAY_PER_REQUEST`.
- **Pausa Programada:** Script de utilidad `despliegue/99_pausar.sh` para suspender la instancia RDS y retirar endpoints de interfaz en periodos de inactividad.

---

## 🚀 Despliegue Automatizado (Runbook)

Para desplegar la solución completa en una cuenta limpia de AWS:

### Requisitos Previos
- AWS CLI v2 configurado con permisos de administrador.
- Node.js compatible con Vite (`^20.19.0 || >=22.12.0`) y Serverless Framework v3 (`npm install -g serverless@3`).
- Python 3.11 y virtualenv.

### Secuencia de Ejecución
```bash
# 1. Aprovisionar infraestructura base (VPC Endpoints, RDS MySQL, Security Groups, SSM)
bash despliegue/01_infra_base.sh

# 2. Desplegar los 5 microservicios Serverless
bash despliegue/02_deploy_servicios.sh

# 3. Cargar los datos en una cuenta limpia e inicializar los esquemas por tenant
bash despliegue/03_datos.sh 10000

# 4. Configurar observabilidad, alarmas y dashboard centralizado
ALERT_EMAIL=tu_correo@dominio.com bash despliegue/04_observabilidad.sh

# 5. Publicar frontend en AWS Amplify Hosting
bash despliegue/05_frontend.sh

# 6. Ejecutar suite de pruebas de humo E2E
bash despliegue/06_smoke_test.sh
```

---

## Datos por microservicio

En el recuento del 25 de noviembre de 2026, el entorno `dev` reunió **150 000 registros** en tres empresas.

| Microservicio | tenant_1 | tenant_2 | tenant_3 | Total |
|---|---:|---:|---:|---:|
| Usuarios | 10 000 | 10 000 | 10 000 | 30 000 |
| Candidatos | 10 000 | 10 000 | 10 000 | 30 000 |
| Vacantes y postulaciones | 10 000 | 10 000 | 10 000 | 30 000 |
| Entrevistas | 10 000 | 10 000 | 10 000 | 30 000 |
| Reportes | 10 000 | 10 000 | 10 000 | 30 000 |

Cada esquema de RDS contiene 5 000 vacantes y 5 000 postulaciones. El total de Usuarios corresponde a las cuentas de `t_usuarios-dev`. Los tokens de sesión se contabilizan aparte.

Para una prueba con una base vacía se puede usar `bash despliegue/03_datos.sh 1000`. Repetir la carga sobre datos existentes puede añadir registros.

---

## 🧪 Pruebas de Humo y Validación

El script `despliegue/06_smoke_test.sh` evalúa automáticamente:
1. Autenticación de administradores de múltiples tenants (`tenant1`, `tenant2`).
2. Acceso autorizado (`HTTP 200`) a los 5 microservicios con Bearer token.
3. Rechazo perimetral (`HTTP 401`) ante peticiones no autenticadas.
4. Aislamiento cross-tenant estricto (`HTTP 404` ante intentos de acceso a recursos de otro tenant).
5. Existencia y operatividad de colas SQS principales y DLQ.

---

## 👥 Equipo de Desarrollo (Grupo 1)

- **Patrick Medina** — Arquitectura Cloud, Microservicio de Vacantes y Despliegue Automatizado.
- **Sandra** — Microservicio de Usuarios y Autenticación.
- **Santiago** — Microservicio de Candidatos.
- **Sanders** — Microservicio de Entrevistas y Seguimiento.
