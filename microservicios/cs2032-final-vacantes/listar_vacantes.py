from common.auth import validar_token
from common.rds import listar_vacantes_rds
from common.utilidades import ESTADOS_VACANTE, respuesta


def handler(event, context):
    item, error = validar_token(event)
    if error:
        return error
    tenant_id = item["tenant_id"]
    parametros = event.get("queryStringParameters") or {}
    estado = parametros.get("estado")
    if estado and estado not in ESTADOS_VACANTE:
        return respuesta(400, {"error": f"estado debe ser uno de {list(ESTADOS_VACANTE)}"})
    items, cursor, cursor_invalido = listar_vacantes_rds(tenant_id, estado, parametros.get("cursor"))
    if cursor_invalido:
        return respuesta(400, {"error": "cursor inválido"})
    return respuesta(200, {"vacantes": items, "cursor": cursor})
