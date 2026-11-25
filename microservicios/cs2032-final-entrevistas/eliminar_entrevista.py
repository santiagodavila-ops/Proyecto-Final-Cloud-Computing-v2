from botocore.exceptions import ClientError

from common.auth import validar_token
from common.dynamo import tabla_entrevistas
from common.entrevistas import _clave, _respuesta


def handler(event, context):
    item, error = validar_token(event)
    if error:
        return error
    try:
        tabla_entrevistas().delete_item(
            Key=_clave(event, item["tenant_id"]),
            ConditionExpression="attribute_exists(entrevista_id)",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return _respuesta(404, {"error": "Entrevista no encontrada"})
        raise
    return _respuesta(200, {"mensaje": "Entrevista eliminada"})
