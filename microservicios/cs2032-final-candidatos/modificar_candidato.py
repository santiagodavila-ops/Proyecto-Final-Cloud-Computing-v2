from botocore.exceptions import ClientError

from common.auth import validar_token
from common.candidatos import ahora, path_param, validar_candidato
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
    cambios, mensaje = validar_candidato(datos, parcial=True)
    if mensaje:
        return _respuesta(400, {"error": mensaje})
    if not cambios:
        return _respuesta(400, {"error": "No hay campos para modificar"})
    cambios["fecha_actualizacion"] = ahora()
    nombres = {f"#c{n}": campo for n, campo in enumerate(cambios)}
    valores = {f":v{n}": valor for n, valor in enumerate(cambios.values())}
    asignaciones = [f"#c{n} = :v{n}" for n in range(len(cambios))]
    try:
        resultado = tabla_candidatos().update_item(
            Key={"tenant_id": tenant_id, "candidato_id": path_param(event, "candidato_id")},
            UpdateExpression="SET " + ", ".join(asignaciones),
            ExpressionAttributeNames=nombres,
            ExpressionAttributeValues=valores,
            ConditionExpression="attribute_exists(candidato_id)",
            ReturnValues="ALL_NEW",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return _respuesta(404, {"error": "Candidato no encontrado"})
        raise
    return _respuesta(200, {"candidato": resultado["Attributes"]})
