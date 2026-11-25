from common.auth import validar_token
from common.rds import listar_postulaciones_rds
from common.utilidades import ESTADOS_POSTULACION, respuesta


def handler(event, context):
    item, error = validar_token(event)
    if error:
        return error
    tenant_id = item["tenant_id"]
    parametros = event.get("queryStringParameters") or {}
    estado = parametros.get("estado")
    vacante_id = parametros.get("vacante_id")
    if estado and estado not in ESTADOS_POSTULACION:
        return respuesta(400, {"error": f"estado debe ser uno de {list(ESTADOS_POSTULACION)}"})
    items, cursor, cursor_invalido = listar_postulaciones_rds(
        tenant_id, estado, vacante_id, parametros.get("cursor"))
    if cursor_invalido:
        return respuesta(400, {"error": "cursor inválido"})
    return respuesta(200, {"postulaciones": items, "cursor": cursor})
