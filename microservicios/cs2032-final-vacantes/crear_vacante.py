from common.auth import validar_token
from common.rds import crear_vacante_rds
from common.respuestas import leer_body
from common.utilidades import ahora, respuesta, validar_vacante


def handler(event, context):
    item, error = validar_token(event)
    if error:
        return error
    tenant_id = item["tenant_id"]
    datos, error = leer_body(event)
    if error:
        return error
    cambios, mensaje = validar_vacante(datos, parcial=False)
    if mensaje:
        return respuesta(400, {"error": mensaje})
    vacante = crear_vacante_rds(tenant_id, cambios, ahora())
    return respuesta(201, {"vacante": vacante})
