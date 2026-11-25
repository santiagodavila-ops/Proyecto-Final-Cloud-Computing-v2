"""Lambda Authorizer para validación perimetral de tokens en AWS API Gateway.

Valida tokens de acceso contra DynamoDB (t_tokens_acceso-{stage}) en el perímetro
de API Gateway antes de que la petición llegue a los microservicios de negocio.
Soporta caché de políticas de 300 segundos en API Gateway (resultTtlInSeconds: 300)
e inyecta tenant_id, usuario_id y rol en requestContext.authorizer.
"""
import os
import time
import boto3

REGION = os.environ.get("AWS_REGION", "us-east-1")
TOKENS_TABLE = os.environ.get("TOKENS_TABLE", "t_tokens_acceso-dev")
USUARIOS_TABLE = os.environ.get("USUARIOS_TABLE", "t_usuarios-dev")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
tabla_tokens = dynamodb.Table(TOKENS_TABLE)
tabla_usuarios = dynamodb.Table(USUARIOS_TABLE)


def extraer_token(event):
    """Extrae el token Bearer tanto de eventos TOKEN como de REQUEST."""
    raw = None
    if "authorizationToken" in event:
        raw = event.get("authorizationToken")
    elif "headers" in event and isinstance(event.get("headers"), dict):
        headers = event["headers"]
        raw = headers.get("Authorization") or headers.get("authorization")

    if not raw or not isinstance(raw, str):
        return None

    raw = raw.strip()
    if raw.lower().startswith("bearer "):
        token = raw[7:].strip()
    else:
        token = raw
    return token if token else None


def construir_recurso_wildcard(method_arn):
    """Construye un ARN con comodín para habilitar caching efectivo en API Gateway.

    methodArn típico:
      arn:aws:execute-api:<region>:<account-id>:<api-id>/<stage>/<method>/<resourcePath>
    Para que el TTL de 300 segundos no bloquee subsecuentes métodos o rutas de la
    misma API (o entre microservicios con el mismo token), se retorna un ARN wildcard.
    """
    if not method_arn or method_arn == "*":
        return "*"
    partes = method_arn.split(":")
    if len(partes) >= 6:
        region = partes[3]
        account_id = partes[4]
        return f"arn:aws:execute-api:{region}:{account_id}:*/*/*"
    return method_arn


def generar_politica(principal_id, effect, resource, context=None):
    """Genera el documento IAM Policy para el Authorizer de API Gateway."""
    auth_response = {
        "principalId": str(principal_id)
    }
    if effect and resource:
        auth_response["policyDocument"] = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": effect,
                    "Resource": resource
                }
            ]
        }
    if context:
        # API Gateway solo admite valores primitivos en context (string, int, bool)
        auth_response["context"] = {
            str(k): str(v) for k, v in context.items() if v is not None
        }
    return auth_response


def validar_token_en_bd(token):
    """Verifica el token contra la tabla DynamoDB de tokens de acceso."""
    try:
        res = tabla_tokens.get_item(Key={"token": token})
        item = res.get("Item")
        if not item:
            return None, "Token no existe en tabla de tokens"
        if item.get("tipo") != "acceso":
            return None, f"Tipo de token no permitido: {item.get('tipo')}"
        expira = int(item.get("expira", 0))
        ahora = int(time.time())
        if expira <= ahora:
            return None, f"Token expirado (expira={expira}, ahora={ahora})"
        return item, None
    except Exception as e:
        print(f"Error consultando DynamoDB para token: {e}")
        return None, str(e)


def obtener_rol_usuario(tenant_id, usuario_id, fallback_rol="reclutador"):
    """Recupera el rol del usuario desde t_usuarios si no está en el token."""
    if not tenant_id or not usuario_id:
        return fallback_rol
    try:
        res = tabla_usuarios.get_item(Key={"tenant_id": tenant_id, "usuario_id": usuario_id})
        usr = res.get("Item")
        if usr and usr.get("rol"):
            return str(usr["rol"])
    except Exception as e:
        print(f"Advertencia al consultar rol de usuario {usuario_id}: {e}")
    return fallback_rol


def handler(event, context=None):
    """Handler principal del Lambda Authorizer."""
    method_arn = event.get("methodArn", "*")
    resource_arn = construir_recurso_wildcard(method_arn)

    token = extraer_token(event)
    if not token:
        print("Authorizer: No se encontro token Bearer en el evento")
        return generar_politica("anonymous", "Deny", resource_arn)

    item, error = validar_token_en_bd(token)
    if error:
        print(f"Authorizer: Acceso DENEGADO - {error}")
        return generar_politica("anonymous", "Deny", resource_arn)

    tenant_id = item.get("tenant_id", "")
    usuario_id = item.get("usuario_id", "")
    rol = item.get("rol")
    if not rol:
        rol = obtener_rol_usuario(tenant_id, usuario_id)

    principal_id = str(usuario_id) if usuario_id else "authenticated_user"
    auth_context = {
        "tenant_id": str(tenant_id),
        "usuario_id": str(usuario_id),
        "rol": str(rol),
    }

    print(f"Authorizer: Acceso PERMITIDO para principalId={principal_id}, tenant={tenant_id}, rol={rol}")
    return generar_politica(principal_id, "Allow", resource_arn, context=auth_context)
