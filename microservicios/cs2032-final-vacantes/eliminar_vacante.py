from common.auth import validar_token
from common.rds import (
    RESULTADO_CON_POSTULACIONES,
    RESULTADO_NO_ENCONTRADA,
    eliminar_vacante_rds,
)
from common.utilidades import path_param, respuesta


def handler(event, context):
    item, error = validar_token(event)
    if error:
        return error
    tenant_id = item["tenant_id"]
    resultado = eliminar_vacante_rds(tenant_id, path_param(event, "vacante_id"))
    if resultado == RESULTADO_NO_ENCONTRADA:
        return respuesta(404, {"error": "Vacante no encontrada"})
    if resultado == RESULTADO_CON_POSTULACIONES:
        return respuesta(409, {"error": "La vacante tiene postulaciones y no se puede eliminar"})
    return respuesta(200, {"mensaje": "Vacante eliminada"})
