from common.auth import TIPO_ACCESO, emitir_token, validar_token_refresh
from common.respuestas import _respuesta, leer_body


def handler(event, context):
    datos, error = leer_body(event)
    if error:
        return error
    item, error = validar_token_refresh(datos.get("token_refresh"))
    if error:
        return error
    token_acceso, expira_acceso = emitir_token(TIPO_ACCESO, item["tenant_id"], item["usuario_id"])
    return _respuesta(200, {"token_acceso": token_acceso, "expira_acceso": expira_acceso})
