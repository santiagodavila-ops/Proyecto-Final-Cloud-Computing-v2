# Guía de revisión — Solutions Architect AWS Senior

Se aplica en dos momentos: (A) tras el reset de la cuenta, (B) tras el despliegue completo. Claude revisa con esta lista y emite un veredicto por sección (OK / OBSERVACIÓN / BLOQUEANTE) citando la evidencia.

## A. Reset de la cuenta (`RESET_CUENTA.md`)
- [ ] Cuenta confirmada `452254767800` antes de borrar (evidencia con `sts`).
- [ ] `evidencia_reset/01_inventario_antes.txt` y `99_inventario_despues.txt` existen y el diff es coherente.
- [ ] Stack del Lab, `LabRole`, VPC por defecto y SG `default` intactos.
- [ ] 0 recursos con coste residual: EC2, EIP, NAT, RDS, endpoints de interfaz, volúmenes, snapshots.
- [ ] Sin `--retain-resources` injustificados; incidentes documentados.
- [ ] El script de reset tiene `--dry-run` por defecto y confirmación explícita.

## B. Despliegue del proyecto
Pilares Well-Architected y puntos concretos a comprobar (con comandos en `despliegue/`):

**Seguridad**
- [ ] `aws lambda get-function-configuration` de las 31+ funciones: ninguna con `RDS_PASSWORD` en el entorno.
- [ ] SG `cs2032-lambda-rds`: ingreso solo desde sí mismo (3306/443). SG `cs2032-rds-admin`: sin reglas tras la carga. RDS `PubliclyAccessible=false`.
- [ ] `.env.local` con permisos 600 y fuera de git (`git check-ignore`). Ningún secreto en el repo ni en los `.md` (grep de la contraseña antigua y de `ADMIN_PASSWORD`).
- [ ] Authorizer en los 5 stages; sin token → 401 sin invocar la Lambda de negocio.
- [ ] RDS sin cifrado KMS y Single-AZ: hallazgo aceptado de Learner Lab (documentar, no bloquear).

**Fiabilidad**
- [ ] DLQ con `RedrivePolicy maxReceiveCount=3`, trigger SQS `Enabled`, `ReportBatchItemFailures`.
- [ ] Los scripts son idempotentes (relanzar `01` y `02` no rompe nada).
- [ ] Prueba de DLQ extremo a extremo (publicar evento inválido en SNS → mensaje en DLQ → alarma).

**Rendimiento**
- [ ] Lambdas en VPC alcanzan DynamoDB (gateway), SNS/SSM (interface) sin NAT; sin timeouts en cold start.
- [ ] Conexiones RDS: sin fugas (cierre en `finally`), alarma de conexiones razonable para db.t3.micro.

**Operaciones**
- [ ] 6 alarmas + dashboard creados; suscripción SNS confirmada; X-Ray activo (Lambdas y stages).
- [ ] `RUNBOOK.md` reproducible por otra persona: ejecutar en orden sin pasos ocultos.

**Costes**
- [ ] Inventario de recursos con coste por hora al terminar; `99_pausar.sh` probado.

**Calidad de scripts (revisión de código)**
- [ ] `set -euo pipefail`, manejo de `trap`, sin `eval`, sin secretos en `ps`/logs (la contraseña de RDS aparece como argumento de `aws rds create-db-instance`: aceptable en laptop personal, anotar).
- [ ] `03_datos.sh`: orden de dependencias; `schema.sql` troceado por `;`.
- [ ] `06_smoke_test.sh`: usa `/tmp/smoke_resp.json` fijo (no ejecutar en paralelo).
- [ ] `02_deploy_servicios.sh` escribe `API_*` sin `export` mientras `env_set` usa `export`: consistente al hacer `source`, pero revisar.

## Riesgos abiertos reportados por los agentes de construcción
1. Ningún script probado contra AWS (solo `bash -n`/`py_compile`).
2. Nombres fijos en el script de alarmas (`cs2032-vacantes-dev`, `dev-cs2032-*`): solo válidos para stage `dev`.
3. El smoke test asume `token_acceso` en la respuesta del login y que `GET /reportes` lo puede hacer el admin.
4. Si reportes/vacantes necesitaran SNS u otros endpoints adicionales, puede haber conflicto de DNS privado con los creados por otros stacks (verificar en el primer deploy).
5. `requirements`/`faker` requieren internet en la laptop.

## Plantilla de veredicto
| Sección | Veredicto | Evidencia | Acción |
|---|---|---|---|
| A. Reset | | | |
| B. Seguridad | | | |
| B. Fiabilidad | | | |
| B. Rendimiento | | | |
| B. Operaciones | | | |
| B. Costes | | | |
| **Global** | | | |
