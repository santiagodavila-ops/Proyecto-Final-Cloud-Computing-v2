import uuid

from common.auth import validar_token
from common.dynamo import tabla_candidatos, tabla_entrevistas
from common.eventos import publicar_entrevista_agendada
from common.entrevistas import _ahora, _leer_body, _respuesta, _texto, _validar
from common.rds import vacante_existe


def handler(event, context):
    item, error = validar_token(event)
    if error:
        return error
    tenant_id = item["tenant_id"]
    datos, error = _leer_body(event)
    if error:
        return error
    candidato_id = datos.get("candidato_id")
    vacante_id = datos.get("vacante_id")
    if not _texto(candidato_id) or not _texto(vacante_id):
        return _respuesta(400, {"error": "Faltan candidato_id y vacante_id"})
    cambios, mensaje = _validar(datos, parcial=False)
    if mensaje:
        return _respuesta(400, {"error": mensaje})
    if "Item" not in tabla_candidatos().get_item(
        Key={"tenant_id": tenant_id, "candidato_id": candidato_id},
        ProjectionExpression="candidato_id",
    ):
        return _respuesta(404, {"error": "Candidato no encontrado"})
    # Las vacantes viven en RDS (schema del tenant), no en DynamoDB
    if not vacante_existe(tenant_id, vacante_id):
        return _respuesta(404, {"error": "Vacante no encontrada"})
    ahora = _ahora()
    entrevista = {
        "tenant_id": tenant_id,
        "entrevista_id": str(uuid.uuid4()),
        "candidato_id": candidato_id,
        "vacante_id": vacante_id,
        "postulacion_id": datos["postulacion_id"] if _texto(datos.get("postulacion_id")) else "",
        "notas": "",
        **cambios,
        "estado": "agendada",
        "fecha_creacion": ahora,
        "fecha_actualizacion": ahora,
    }
    tabla_entrevistas().put_item(Item=entrevista)
    # Evento asíncrono: si SNS falla se registra el error y se responde 201 igualmente
    publicar_entrevista_agendada(entrevista)
    return _respuesta(201, {"entrevista": entrevista})
