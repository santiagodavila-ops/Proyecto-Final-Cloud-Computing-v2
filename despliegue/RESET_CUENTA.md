# Plan de reset total de la cuenta AWS Learner Lab (para el agente ejecutor)

**Cuenta:** `452254767800` · **Región:** `us-east-1` · **Autorizado por:** Patrick Medina (reset COMPLETO de la cuenta, decisión del usuario el 2026-11-23).
**Objetivo:** dejar la cuenta limpia para desplegar el proyecto `cs2032` con `RUNBOOK.md`.
**Revisor:** Claude (rol Solutions Architect AWS Senior) revisará el resultado al terminar. Lee `REVISION_ARQUITECTO.md`: debes dejar la evidencia que pide.

> Este reset es **irreversible**. Antes de empezar, el ejecutor debe confirmar `aws sts get-caller-identity` → `Account = 452254767800`. Si es otra cuenta, **detenerse**.

## 0. Reglas

1. **No borrar lo gestionado por el Learner Lab.** Se conserva:
   - El stack CloudFormation `c220111a5553174l17447627t1w452254767800` y todos sus recursos. Antes de nada, ejecuta `aws cloudformation list-stack-resources --stack-name c220111a5553174l17447627t1w452254767800` y guarda la lista en `evidencia_reset/00_stack_lab.txt`.
   - Rol `LabRole` (y `voclabs`, y cualquier rol/instance profile del Lab). No se pueden recrear.
   - La VPC por defecto `vpc-0242679619378340f`, sus subnets, route table principal, internet gateway y el SG `default`.
   - Los roles de servicio (`/aws-service-role/`).
2. **Antes de borrar, descubre.** Estado al 2026-11-23 (puede haber cambiado; vuelve a listar):

| Servicio | Recursos conocidos |
|---|---|
| CloudFormation (14 + 1 del Lab) | `api-alumnos-rds-{dev,test,prod}`, `api-vision-artificial-dev`, `api-web-scraping-sismos-dev`, `api-web-scraping-dev`, `api-pelicula-dev`, `api-comentario-{dev,test,prod}`, `api-s3-{dev,test,prod}`, `api-alumnos-dev` (+ el stack del Lab a conservar) |
| Lambda (~50) | las de esos stacks + sueltas: `CrearAlumno*`, `ProcesarPedido`, `RegistrarPedido`, `CrearProducto`, `listarProductos`, `buscarProducto`, `eliminarProducto`, `modificarAlumno`, `buscar2`, `ListarAlumnos`, `BuscarAlumno`, `EliminarAlumno`, `CrearUsuario`, `LoginUsuario`, `ValidarTokenAcceso`, `RegistrarCanvas`, `CrearArchivo_UTEC`, `LeerMetadataArchivo`, `InsertarEventoSensorIoT`, `GenerarEventoSensorIoT`, `RedshiftOverwatch`, `RedshiftEventSubscription`, `MainMonitoringFunction`, `RoleCreationFunction`, `ModLabRole` |
| API Gateway (18) | `dev/test/prod-api-*`, `api-alumnos`, `api-productos`, `pedidos`, `api-usuarios` |
| DynamoDB (16) | `TablaSismosIGP`, `TablaWebScrapping`, `dev-t_comentarios`, `prod-t_comentarios`, `test-t_comentarios`, `dev-t_peliculas`, `t_alumnos`, `t_alumnos_canvas`, `t_alumnos_seguridad`, `t_archivos_UTEC`, `t_pedidos_procesados`, `t_productos`, `t_red_social`, `t_sensor_iot_FAB1`, `t_tokens_acceso`, `t_usuarios`, `tienda` |
| S3 (9) | `dev-/test-/prod-ingesta-comentarios-452254767800`, `images-pmr`, `mi-bucket-patrick-452254767800`, `mi-bucket-patrick2-452254767800`, `pmr-archivos`, `universidades-pmr`, `serverless-framework-deployments-us-east-1-119c2ccc-19b2` |
| RDS | `alumnos` (available) |
| EC2 | 3 instancias `running`, 1 EIP `eipalloc-0246165fa3e2b36b3`, SG `launch-wizard-1` |
| SQS | `ColaSensorIoTFAB1`, `sqs-pedidos`, `sqs-registrar-canvas`, `sqs-registrar-canvas-dlq` |
| SNS | `NuevoAlumno`, `RedshiftSNS`, `TemaNuevoArchivo`, `TemaSensorIoT` |
| SSM | `/rds_mysql_alumnos/*`, `/serverless-framework/deployment/s3-bucket` |
| Logs | ~50 log groups `/aws/lambda/*` |

3. **No borrar a ciegas por nombre.** Si un recurso está en el stack del Lab, se conserva aunque coincida con la lista de arriba (p. ej. `RoleCreationFunction`, `ModLabRole`, `MainMonitoringFunction` podrían ser del Lab: verifica con `list-stack-resources` y con los tags `aws:cloudformation:stack-name`).
4. **Registrar todo.** Cada paso escribe su salida en `despliegue/evidencia_reset/NN_<paso>.txt` (antes y después). Sin evidencia, el revisor lo marcará como no hecho.
5. Si el token expira (`ExpiredToken`), pedir al usuario que renueve `~/.aws/credentials` y continuar. No inventar credenciales.
6. Pausa de seguridad: **antes del paso 2**, mostrar al usuario el inventario real (paso 1) y esperar su "adelante" si aparece algo no listado en la tabla.

