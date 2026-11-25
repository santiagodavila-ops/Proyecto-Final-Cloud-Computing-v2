# Suite de Monitoreo y Observabilidad CloudWatch - Entorno DEV

## 1. Resumen Ejecutivo
Se ha implementado el stack completo de observabilidad en AWS CloudWatch para la plataforma serverless de reclutamiento (CS2032), resolviendo la deficiencia de observabilidad previa (*"Cero Alarmas de CloudWatch Configuradas"*).

La solución comprende:
- **Tópico SNS Centralizado:** `arn:aws:sns:us-east-1:816193343783:topico-alertas-cloudwatch-dev` con permisos de publicación para `cloudwatch.amazonaws.com` y suscripción por correo electrónico activa.
- **6 Alarmas de Métricas CloudWatch:** Cobertura de extremo a extremo (SQS DLQ, API Gateway, AWS Lambda, y Amazon RDS).
- **Dashboard Centralizado:** `dashboard-cs2032-dev` con vista integral de la plataforma en tiempo real.

---

## 2. Alarmas de Métricas Configuradas

| Alarma | Namespace / Métrica | Dimensión / Expresión Math | Umbral (Threshold) | Período / Eval | Acción SNS | Estado Actual |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`alarma-dlq-mensajes-visibles-dev`** | `AWS/SQS`<br>`ApproximateNumberOfMessagesVisible` | `QueueName: cola-notificaciones-entrevistas-dlq-dev` | `>= 1` mensaje | 60 seg / 1 eval | `topico-alertas-cloudwatch-dev` | **ALARM** (Mensaje detectado en DLQ) |
| **`alarma-apigateway-5xx-dev`** | `AWS/ApiGateway`<br>`5XXError` | Metric Math:<br>`FILL(m1,0)+FILL(m2,0)+FILL(m3,0)+FILL(m4,0)+FILL(m5,0)`<br>sobre las 5 APIs REST | `>= 1` error 5XX | 300 seg / 1 eval | `topico-alertas-cloudwatch-dev` | **OK** |
| **`alarma-lambda-errores-dev`** | `AWS/Lambda`<br>`Errors` | Metric Math:<br>Suma de errores con `FILL(lX,0)` sobre las 8 funciones críticas | `>= 2` errores | 300 seg / 1 eval | `topico-alertas-cloudwatch-dev` | **OK** |
| **`alarma-lambda-throttles-dev`** | `AWS/Lambda`<br>`Throttles` | Métricas de estrangulamiento de concurrencia | `>= 1` throttle | 300 seg / 1 eval | `topico-alertas-cloudwatch-dev` | **OK** |
| **`alarma-rds-cpu-dev`** | `AWS/RDS`<br>`CPUUtilization` | `DBInstanceIdentifier: cs2032-vacantes-dev` | `>= 80%` CPU | 300 seg / 1 eval | `topico-alertas-cloudwatch-dev` | **OK** |
| **`alarma-rds-conexiones-dev`** | `AWS/RDS`<br>`DatabaseConnections` | `DBInstanceIdentifier: cs2032-vacantes-dev` | `>= 60` conexiones (límite db.t3.micro: ~80) | 300 seg / 1 eval | `topico-alertas-cloudwatch-dev` | **OK** |

---

## 3. Dashboard Centralizado: `dashboard-cs2032-dev`

El dashboard incluye 11 widgets organizados modularmente:
1. **Banner de Estado:** Información de entorno, región, cuenta y enlaces.
2. **Widget de Alarmas:** Vista en vivo de las 6 alarmas configuradas.
3. **SQS DLQ Messages:** Monitoreo en tiempo real de mensajes fallidos en la cola DLQ.
4. **SQS Main Queue Traffic & Depth:** Mensajes entrantes, salientes, en vuelo y procesados en la cola de notificaciones.
5. **API Gateway - 4XX & 5XX Error Rates:** Agregación de fallas HTTP para las 5 APIs (Vacantes, Candidatos, Entrevistas, Usuarios, Reportes).
6. **API Gateway - Throughput & Latencia:** Volumen de requests y tiempos de respuesta (Latency e IntegrationLatency).
7. **AWS Lambda - Invocaciones:** Tasa de ejecución por microservicio crítico.
8. **AWS Lambda - Errores y Throttles:** Concurrencia excedida y fallos de ejecución.
9. **AWS Lambda - Duración:** Percentiles de latencia (p50, p95, Average).
10. **RDS - CPU Utilization:** Consumo de procesador en la base de datos MySQL con línea de umbral de 80%.
11. **RDS - Conexiones y Memoria:** Conexiones concurrentes activas y memoria disponible (FreeableMemory).

---

## 4. Script de Automatización
El script de aprovisionamiento idempotente se encuentra en:
- `scripts/observability/setup_cloudwatch_alarms_and_dashboard.py`
