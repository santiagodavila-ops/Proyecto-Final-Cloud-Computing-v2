from common.auth import validar_token
from common.rds import modificar_postulacion_rds
from common.respuestas import leer_body
from common.utilidades import ESTADOS_POSTULACION, ahora, path_param, respuesta


def handler(event, context):
    """Mueve la postulación por el pipeline (estado) y/o actualiza notas."""
    item, error = validar_token(event)
    if error:
        return error
    tenant_id = item["tenant_id"]
    datos, error = leer_body(event)
    if error:
        return error
    cambios = {}
    if "estado" in datos:
        if datos["estado"] not in ESTADOS_POSTULACION:
            return respuesta(400, {"error": f"estado debe ser uno de {list(ESTADOS_POSTULACION)}"})
        cambios["estado"] = datos["estado"]
    if "notas" in datos:
        if not isinstance(datos["notas"], str):
            return respuesta(400, {"error": "notas debe ser texto"})
        cambios["notas"] = datos["notas"].strip()
    if not cambios:
        return respuesta(400, {"error": "Campos modificables: estado, notas"})
    postulacion = modificar_postulacion_rds(
        tenant_id, path_param(event, "postulacion_id"), cambios, ahora())
    if not postulacion:
        return respuesta(404, {"error": "Postulación no encontrada"})
    return respuesta(200, {"mensaje": "Postulación modificada", "postulacion": postulacion})
