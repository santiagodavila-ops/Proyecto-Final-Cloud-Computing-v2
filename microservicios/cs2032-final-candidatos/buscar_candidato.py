from common.auth import validar_token
from common.candidatos import obtener_candidato, path_param
from common.respuestas import _respuesta


def handler(event, context):
    item, error = validar_token(event)
    if error:
        return error
    candidato = obtener_candidato(item["tenant_id"], path_param(event, "candidato_id"))
    if not candidato:
        return _respuesta(404, {"error": "Candidato no encontrado"})
    return _respuesta(200, {"candidato": candidato})
