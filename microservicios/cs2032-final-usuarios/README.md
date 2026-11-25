# cs2032-usuarios — Microservicio de Usuarios / Autenticación

CRM de Empleabilidad Nacional — CS2032 (Grupo 1).

Registra usuarios por tenant, emite los tokens de acceso y renovación, y valida tokens.
Los demás microservicios leen la tabla `t_tokens_acceso-<stage>` mediante su
`common/auth.py` (contrato compartido).

## API desplegada (dev)

```
https://hwi0abum32.execute-api.us-east-1.amazonaws.com/dev
```

| Método | Ruta | Operación |
|---|---|---|
| POST | /usuarios/login | Login con `{email, password}` (sin `tenant_id`). Público |
| POST | /usuarios/refresh | Renueva el acceso con `{"token_refresh"}`. Público |
| POST | /usuarios | Crear usuario (solo administrador; el tenant sale del token) |
| GET | /usuarios/validar | Valida el `token_acceso` y devuelve `tenant_id` y `usuario_id` |

## Login

```bash
API=https://hwi0abum32.execute-api.us-east-1.amazonaws.com/dev

curl -X POST "$API/usuarios/login" -H 'Content-Type: application/json' \
  -d '{"email":"demo.tenant_1@cs2032.test","password":"Demo-cs2032"}'
```

Respuesta: `token_acceso`, `token_refresh`, `expira_acceso`, `expira_refresh`,
`tenant_id`, `usuario_id`, `rol` y el alias deprecado `token` (= `token_acceso`).
El correo es único en todos los tenants, por eso el login no necesita `tenant_id`.

Las rutas protegidas llevan `Authorization: Bearer <token_acceso>`:

```bash
TOKEN=<token_acceso>
curl "$API/usuarios/validar" -H "Authorization: Bearer $TOKEN"

curl -X POST "$API/usuarios/refresh" -H 'Content-Type: application/json' \
  -d '{"token_refresh":"<token_refresh>"}'
```

`/usuarios/refresh` responde `{token_acceso, expira_acceso}`. Si el `token_refresh`
también expiró, hay que volver a iniciar sesión.

## Crear usuario

Requiere el `token_acceso` de un usuario con rol `administrador`. El usuario se crea
en el tenant del token (cualquier `tenant_id` del body se ignora).

```bash
curl -X POST "$API/usuarios" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"nombre":"Ana Torres","email":"ana@empresa.pe","password":"<contraseña>","rol":"reclutador"}'
```

- `nombre`, `email` y `password` (mínimo 6 caracteres) son obligatorios.
- `rol` es opcional: `administrador` o `reclutador` (por defecto `reclutador`).
- Errores: `400` datos inválidos, `401` token ausente/inválido/expirado, `403` el
  solicitante no es administrador, `409` el correo ya existe en cualquier tenant.

## Contraseñas

Se guardan con PBKDF2-SHA256 y salt (`common/passwords.py`). Los hashes legados se
rehashean automáticamente en el siguiente login correcto.

## Diseño de datos (DynamoDB)

- **`t_usuarios-<stage>`** — PK `tenant_id`, SK `usuario_id` (uuid4); GSI `indice_email`
  (`email`) para login y unicidad del correo.
- **`t_tokens_acceso-<stage>`** — PK `token`; atributos `tenant_id`, `usuario_id`, tipo
  (acceso o refresh) y `ttl` (TTL de DynamoDB elimina los tokens vencidos).

## Estructura del código

Una función por archivo en la raíz (`crear_usuario.py`, `login_usuario.py`,
`refrescar_token.py`, `validar_token_endpoint.py`) y `common/` con `auth.py` (contrato
compartido), `dynamo.py`, `passwords.py` y `respuestas.py`. `serverless.yml` usa
`package: individually`.

## Variables de entorno

| Variable | Valor |
|---|---|
| USUARIOS_TABLE | t_usuarios-<stage> |
| TOKENS_TABLE | t_tokens_acceso-<stage> |

## Despliegue

```bash
serverless deploy --stage dev
```

Región `us-east-1`, rol `LabRole`. Este servicio crea las tablas de usuarios y tokens,
así que se despliega primero.

## Pruebas

- Pruebas unitarias en `tests/`.
- Prueba de integración de los 5 microservicios: `prueba_integracion.sh` (en la raíz de `repos`).
