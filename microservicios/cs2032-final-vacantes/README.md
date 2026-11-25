# cs2032-vacantes — Microservicio de Vacantes / Postulaciones

CRM de Empleabilidad Nacional — CS2032 (Grupo 1). Responsable: Patrick Medina.

Gestiona las **vacantes** que publica cada tenant y las **postulaciones** de los
candidatos a esas vacantes. La postulación es la "oportunidad" del CRM y recorre
el pipeline:

```
postulado → preseleccionado → entrevista → oferta → contratado
                                                  ↘ rechazado (desde cualquier etapa)
```

Una vacante puede recibir muchas postulaciones; por eso el pipeline vive en la
postulación y la vacante solo tiene estado `abierta` / `cerrada`.

## API desplegada (dev)

```
https://7i7gtr9xv7.execute-api.us-east-1.amazonaws.com/dev
```

Todas las rutas requieren `Authorization: Bearer <token_acceso>`. El token se obtiene en
`POST https://hwi0abum32.execute-api.us-east-1.amazonaws.com/dev/usuarios/login`
con `{"email","password"}` (sin `tenant_id`); la respuesta trae `token_acceso`,
`token_refresh`, `rol`, `tenant_id` y `usuario_id`. `POST /usuarios/refresh` renueva el acceso.
El `tenant_id` se toma **siempre del token**, nunca del body ni de la URL.

| Método | Ruta | Operación |
|---|---|---|
| GET | /vacantes | Listar vacantes (`?estado=abierta\|cerrada`, `?cursor=`) |
| POST | /vacantes | Crear vacante (nace `abierta`) |
| GET | /vacantes/{vacante_id} | Buscar vacante |
| PUT | /vacantes/{vacante_id} | Modificar vacante (incluye `estado`) |
| DELETE | /vacantes/{vacante_id} | Eliminar vacante (`409` si tiene postulaciones) |
| GET | /postulaciones | Listar (`?estado=`, `?vacante_id=`, `?cursor=`) |
| POST | /postulaciones | Postular un candidato a una vacante abierta |
| GET | /postulaciones/{postulacion_id} | Buscar postulación |
| PUT | /postulaciones/{postulacion_id} | Mover en el pipeline (`estado`) y/o `notas` |
| DELETE | /postulaciones/{postulacion_id} | Eliminar postulación |

Los listados devuelven hasta 100 ítems y un `cursor`; si no es `null`, se pide
la página siguiente con `?cursor=<valor>`.

## Ejemplos con curl

El token se obtiene así (sin `tenant_id`):

```bash
curl -X POST https://hwi0abum32.execute-api.us-east-1.amazonaws.com/dev/usuarios/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo.tenant_1@cs2032.test","password":"Demo-cs2032"}'
```

```bash
API=https://7i7gtr9xv7.execute-api.us-east-1.amazonaws.com/dev
TOKEN=<token_acceso>
```

Crear vacante (`titulo` y `descripcion` obligatorios; `area`, `ubicacion`,
`modalidad` = `presencial|remoto|hibrido` y `salario` opcionales):

```bash
curl -X POST "$API/vacantes" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"titulo":"Analista de Datos","descripcion":"SQL y Python","area":"Tecnología","ubicacion":"Lima","modalidad":"hibrido","salario":5500}'
```

Respuesta `201`:

```json
{"vacante": {"tenant_id": "tenant_1", "vacante_id": "6f1c…", "titulo": "Analista de Datos",
  "descripcion": "SQL y Python", "area": "Tecnología", "ubicacion": "Lima",
  "modalidad": "hibrido", "salario": 5500, "estado": "abierta",
  "fecha_publicacion": "2026-11-02T22:40:11+00:00", "fecha_actualizacion": "2026-11-02T22:40:11+00:00"}}
```

Postular un candidato (el `candidato_id` debe existir en Candidatos y la vacante
debe estar abierta):

```bash
curl -X POST "$API/postulaciones" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"vacante_id":"VACANTE_ID","candidato_id":"CANDIDATO_ID"}'
```

Avanzar en el pipeline:

```bash
curl -X PUT "$API/postulaciones/POSTULACION_ID" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"estado":"entrevista"}'
```

Postulaciones en etapa de entrevista / postulantes de una vacante:

```bash
curl "$API/postulaciones?estado=entrevista" -H "Authorization: Bearer $TOKEN"
curl "$API/postulaciones?vacante_id=VACANTE_ID" -H "Authorization: Bearer $TOKEN"
```

Errores: `400` datos inválidos, `401` token ausente/inválido/expirado, `404`
recurso inexistente dentro del tenant, `409` al eliminar una vacante que aún tiene
postulaciones.

## RDS MySQL

