# Runbook de despliegue — CRM de Empleabilidad (CS2032) en AWS Learner Lab nuevo

**Cuenta destino:** `452254767800` · **Región:** `us-east-1` · **Stage:** `dev` · **Rol:** `LabRole` (no se pueden crear roles IAM).
**Carpeta de scripts:** `despliegue/` (todo se ejecuta desde la raíz del repo `~/Desktop/Proyecto-Final-CloudComputing`).
**Fecha de preparación:** 2026-11-24.

## Requisitos locales (ya verificados en esta laptop)
Serverless Framework 3.40, Node 26 / npm, Python 3.11, AWS CLI 2, Docker (no es obligatorio: `dockerizePip: false`). `shellcheck` y el cliente `mysql` **no** están instalados (el schema se carga con `pymysql`).

## Antes de empezar
1. Reset de la cuenta hecho y revisado (ver `RESET_CUENTA.md`).
2. Credenciales vigentes del Learner Lab en `~/.aws/credentials` (duran unas horas). Comprobar: `aws sts get-caller-identity` → cuenta `452254767800`.
3. Si renuevas credenciales a mitad de camino, vuelve a lanzar el script en el que estabas: todos son idempotentes.

## Orden de ejecución

| # | Script | Qué hace | Tiempo aprox. |
|---|---|---|---|
| 1 | `bash despliegue/01_infra_base.sh` | SGs, RDS MySQL 8 (`cs2032-vacantes-dev`), parámetros SSM `/cs2032/dev/rds/*`, endpoints SSM y KMS, `.env.local`, aplica `schema.sql` (RDS abierto solo a tu IP durante la carga) | 10–15 min |
| 2 | `bash despliegue/02_deploy_servicios.sh` | `serverless deploy` en orden usuarios → candidatos → vacantes → entrevistas → reportes; guarda `API_*` en `.env.local` | 10–20 min |
| 3 | `bash despliegue/03_datos.sh 1000` | Admins semilla, candidatos, vacantes/postulaciones, entrevistas, reportes y migración a RDS (usar `10000` para el requisito de 30 000 por tabla) | 5 min (1000) / 1 h (10000) |
| 4 | `ALERT_EMAIL=tu@correo bash despliegue/04_observabilidad.sh` | Tópico SNS, 6 alarmas y dashboard `dashboard-cs2032-dev`. **Confirmar la suscripción por correo** | 1 min |
| 5 | `bash despliegue/05_frontend.sh` | Sustituye las URLs antiguas de las 5 APIs y publica en Amplify | 3 min |
| 6 | `bash despliegue/06_smoke_test.sh` | Login, 5 APIs con/sin token, aislamiento multi-tenant, colas SQS/DLQ | 1 min |

Utilidades:
- `bash despliegue/02_rds_acceso.sh on|off`: abre/cierra RDS a tu IP (solo para operaciones manuales).
- `bash despliegue/99_pausar.sh`: ahorra crédito (stop RDS + borra endpoints de interfaz). Para volver: `aws rds start-db-instance --db-instance-identifier cs2032-vacantes-dev` y `01_infra_base.sh` (recrea endpoints). RDS se reinicia solo a los 7 días.
- `bash despliegue/99_destruir.sh`: borra todo el proyecto (pide teclear el ID de cuenta).

## Qué cambió respecto a la cuenta anterior (816193343783)
| Antes (manual) | Ahora |
|---|---|
| DLQ creada a mano | En `entrevistas/serverless.yml` (`ColaNotificacionesEntrevistasDLQ`, `maxReceiveCount: 3`, retención 14 d) |
| `RDS_PASSWORD` en variables de entorno al redesplegar | Eliminada de los 3 `serverless.yml`; la contraseña se lee de SSM en ejecución (`common/rds.py`). Si SSM falla ya no se cachea el fallo |
| RDS, SSM, endpoints SSM/KMS manuales | `01_infra_base.sh` |
| Admin inicial inexistente en el código | `seed_admin.py` (admin@tenant{1,2,3}.example) |
| Alarmas con cuenta/ARN fijos | `setup_cloudwatch_alarms_and_dashboard.py` toma cuenta por STS y correo por `ALERT_EMAIL` |
| URLs de API fijas en el frontend/README/Postman | `05_frontend.sh` las reemplaza |

## Secretos
- Todo secreto vive solo en `despliegue/.env.local` (permisos 600, ignorado por git): `DB_PASSWORD`, `ADMIN_PASSWORD`, y las URLs `API_*`.
- **No** commitear `.env.local`, `.venv/`, ni `*.pem`. Rotar la contraseña de MySQL mostrada en `LINEA_DE_TIEMPO_Y_MEJORAS_ARQUITECTURA.md` (línea 56; era de la cuenta anterior) y reemplazarla por `<password>`.

## Costes a vigilar (Learner Lab)
- Endpoints de interfaz (SNS, SSM, KMS): cobran por hora y por AZ.
- RDS db.t3.micro encendida 24 h.
- Los 3 endpoints de interfaz y RDS son lo primero a apagar al terminar la sesión (`99_pausar.sh`).

## Problemas conocidos / cómo resolverlos
- `ExpiredToken`: renovar credenciales y relanzar el mismo script.
- `serverless deploy` falla en `${ssm:...}`: no se corrió `01_infra_base.sh` o el parámetro no existe.
- Lambda en VPC con timeout al leer SSM: el endpoint SSM aún no está `available` o el SG no permite 443 interno.
- `DELETE_FAILED` por SG al destruir: esperar a que las Lambdas liberen sus ENIs y reintentar.
- Smoke test falla en DLQ: confirmar que `entrevistas` se desplegó con el yml actualizado.

## Estado de validación (honesto)
Los scripts se escribieron y validaron con `bash -n` / `py_compile`. **Ninguno se ha ejecutado contra AWS todavía.** La primera ejecución real es la prueba; cualquier fallo debe documentarse en `despliegue/BITACORA.md`.
