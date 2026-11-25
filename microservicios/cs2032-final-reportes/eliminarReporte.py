from botocore.exceptions import ClientError

from common.auth import validar_token
from common.dynamo import tabla_reportes
from common.respuestas import _respuesta


def handler(event, context):
    item, error = validar_token(event)
    if error:
        return error
    clave = {
        "tenant_id": item["tenant_id"],
        "tipo_reporte": (event.get("pathParameters") or {}).get("tipo_reporte"),
    }
    try:
        tabla_reportes().delete_item(
            Key=clave,
            ConditionExpression="attribute_exists(tipo_reporte)",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return _respuesta(404, {"error": "Reporte no encontrado"})
        raise
    return _respuesta(200, {"mensaje": "Reporte eliminado"})
