import uuid
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key

from common.auth import validar_token
from common.dynamo import obtener_usuario, tabla_usuarios
from common.passwords import hashear_password
from common.respuestas import _respuesta, leer_body, texto

LONGITUD_MINIMA_PASSWORD = 6
ROLES_VALIDOS = ("administrador", "reclutador")
ROL_POR_DEFECTO = "reclutador"


def _buscar_por_email(email):
    # Consulta al GSI indice_email: el correo es único en todos los tenants
    resultado = tabla_usuarios().query(
        IndexName="indice_email",
        KeyConditionExpression=Key("email").eq(email),
        Limit=1,
    )
    items = resultado.get("Items", [])
    return items[0] if items else None


def handler(event, context):
    # Solo un administrador autenticado puede crear usuarios, y solo en su propio tenant
    token_item, error = validar_token(event)
    if error:
        return error
    tenant_id = token_item["tenant_id"]  # se ignora cualquier tenant_id del body

    # El rol se lee del registro del usuario que hace la petición, no del token
    solicitante = obtener_usuario(tenant_id, token_item["usuario_id"])
    if not solicitante or solicitante.get("rol") != "administrador":
        return _respuesta(403, {"error": "Solo un administrador puede crear usuarios"})

    datos, error = leer_body(event)
    if error:
        return error
    nombre = datos.get("nombre")
    email = datos.get("email")
    password = datos.get("password")
    if not texto(nombre) or not texto(email):
        return _respuesta(400, {"error": "Faltan nombre o email"})
    if not isinstance(password, str) or len(password) < LONGITUD_MINIMA_PASSWORD:
        return _respuesta(400, {"error": f"La contraseña debe tener al menos {LONGITUD_MINIMA_PASSWORD} caracteres"})
    rol = datos.get("rol", ROL_POR_DEFECTO)
    if rol not in ROLES_VALIDOS:
        return _respuesta(400, {"error": "Rol inválido"})
    email = email.strip().lower()
    if _buscar_por_email(email):
        return _respuesta(409, {"error": "Ya existe un usuario con ese correo"})

    usuario = {
        "tenant_id": tenant_id,
        "usuario_id": str(uuid.uuid4()),
        "nombre": nombre.strip(),
        "email": email,
        "password_hash": hashear_password(password),
        "rol": rol,
        "fecha_registro": datetime.now(timezone.utc).isoformat(),
    }
    tabla_usuarios().put_item(Item=usuario)
    publico = {k: v for k, v in usuario.items() if k != "password_hash"}
    return _respuesta(201, {"usuario": publico})