Vacantes y postulaciones viven en RDS MySQL con el patrón *Single Database, Multiple
Schemas*: un schema por tenant (`tenant_1`, `tenant_2`, `tenant_3`) con las tablas
`vacantes` y `postulaciones` (clave foránea a vacantes). El `tenant_id` del token
decide el schema (`common/rds.py`); el nombre del schema nunca viene del cliente.

- Esquema: `sql/schema.sql` (se ejecuta una sola vez con un cliente SQL, no desde las Lambdas).
- Migración desde DynamoDB: `scripts/migrar_a_rds.py` (idempotente; requiere acceso de red a RDS).
- Las Lambdas se despliegan en la misma VPC que la instancia RDS (ver variables abajo).

## Diseño de datos (DynamoDB, origen de la migración a RDS)

> Vacantes y postulaciones se sirven desde RDS MySQL (schema por tenant, tabla `postulaciones`). Las tablas DynamoDB de abajo son el formato de origen que `scripts/migrar_a_rds.py` migra.

**`t_vacantes-<stage>`** — PK `tenant_id`, SK `vacante_id` (uuid4)

```json
{
  "tenant_id": "tenant_1",
  "vacante_id": "6f1c2a0e-3b7d-4c55-9a43-1f0e2d9b7c11",
  "titulo": "Analista de Datos",
  "descripcion": "SQL, Python y Power BI",
  "area": "Tecnología",
  "ubicacion": "Lima",
  "modalidad": "hibrido",
  "salario": 5500,
  "estado": "abierta",
  "fecha_publicacion": "2026-11-02T22:40:11.512+00:00",
  "fecha_actualizacion": "2026-11-02T22:40:11.512+00:00"
}
```

**`t_postulaciones-<stage>`** — PK `tenant_id`, SK `postulacion_id` (uuid4)

- GSI `indice_estado`: `tenant_id` + `estado` → postulaciones por etapa del pipeline.
- GSI `indice_vacante`: `tenant_id` + `vacante_id` → postulantes de una vacante.

```json
{
  "tenant_id": "tenant_1",
  "postulacion_id": "b7e4…",
  "vacante_id": "6f1c2a0e-3b7d-4c55-9a43-1f0e2d9b7c11",
  "candidato_id": "a8ecdea6-fd60-4045-81be-32ec8dc51921",
  "titulo_vacante": "Analista de Datos",
  "estado": "entrevista",
  "notas": "",
  "fecha_postulacion": "2026-11-02T22:41:03+00:00",
  "fecha_actualizacion": "2026-11-02T22:45:20+00:00"
}
```

## Variables de entorno

| Variable | Valor |
|---|---|
| VACANTES_TABLE | t_vacantes-<stage> |
| POSTULACIONES_TABLE | t_postulaciones-<stage> |
| CANDIDATOS_TABLE | t_candidatos-<stage> (solo lectura, valida `candidato_id`) |
| TOKENS_TABLE | t_tokens_acceso-<stage> (solo lectura) |
| RDS_HOST, RDS_USER, RDS_PASSWORD | Conexión a RDS MySQL (`RDS_PORT`, por defecto 3306). La contraseña no va en el repo: se exporta antes de desplegar |
| RDS_SG_IDS, RDS_SUBNET_IDS | Grupo de seguridad y subredes (separadas por coma) de la VPC de RDS donde corren las Lambdas |
| RDS_VPC_ID, RDS_ROUTE_TABLE_IDS | VPC y tablas de rutas (separadas por coma) para el endpoint de VPC |

`VACANTES_TABLE` y `POSTULACIONES_TABLE` solo las usan los scripts de carga y migración (DynamoDB de origen).

## Despliegue

```bash
# exportar antes las variables RDS_* de la tabla anterior (sin escribirlas en el repo)
serverless deploy --stage dev
```

Región `us-east-1`, rol `LabRole` de AWS Academy. Requiere que Usuarios y
Candidatos estén desplegados en el mismo stage.

## Datos ficticios

```bash
pip3 install boto3 faker
python3 scripts/cargar_datos.py dev 10000
```

Carga, por cada tenant (`tenant_1..3`), 10,000 vacantes y 10,000 postulaciones
que apuntan a candidatos reales de `t_candidatos-dev`. Total: 30,000 vacantes +
30,000 postulaciones. El script escribe en las tablas DynamoDB `t_vacantes-dev` y
`t_postulaciones-dev` (fuente de la migración); luego `scripts/migrar_a_rds.py` las pasa
a RDS, donde viven las postulaciones y vacantes. **Ya se ejecutó en dev**; volver a correrlo agrega otros tantos.

## Pruebas

- Colección Postman: `postman/vacantes.postman_collection.json` (ejecutar en orden).
- Prueba de integración de los 5 microservicios: `prueba_integracion.sh`.
