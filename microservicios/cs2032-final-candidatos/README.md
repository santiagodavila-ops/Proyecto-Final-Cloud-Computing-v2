# cs2032-candidatos — Microservicio de Candidatos

CRM de Empleabilidad Nacional — CS2032 (Grupo 1).

Gestiona los candidatos de cada tenant y la carga de su CV a S3 mediante URL prefirmada.

## API desplegada (dev)

```
https://d3q8s9iuzj.execute-api.us-east-1.amazonaws.com/dev
```

Todas las rutas requieren `Authorization: Bearer <token_acceso>`. El `tenant_id` se
toma siempre del token, nunca del body ni de la URL.

| Método | Ruta | Operación |
|---|---|---|
| GET | /candidatos | Listar candidatos del tenant (100 por página, `?ultimo_id=` como cursor) |
| POST | /candidatos | Crear candidato (nace `activo`) |
| GET | /candidatos/{candidato_id} | Buscar candidato |
| PUT | /candidatos/{candidato_id} | Modificar candidato |
| DELETE | /candidatos/{candidato_id} | Eliminar candidato |
| POST | /candidatos/{candidato_id}/cv-url | Generar URL prefirmada de S3 para subir el CV; con `{"confirmar": true}` registra el CV subido |

## Autenticación (login)

```bash
curl -X POST https://hwi0abum32.execute-api.us-east-1.amazonaws.com/dev/usuarios/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo.tenant_1@cs2032.test","password":"Demo-cs2032"}'
```

La respuesta trae `token_acceso`, `token_refresh`, `expira_acceso`, `expira_refresh`,
`tenant_id`, `usuario_id`, `rol` y el alias deprecado `token` (= `token_acceso`). Cuando
expira el acceso (`401`), `POST /usuarios/refresh` con `{"token_refresh"}` entrega uno nuevo.

## Ejemplos con curl

```bash
API=https://d3q8s9iuzj.execute-api.us-east-1.amazonaws.com/dev
TOKEN=<token_acceso>

curl -X POST "$API/candidatos" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"nombre":"Lucía Ramos","email":"lucia@correo.pe","telefono":"999111222","profesion":"Analista de datos"}'

curl "$API/candidatos" -H "Authorization: Bearer $TOKEN"

curl -X PUT "$API/candidatos/CANDIDATO_ID" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"profesion":"Científica de datos"}'

# CV: 1) pedir la URL prefirmada (vale 5 minutos), 2) subir el PDF con PUT, 3) confirmar
curl -X POST "$API/candidatos/CANDIDATO_ID/cv-url" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{}'
curl -X POST "$API/candidatos/CANDIDATO_ID/cv-url" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"confirmar": true}'
```

El CV se guarda en `<tenant_id>/<candidato_id>/cv.pdf` dentro del bucket de CVs
(privado, con acceso público bloqueado).

Errores: `400` datos inválidos, `401` token ausente/inválido/expirado, `404`
candidato inexistente dentro del tenant.

## Diseño de datos (DynamoDB)

**`t_candidatos-<stage>`** — PK `tenant_id`, SK `candidato_id` (uuid4). Atributos:
`nombre`, `email`, `telefono`, `profesion`, `estado`, `cv_url`, `fecha_registro` y
`fecha_actualizacion`.

## Variables de entorno

| Variable | Valor |
|---|---|
| CANDIDATOS_TABLE | t_candidatos-<stage> |
| TOKENS_TABLE | t_tokens_acceso-<stage> (solo lectura) |
| BUCKET_CVS | cs2032-candidatos-cv-<stage>-<id de cuenta> |

## Despliegue

```bash
serverless deploy --stage dev
```

Región `us-east-1`, rol `LabRole`. Requiere Usuarios desplegado en el mismo stage. Crea
la tabla de candidatos y el bucket S3 de CVs.

## Datos ficticios

```bash
pip3 install boto3 faker
python3 scripts/cargar_datos.py dev 10000
```

Debe correr antes que Vacantes y Entrevistas, porque sus datos apuntan a `candidato_id`
reales de `t_candidatos-<stage>`.

## Pruebas

Prueba de integración de los 5 microservicios: `prueba_integracion.sh` (en la raíz de `repos`).
