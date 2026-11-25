import base64

from boto3.dynamodb.conditions import Attr, Key

from common.auth import validar_token
from common.dynamo import tabla_entrevistas
from common.entrevistas import ESTADOS, TAMANO_PAGINA, _respuesta


def handler(event, context):
    """Filtros opcionales: ?estado=, ?candidato_id=, ?vacante_id=, paginado con ?cursor=."""
    item, error = validar_token(event)
    if error:
        return error
    tenant_id = item["tenant_id"]
    parametros = event.get("queryStringParameters") or {}
    if parametros.get("estado") and parametros["estado"] not in ESTADOS:
        return _respuesta(400, {"error": f"estado debe ser uno de {list(ESTADOS)}"})
    consulta = {
        "KeyConditionExpression": Key("tenant_id").eq(tenant_id),
        "Limit": TAMANO_PAGINA,
    }
    filtro = None
    for campo in ("estado", "candidato_id", "vacante_id"):
        if parametros.get(campo):
            condicion = Attr(campo).eq(parametros[campo])
            filtro = condicion if filtro is None else filtro & condicion
    if filtro is not None:
        consulta["FilterExpression"] = filtro
    if parametros.get("cursor"):
        try:
            consulta["ExclusiveStartKey"] = {
                "tenant_id": tenant_id,
                "entrevista_id": base64.urlsafe_b64decode(parametros["cursor"].encode()).decode(),
            }
        except (ValueError, TypeError):
            return _respuesta(400, {"error": "cursor inválido"})
    resultado = tabla_entrevistas().query(**consulta)
    siguiente = resultado.get("LastEvaluatedKey", {}).get("entrevista_id")
    return _respuesta(200, {
        "entrevistas": resultado["Items"],
        "cursor": base64.urlsafe_b64encode(siguiente.encode()).decode() if siguiente else None,
    })
