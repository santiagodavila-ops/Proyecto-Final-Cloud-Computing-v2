import uuid

from common.auth import validar_token
from common.candidatos import ahora, validar_candidato
from common.dynamo import tabla_candidatos
from common.respuestas import _respuesta, leer_body


def handler(event, context):
    item, error = validar_token(event)
    if error:
        return error
    tenant_id = item["tenant_id"]
    datos, error = leer_body(event)
    if error:
        return error
    cambios, mensaje = validar_candidato(datos, parcial=False)
    if mensaje:
        return _respuesta(400, {"error": mensaje})
    ahora_iso = ahora()
    candidato = {
        "tenant_id": tenant_id,
        "candidato_id": str(uuid.uuid4()),
        **cambios,
        "estado": "activo",
        "cv_url": "",
        "fecha_registro": ahora_iso,
        "fecha_actualizacion": ahora_iso,
    }
    tabla_candidatos().put_item(Item=candidato)
    return _respuesta(201, {"candidato": candidato})
