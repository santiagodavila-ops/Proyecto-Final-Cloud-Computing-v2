from common.auth import validar_token
from common.rds import modificar_vacante_rds
from common.respuestas import leer_body
from common.utilidades import ahora, path_param, respuesta, validar_vacante


def handler(event, context):
    item, error = validar_token(event)
    if error:
        return error
    tenant_id = item["tenant_id"]
    datos, error = leer_body(event)
    if error:
        return error
    cambios, mensaje = validar_vacante(datos, parcial=True)
    if mensaje:
        return respuesta(400, {"error": mensaje})
    if not cambios:
        return respuesta(400, {"error": "No hay campos válidos para modificar"})
    vacante = modificar_vacante_rds(tenant_id, path_param(event, "vacante_id"), cambios, ahora())
    if not vacante:
        return respuesta(404, {"error": "Vacante no encontrada"})
    return respuesta(200, {"mensaje": "Vacante modificada", "vacante": vacante})
