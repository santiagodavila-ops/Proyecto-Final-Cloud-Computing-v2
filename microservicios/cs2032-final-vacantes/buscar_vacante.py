from common.auth import validar_token
from common.rds import buscar_vacante_rds
from common.utilidades import path_param, respuesta


def handler(event, context):
    item, error = validar_token(event)
    if error:
        return error
    tenant_id = item["tenant_id"]
    vacante = buscar_vacante_rds(tenant_id, path_param(event, "vacante_id"))
    if not vacante:
        return respuesta(404, {"error": "Vacante no encontrada"})
    return respuesta(200, {"vacante": vacante})