## 1. Inventario previo (solo lectura)

Guardar en `evidencia_reset/01_inventario_antes.txt`: stacks, lambdas, APIs, DynamoDB, S3 (con `--summarize` y estado de versionado), RDS (+ snapshots, clusters, subnet groups), EC2 (+ volúmenes, snapshots propios, AMIs propias, key pairs, EIPs, NAT, ENIs), ELB, ECR, Secrets Manager, EventBridge rules, Redshift, Glue, Kinesis, SQS, SNS, SSM, alarmas/dashboards, log groups, VPC endpoints, SGs, IAM (users/roles no de servicio).

## 2. Orden de borrado

Orden pensado para evitar dependencias (ENIs de Lambda-en-VPC y SGs son lo que más bloquea).

1. **Detener fuentes de coste vivas:** terminar las 3 EC2 (`terminate-instances`), esperar `terminated`; liberar EIP; borrar volúmenes `available` y snapshots/AMIs propias; eliminar key pairs creados por el usuario **excepto** `vockey`.
2. **RDS `alumnos`:** `modify-db-instance --no-deletion-protection` si aplica, luego `delete-db-instance --skip-final-snapshot --delete-automated-backups`; esperar `db-instance-deleted`. Borrar snapshots manuales y DB subnet groups no usados.
3. **Stacks CloudFormation** (todos menos el del Lab): para cada uno vaciar antes los buckets S3 que contenga (incluidas versiones y delete markers), luego `delete-stack` y `wait stack-delete-complete`. Si falla (`DELETE_FAILED`), leer `describe-stack-events`, resolver la causa (bucket no vacío, ENI, SG) y reintentar con `--retain-resources` solo como último recurso (documentarlo).
4. **Lambdas sueltas** (las que no eran de stacks y no son del Lab): `delete-function`. Luego event source mappings huérfanos.
5. **API Gateway REST** sueltas: `delete-rest-api` (límite de 1 borrado cada ~30 s por cuenta/región: reintentar con espera en `TooManyRequestsException`).
6. **DynamoDB:** `delete-table` en cada tabla restante (incluye `PITR` desactivado/backups on-demand: borrar con `delete-backup`).
7. **S3:** por cada bucket: vaciar (objetos + versiones + delete markers + multipart incompletos) y `delete-bucket`. Incluye `serverless-framework-deployments-...` (Serverless lo recrea).
8. **SQS** (borrar `sqs-registrar-canvas` y su DLQ), **SNS** (borrar suscripciones y tópicos), reglas EventBridge no del Lab, Secrets Manager, ECR, Kinesis, Glue, Redshift si existieran.
9. **SSM:** `delete-parameters` de `/rds_mysql_alumnos/*` y `/serverless-framework/*`.
10. **CloudWatch:** borrar alarmas, dashboards y los log groups `/aws/lambda/*` y `/aws/apigateway/*` que sobren (no los del Lab).
11. **Red:** borrar VPC endpoints no gestionados, ENIs `available` huérfanas, SGs distintos de `default` (`launch-wizard-1` y cualquier otro; reintentar: hasta ~10 min tras borrar Lambdas en VPC). **No tocar** la VPC por defecto ni sus subnets.
12. **IAM:** no hay que borrar nada (no se pueden crear/borrar roles en el Lab). Solo reportar users/roles no esperados.

## 3. Verificación final (criterio de "limpio")

Guardar `evidencia_reset/99_inventario_despues.txt` con los mismos comandos del paso 1. Debe cumplirse:

- [ ] `list-stacks` (estados vivos): solo el stack `c220111a…`.
- [ ] 0 Lambdas (salvo las del stack del Lab), 0 APIs REST, 0 tablas DynamoDB, 0 buckets S3, 0 RDS, 0 EC2 (running/stopped), 0 EIP, 0 NAT, 0 colas SQS, 0 tópicos SNS, 0 parámetros SSM, 0 alarmas, 0 dashboards.
- [ ] SGs: solo `default`. Endpoints VPC: 0 (o solo los del Lab).
- [ ] `aws iam get-role --role-name LabRole` sigue funcionando; el stack del Lab sigue `CREATE_COMPLETE`.
- [ ] Cost Explorer / `aws ce` no aplica en Learner Lab: en su lugar, anotar el saldo de créditos mostrado en la consola del Lab antes y después.

## 4. Entregable del ejecutor

- Script reproducible `despliegue/00_reset_cuenta.sh` (con `set -euo pipefail`, confirmación interactiva que exige teclear el ID de cuenta, `--dry-run` por defecto y `--ejecutar` para borrar de verdad), o bien el registro paso a paso de los comandos usados.
- Carpeta `despliegue/evidencia_reset/` con los `.txt`.
- Resumen: qué se borró, qué se conservó y por qué, incidentes (`DELETE_FAILED`, retenciones).

Cuando termine, avisar al usuario para que Claude haga la revisión arquitectónica.
