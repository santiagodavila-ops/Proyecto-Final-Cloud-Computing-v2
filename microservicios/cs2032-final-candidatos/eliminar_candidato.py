from botocore.exceptions import ClientError

from common.auth import validar_token
from common.candidatos import path_param
from common.dynamo import tabla_candidatos
from common.respuestas import _respuesta


def handler(event, context):
    item, error = validar_token(event)
    if error:
        return error
    try:
        tabla_candidatos().delete_item(
            Key={"tenant_id": item["tenant_id"], "candidato_id": path_param(event, "candidato_id")},
            ConditionExpression="attribute_exists(candidato_id)",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return _respuesta(404, {"error": "Candidato no encontrado"})
        raise
    return _respuesta(200, {"mensaje": "Candidato eliminado"})
