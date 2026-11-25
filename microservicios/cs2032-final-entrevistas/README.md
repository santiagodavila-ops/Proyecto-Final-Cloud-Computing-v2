# cs2032-entrevistas — Microservicio de Entrevistas / Seguimiento

CRM de Empleabilidad Nacional — CS2032 (Grupo 1).

Registra las entrevistas (la "actividad" del CRM) de un candidato para una vacante.

## API desplegada (dev)

```
https://nhso47cnu1.execute-api.us-east-1.amazonaws.com/dev
```

Todas las rutas requieren `Authorization: Bearer <token_acceso>` (login en
`https://hwi0abum32.execute-api.us-east-1.amazonaws.com/dev/usuarios/login`).
El `tenant_id` se toma siempre del token.

| Método | Ruta | Operación |
|---|---|---|
| GET | /entrevistas | Listar (`?estado=`, `?candidato_id=`, `?vacante_id=`, `?cursor=`) |
| POST | /entrevistas | Agendar entrevista (nace `agendada`) |
| GET | /entrevistas/{entrevista_id} | Buscar entrevista |
| PUT | /entrevistas/{entrevista_id} | Modificar `entrevistador`, `fecha_hora`, `modalidad`, `estado`, `notas` |
| DELETE | /entrevistas/{entrevista_id} | Eliminar entrevista |

Valores:
- `modalidad`: `presencial` | `virtual`
- `estado`: `agendada` | `realizada` | `cancelada`
- `fecha_hora`: ISO 8601, p. ej. `2026-11-20T15:00:00-05:00`

Al crear, se valida que `candidato_id` exista en Candidatos y `vacante_id` en
Vacantes (mismo tenant). `postulacion_id` es opcional.

Los listados devuelven hasta 100 ítems y un `cursor` para la página siguiente.
Con filtros, una página puede venir con menos de 100 ítems aunque haya más: se
sigue pidiendo con `cursor` hasta que sea `null`.

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
API=https://nhso47cnu1.execute-api.us-east-1.amazonaws.com/dev
TOKEN=<token_acceso>

curl -X POST "$API/entrevistas" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"candidato_id":"CANDIDATO_ID","vacante_id":"VACANTE_ID","entrevistador":"Carla Ruiz","fecha_hora":"2026-11-20T15:00:00-05:00","modalidad":"virtual"}'

curl "$API/entrevistas?estado=agendada" -H "Authorization: Bearer $TOKEN"

curl -X PUT "$API/entrevistas/ENTREVISTA_ID" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"estado":"realizada","notas":"Buen perfil"}'

curl -X DELETE "$API/entrevistas/ENTREVISTA_ID" -H "Authorization: Bearer $TOKEN"
```

Errores: `400` datos inválidos, `401` token ausente/inválido/expirado, `404`
entrevista, candidato o vacante inexistente dentro del tenant.

## Eventos (SNS + SQS)

Al agendar una entrevista (`POST /entrevistas`), `crear_entrevista` guarda el ítem
y publica el evento `entrevista_agendada` en el tópico SNS
`topico-entrevistas-agendadas-<stage>` (campos: `tenant_id`, `entrevista_id`,
`candidato_id`, `vacante_id`, `fecha_hora`, `modalidad`, `entrevistador`). Si la
publicación falla, se registra el error pero la entrevista queda creada.

El tópico está suscrito a la cola SQS `cola-notificaciones-entrevistas-<stage>`, que
consume la Lambda `procesarNotificacion` (lotes de 5, `ReportBatchItemFailures`):
simula el recordatorio al candidato y al entrevistador escribiendo logs en
CloudWatch; no se envían correos reales.

## Diseño de datos (DynamoDB)

**`t_entrevistas-<stage>`** — PK `tenant_id`, SK `entrevista_id` (uuid4)

```json
{
  "tenant_id": "tenant_1",
  "entrevista_id": "0c6d9b1e-7a43-4f0b-bb2e-5d8f3a1c9e72",
  "candidato_id": "a8ecdea6-fd60-4045-81be-32ec8dc51921",
  "vacante_id": "6f1c2a0e-3b7d-4c55-9a43-1f0e2d9b7c11",
  "postulacion_id": "b7e4…",
  "entrevistador": "Carla Ruiz",
  "fecha_hora": "2026-11-20T15:00:00-05:00",
  "modalidad": "virtual",
  "estado": "agendada",
  "notas": "",
  "fecha_creacion": "2026-11-02T22:50:00+00:00",
  "fecha_actualizacion": "2026-11-02T22:50:00+00:00"
}
```

## Variables de entorno

| Variable | Valor |
|---|---|
| ENTREVISTAS_TABLE | t_entrevistas-<stage> |
| TOPICO_ENTREVISTAS_ARN | ARN del tópico SNS `topico-entrevistas-agendadas-<stage>` (solo `crearEntrevista`) |
| CANDIDATOS_TABLE | t_candidatos-<stage> (solo lectura) |
| VACANTES_TABLE | t_vacantes-<stage> (solo lectura) |
| TOKENS_TABLE | t_tokens_acceso-<stage> (solo lectura) |

## Despliegue

```bash
serverless deploy --stage dev
```

Región `us-east-1`, rol `LabRole`. Requiere Usuarios, Candidatos y Vacantes en el
mismo stage. El despliegue crea también el tópico SNS, la cola SQS y la suscripción.

## Datos ficticios

```bash
pip3 install boto3 faker
python3 scripts/cargar_datos.py dev 10000
```

Crea 10,000 entrevistas por tenant (30,000 en total) a partir de postulaciones
reales de `t_postulaciones-dev`; las pasadas quedan `realizada`/`cancelada` y las
futuras `agendada`. **Ya se ejecutó en dev.**

## Pruebas

- Colección Postman: `postman/entrevistas.postman_collection.json`.
- Prueba de integración de los 5 microservicios: `prueba_integracion.sh`.
