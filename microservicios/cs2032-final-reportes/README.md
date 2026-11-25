# cs2032-reportes — Microservicio de Reportes

CRM de Empleabilidad Nacional — CS2032 (Grupo 1).

Métricas de contratación por tenant. Lee (solo lectura) las tablas de los otros
microservicios y guarda los resultados en su propia tabla `t_reportes-<stage>`.

## API desplegada (dev)

```
https://zeagrg9231.execute-api.us-east-1.amazonaws.com/dev
```

Todas las rutas requieren `Authorization: Bearer <token_acceso>` (login en
`https://hwi0abum32.execute-api.us-east-1.amazonaws.com/dev/usuarios/login`).

| Método | Ruta | Operación |
|---|---|---|
| POST | /reportes/generar | Recalcula y guarda el `resumen_general` del tenant |
| GET | /reportes | Listar reportes (`?prefijo=diario_2026-10`, `?cursor=`) |
| GET | /reportes/{tipo_reporte} | Consultar un reporte (ej. `resumen_general`) |
| PUT | /reportes/{tipo_reporte} | Editar `observaciones` |
| DELETE | /reportes/{tipo_reporte} | Eliminar reporte |

Tipos de reporte:
- `resumen_general`: calculado en vivo con `POST /reportes/generar`.
- `diario_<AAAA-MM-DD>_<area>`: métricas históricas diarias por área.

## Autenticación (login)

El token se obtiene en Usuarios, sin `tenant_id` (el tenant sale del usuario):

```bash
curl -X POST https://hwi0abum32.execute-api.us-east-1.amazonaws.com/dev/usuarios/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo.tenant_1@cs2032.test","password":"Demo-cs2032"}'
```

La respuesta trae `token_acceso`, `token_refresh`, `expira_acceso`, `expira_refresh`,
`tenant_id`, `usuario_id`, `rol` y el alias deprecado `token` (= `token_acceso`).
Cuando el acceso expira (`401`), `POST /usuarios/refresh` con `{"token_refresh"}`
devuelve un nuevo `token_acceso`.

## Ejemplos con curl

```bash
API=https://zeagrg9231.execute-api.us-east-1.amazonaws.com/dev
TOKEN=<token_acceso>

curl -X POST "$API/reportes/generar" -H "Authorization: Bearer $TOKEN"
curl "$API/reportes/resumen_general" -H "Authorization: Bearer $TOKEN"
curl "$API/reportes?prefijo=diario_2026-10" -H "Authorization: Bearer $TOKEN"
```

Respuesta de `POST /reportes/generar` (`201`, tenant_1 en dev):

```json
{"reporte": {
  "tenant_id": "tenant_1", "tipo_reporte": "resumen_general",
  "total_usuarios": 102, "total_candidatos": 10002,
  "total_vacantes": 10001, "vacantes_por_estado": {"abierta": 6946, "cerrada": 3055},
  "total_postulaciones": 10001,
  "postulaciones_por_estado": {"postulado": 3440, "preseleccionado": 2011, "entrevista": 1481,
                               "oferta": 716, "contratado": 834, "rechazado": 1519},
  "total_entrevistas": 10001, "entrevistas_por_estado": {"agendada": 1507, "cancelada": 1267, "realizada": 7227},
  "total_contratados": 834, "tasa_contratacion": 8.34,
  "observaciones": "", "fecha_actualizacion": "2026-11-02T22:41:17.549509+00:00"}}
```

## Diseño de datos (DynamoDB)

**`t_reportes-<stage>`** — PK `tenant_id`, SK `tipo_reporte`

```json
{
  "tenant_id": "tenant_1",
  "tipo_reporte": "diario_2026-10-15_tecnologia",
  "fecha": "2026-10-15",
  "area": "tecnologia",
  "nuevos_candidatos": 34,
  "nuevas_vacantes": 5,
  "total_postulaciones": 27,
  "total_entrevistas": 12,
  "total_contratados": 3,
  "tasa_contratacion": 11.11,
  "observaciones": "",
  "fecha_actualizacion": "2026-11-02T22:50:00+00:00"
}
```

## Variables de entorno

| Variable | Valor |
|---|---|
| REPORTES_TABLE | t_reportes-<stage> (lectura/escritura) |
| TOKENS_TABLE | t_tokens_acceso-<stage> |
| USUARIOS_TABLE | t_usuarios-<stage> |
| CANDIDATOS_TABLE | t_candidatos-<stage> |
| ENTREVISTAS_TABLE | t_entrevistas-<stage> |

Las tablas de los demás microservicios se leen con `Query` por `tenant_id`
recorriendo todas las páginas (no `Scan`).

## Despliegue

```bash
serverless deploy --stage dev
```

Región `us-east-1`, rol `LabRole`. Requiere los otros 4 microservicios en el mismo stage.

## Datos ficticios

```bash
pip3 install boto3
python3 scripts/cargar_datos.py dev 10000
```

20 áreas × 500 días = 10,000 reportes diarios por tenant (30,000 en total).
**Ya se ejecutó en dev.**

## Pruebas

- Colección Postman: `postman/reportes.postman_collection.json`.
- Prueba de integración de los 5 microservicios: `prueba_integracion.sh`.

## Nota sobre Vacantes en RDS

Vacantes y postulaciones se sirven desde RDS MySQL (schema por tenant). `generarReporte`
cuenta vacantes y postulaciones por estado en RDS (`common/rds.py`, `GROUP BY estado`),
no en DynamoDB; usuarios, candidatos, entrevistas y tokens siguen en DynamoDB. Esa función
corre dentro de la VPC y requiere `RDS_HOST`, `RDS_USER`, `RDS_PASSWORD`, `RDS_SG_IDS` y
`RDS_SUBNET_IDS` al desplegar.
