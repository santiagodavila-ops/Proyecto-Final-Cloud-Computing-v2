from common.auth import validar_token
from common.respuestas import _respuesta


def handler(event, context):
    item, error = validar_token(event)
    if error:
        return error
    return _respuesta(200, {"tenant_id": item["tenant_id"], "usuario_id": item["usuario_id"]})
