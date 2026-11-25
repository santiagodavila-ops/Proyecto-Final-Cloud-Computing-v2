import json

from botocore.exceptions import ClientError

from common.auth import validar_token
from common.dynamo import a_json, tabla_reportes
from common.respuestas import _respuesta


def handler(event, context):
    """Solo se pueden editar las observaciones; las métricas se recalculan con /reportes/generar."""
    item, error = validar_token(event)
    if error:
        return error
    try:
        datos = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return _respuesta(400, {"error": "El contenido no es JSON válido"})
    if not isinstance(datos, dict) or not isinstance(datos.get("observaciones"), str):
        return _respuesta(400, {"error": "Campo modificable: observaciones (texto)"})
    clave = {
        "tenant_id": item["tenant_id"],
        "tipo_reporte": (event.get("pathParameters") or {}).get("tipo_reporte"),
    }
    try:
        resultado = tabla_reportes().update_item(
            Key=clave,
            UpdateExpression="SET observaciones = :o",
            ExpressionAttributeValues={":o": datos["observaciones"].strip()},
            ConditionExpression="attribute_exists(tipo_reporte)",
            ReturnValues="ALL_NEW",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return _respuesta(404, {"error": "Reporte no encontrado"})
        raise
    return _respuesta(200, {"mensaje": "Reporte modificado", "reporte": a_json(resultado["Attributes"])})
