from botocore.exceptions import ClientError

from common.auth import validar_token
from common.candidatos import ahora, obtener_candidato, path_param
from common.dynamo import bucket_cvs, cliente_s3, tabla_candidatos
from common.respuestas import _respuesta, leer_body


# CV en S3 (URL prefirmada: el archivo va directo del navegador a S3)
def handler(event, context):
    item, error = validar_token(event)
    if error:
        return error
    tenant_id = item["tenant_id"]
    candidato_id = path_param(event, "candidato_id")
    datos, error = leer_body(event)
    if error:
        return error
    tabla = tabla_candidatos()

    if datos.get("confirmar"):
        # Paso 3: el frontend confirma que S3 recibió el archivo y guardamos la key
        key = f"{tenant_id}/{candidato_id}/cv.pdf"
        try:
            resultado = tabla.update_item(
                Key={"tenant_id": tenant_id, "candidato_id": candidato_id},
                UpdateExpression="SET cv_url = :k, fecha_actualizacion = :f",
                ExpressionAttributeValues={":k": key, ":f": ahora()},
                ConditionExpression="attribute_exists(candidato_id)",
                ReturnValues="ALL_NEW",
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return _respuesta(404, {"error": "Candidato no encontrado"})
            raise
        return _respuesta(200, {"candidato": resultado["Attributes"]})

    if not obtener_candidato(tenant_id, candidato_id):
        return _respuesta(404, {"error": "Candidato no encontrado"})
    key = f"{tenant_id}/{candidato_id}/cv.pdf"
    url = cliente_s3().generate_presigned_url(
        "put_object",
        # El ContentType debe ir firmado: el navegador debe enviar el mismo header en el PUT
        Params={"Bucket": bucket_cvs(), "Key": key, "ContentType": "application/pdf"},
        ExpiresIn=300,
    )
    return _respuesta(200, {"url_subida": url, "key": key})
