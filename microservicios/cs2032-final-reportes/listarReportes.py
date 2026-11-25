from boto3.dynamodb.conditions import Key

from common.auth import validar_token
from common.dynamo import a_json, tabla_reportes
from common.respuestas import _respuesta

TAMANO_PAGINA = 100


def handler(event, context):
    """Lista los reportes del tenant. ?prefijo=diario_2026-10 filtra por tipo_reporte."""
    item, error = validar_token(event)
    if error:
        return error
    tenant_id = item["tenant_id"]
    parametros = event.get("queryStringParameters") or {}
    condicion = Key("tenant_id").eq(tenant_id)
    if parametros.get("prefijo"):
        condicion = condicion & Key("tipo_reporte").begins_with(parametros["prefijo"])
    consulta = {"KeyConditionExpression": condicion, "Limit": TAMANO_PAGINA}
    if parametros.get("cursor"):
        consulta["ExclusiveStartKey"] = {"tenant_id": tenant_id, "tipo_reporte": parametros["cursor"]}
    resultado = tabla_reportes().query(**consulta)
    return _respuesta(200, a_json({
        "reportes": resultado["Items"],
        "cursor": resultado.get("LastEvaluatedKey", {}).get("tipo_reporte"),
    }))
