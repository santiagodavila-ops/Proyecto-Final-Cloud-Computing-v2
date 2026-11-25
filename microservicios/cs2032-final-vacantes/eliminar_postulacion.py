from common.auth import validar_token
from common.rds import eliminar_postulacion_rds
from common.utilidades import path_param, respuesta


def handler(event, context):
    item, error = validar_token(event)
    if error:
        return error
    tenant_id = item["tenant_id"]
    if not eliminar_postulacion_rds(tenant_id, path_param(event, "postulacion_id")):
        return respuesta(404, {"error": "Postulación no encontrada"})
    return respuesta(200, {"mensaje": "Postulación eliminada"})
