from common.auth import validar_token
from common.dynamo import a_json, tabla_reportes
from common.respuestas import _respuesta


def handler(event, context):
    item, error = validar_token(event)
    if error:
        return error
    clave = {
        "tenant_id": item["tenant_id"],
        "tipo_reporte": (event.get("pathParameters") or {}).get("tipo_reporte"),
    }
    reporte = tabla_reportes().get_item(Key=clave).get("Item")
    if not reporte:
        return _respuesta(404, {"error": "Reporte no encontrado"})
    return _respuesta(200, {"reporte": a_json(reporte)})
