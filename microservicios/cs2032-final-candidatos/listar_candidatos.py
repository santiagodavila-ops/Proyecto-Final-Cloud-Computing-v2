from boto3.dynamodb.conditions import Key

from common.auth import validar_token
from common.candidatos import TAMANO_PAGINA
from common.dynamo import tabla_candidatos
from common.respuestas import _respuesta


def handler(event, context):
    item, error = validar_token(event)
    if error:
        return error
    tenant_id = item["tenant_id"]
    consulta = {
        "KeyConditionExpression": Key("tenant_id").eq(tenant_id),
        "Limit": TAMANO_PAGINA,
    }
    ultimo_id = (event.get("queryStringParameters") or {}).get("ultimo_id")
    if ultimo_id:
        # Nunca se pagina dentro de otro tenant: la clave de inicio lleva el tenant del token
        consulta["ExclusiveStartKey"] = {"tenant_id": tenant_id, "candidato_id": ultimo_id}
    resultado = tabla_candidatos().query(**consulta)
    clave = resultado.get("LastEvaluatedKey")
    return _respuesta(200, {
        "candidatos": resultado["Items"],
        "ultimo_id": clave["candidato_id"] if clave else None,
    })
