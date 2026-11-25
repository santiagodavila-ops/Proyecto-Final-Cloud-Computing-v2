from common.auth import validar_token
from common.rds import buscar_vacante_rds, crear_postulacion_rds
from common.respuestas import leer_body, texto
from common.utilidades import ahora, existe_candidato, respuesta


def handler(event, context):
    item, error = validar_token(event)
    if error:
        return error
    tenant_id = item["tenant_id"]
    datos, error = leer_body(event)
    if error:
        return error
    vacante_id = datos.get("vacante_id")
    candidato_id = datos.get("candidato_id")
    if not texto(vacante_id) or not texto(candidato_id):
        return respuesta(400, {"error": "Faltan vacante_id y candidato_id"})
    # La vacante vive en RDS (mismo schema del tenant); el candidato, en DynamoDB
    vacante = buscar_vacante_rds(tenant_id, vacante_id)
    if not vacante:
        return respuesta(404, {"error": "Vacante no encontrada"})
    if vacante["estado"] != "abierta":
        return respuesta(400, {"error": "La vacante está cerrada"})
    if not existe_candidato(tenant_id, candidato_id):
        return respuesta(404, {"error": "Candidato no encontrado"})
    notas = datos["notas"].strip() if texto(datos.get("notas")) else ""
    postulacion = crear_postulacion_rds(tenant_id, vacante, candidato_id, notas, ahora())
    return respuesta(201, {"postulacion": postulacion})
