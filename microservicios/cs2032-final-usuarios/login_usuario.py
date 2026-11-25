from boto3.dynamodb.conditions import Key

from common.auth import TIPO_ACCESO, TIPO_REFRESH, emitir_token
from common.dynamo import tabla_usuarios
from common.passwords import hashear_password, verificar_password
from common.respuestas import _respuesta, leer_body, texto


def _buscar_por_email(email):
    # Consulta al GSI indice_email (el correo es único en todo el sistema, sin tenant)
    resultado = tabla_usuarios().query(
        IndexName="indice_email",
        KeyConditionExpression=Key("email").eq(email),
        Limit=1,
    )
    items = resultado.get("Items", [])
    return items[0] if items else None


def handler(event, context):
    datos, error = leer_body(event)
    if error:
        return error
    # Se ignora cualquier tenant_id del body: el tenant sale del registro del usuario
    email = datos.get("email")
    password = datos.get("password")
    if not texto(email) or not isinstance(password, str):
        return _respuesta(400, {"error": "Faltan email o password"})

    usuario = _buscar_por_email(email.strip().lower())
    # Mismo mensaje para usuario inexistente y contraseña incorrecta
    if not usuario:
        return _respuesta(401, {"error": "Credenciales inválidas"})
    ok, necesita_rehash = verificar_password(password, usuario.get("password_hash"))
    if not ok:
        return _respuesta(401, {"error": "Credenciales inválidas"})

    tenant_id = usuario["tenant_id"]
    usuario_id = usuario["usuario_id"]
    if necesita_rehash:
        # Migración transparente del hash legado sha256 a pbkdf2; si falla no bloquea el login
        try:
            tabla_usuarios().update_item(
                Key={"tenant_id": tenant_id, "usuario_id": usuario_id},
                UpdateExpression="SET password_hash = :h",
                ExpressionAttributeValues={":h": hashear_password(password)},
            )
        except Exception as e:
            print(f"No se pudo actualizar el hash de {usuario_id}: {e}")
    rol_usuario = usuario.get("rol", "reclutador")
    token_acceso, expira_acceso = emitir_token(TIPO_ACCESO, tenant_id, usuario_id, rol=rol_usuario)
    token_refresh, expira_refresh = emitir_token(TIPO_REFRESH, tenant_id, usuario_id, rol=rol_usuario)
    return _respuesta(200, {
        "token_acceso": token_acceso,
        "token_refresh": token_refresh,
        "expira_acceso": expira_acceso,
        "expira_refresh": expira_refresh,
        "tenant_id": tenant_id,
        "usuario_id": usuario_id,
        "rol": usuario.get("rol", "reclutador"),
        # DEPRECADO: alias de token_acceso por compatibilidad con el frontend actual
        "token": token_acceso,
    })
