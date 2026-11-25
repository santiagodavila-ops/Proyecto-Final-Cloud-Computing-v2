"""Contrato de autenticación compartido por TODOS los microservicios.

Este archivo se copia SIN CAMBIOS en cada servicio. Solo depende de boto3
(vía common.dynamo) y de common.respuestas.

Tabla t_tokens_acceso-{stage} (PK "token", TTL sobre "ttl"). Cada item:
  token, tipo ("acceso" | "refresh"), tenant_id, usuario_id,
  expira (epoch en segundos), ttl (= expira), fecha_expiracion (ISO, compatibilidad).
"""
import time
import uuid
from datetime import datetime, timezone

from common.dynamo import tabla_tokens
from common.respuestas import _respuesta

TIPO_ACCESO = "acceso"
TIPO_REFRESH = "refresh"
DURACION_ACCESO_SEG = 15 * 60            # 15 minutos
DURACION_REFRESH_SEG = 7 * 24 * 60 * 60  # 7 días


def _ahora_epoch():
    return int(time.time())


def _iso(epoch):
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def emitir_token(tipo, tenant_id, usuario_id, rol="reclutador"):
    """Crea y guarda un token del tipo indicado. Devuelve (token, expira_iso)."""
    duracion = DURACION_ACCESO_SEG if tipo == TIPO_ACCESO else DURACION_REFRESH_SEG
    expira = _ahora_epoch() + duracion
    token = str(uuid.uuid4())
    tabla_tokens().put_item(Item={
        "token": token,
        "tipo": tipo,
        "tenant_id": tenant_id,
        "usuario_id": usuario_id,
        "rol": rol,
        "expira": expira,
        "ttl": expira,
        "fecha_expiracion": _iso(expira),
    })
    return token, _iso(expira)


def _obtener_token(token, tipo_esperado):
    """Devuelve (item, error) verificando existencia, tipo y vigencia."""
    item = tabla_tokens().get_item(Key={"token": token}).get("Item")
    if not item or item.get("tipo") != tipo_esperado:
        return None, _respuesta(401, {"error": "Token inválido"})
    if int(item.get("expira", 0)) <= _ahora_epoch():
        return None, _respuesta(401, {"error": "Token expirado"})
    return item, None


def validar_token(event):
    """Para endpoints protegidos. Devuelve (item, error_respuesta).

    Soporta dos modalidades:
    1. Perimetral (API Gateway Lambda Authorizer): Si el token ya fue validado
       en el perímetro, event['requestContext']['authorizer'] contiene tenant_id,
       usuario_id y rol. No requiere llamada a DynamoDB (0 latencia, 0 costo BD).
    2. En código (Fallback / Local / Tests): Si no hay requestContext.authorizer,
       valida el header Authorization contra DynamoDB como fallback.
    """
    auth_ctx = (event.get("requestContext") or {}).get("authorizer")
    if auth_ctx and auth_ctx.get("tenant_id"):
        return {
            "tenant_id": auth_ctx["tenant_id"],
            "usuario_id": auth_ctx.get("usuario_id", ""),
            "rol": auth_ctx.get("rol", "reclutador"),
            **auth_ctx,
        }, None

    headers = event.get("headers") or {}
    auth_header = headers.get("Authorization") or headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, _respuesta(401, {"error": "Token no enviado"})
    token = auth_header[len("Bearer "):].strip()
    if not token:
        return None, _respuesta(401, {"error": "Token no enviado"})
    item, error = _obtener_token(token, TIPO_ACCESO)
    if error:
        return None, error
    return {"tenant_id": item["tenant_id"], "usuario_id": item["usuario_id"], **item}, None


def validar_token_refresh(token_refresh):
    """Devuelve (item, error) para un token_refresh recibido en el body."""
    if not isinstance(token_refresh, str) or not token_refresh.strip():
        return None, _respuesta(401, {"error": "Token inválido"})
    return _obtener_token(token_refresh.strip(), TIPO_REFRESH)
