from botocore.exceptions import ClientError

from common.auth import validar_token
from common.dynamo import tabla_entrevistas
from common.entrevistas import _ahora, _clave, _leer_body, _respuesta, _validar


def handler(event, context):
    item, error = validar_token(event)
    if error:
        return error
    tenant_id = item["tenant_id"]
    datos, error = _leer_body(event)
    if error:
        return error
    cambios, mensaje = _validar(datos, parcial=True)
    if mensaje:
        return _respuesta(400, {"error": mensaje})
    if not cambios:
        return _respuesta(400, {"error": "Campos modificables: entrevistador, fecha_hora, modalidad, estado, notas"})
    cambios["fecha_actualizacion"] = _ahora()
    nombres, valores, asignaciones = {}, {}, []
    for numero, (campo, valor) in enumerate(cambios.items()):
        nombres[f"#c{numero}"] = campo
        valores[f":v{numero}"] = valor
        asignaciones.append(f"#c{numero} = :v{numero}")
    try:
        resultado = tabla_entrevistas().update_item(
            Key=_clave(event, tenant_id),
            UpdateExpression="SET " + ", ".join(asignaciones),
            ExpressionAttributeNames=nombres,
            ExpressionAttributeValues=valores,
            ConditionExpression="attribute_exists(entrevista_id)",
            ReturnValues="ALL_NEW",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return _respuesta(404, {"error": "Entrevista no encontrada"})
        raise
    return _respuesta(200, {"mensaje": "Entrevista modificada", "entrevista": resultado["Attributes"]})
