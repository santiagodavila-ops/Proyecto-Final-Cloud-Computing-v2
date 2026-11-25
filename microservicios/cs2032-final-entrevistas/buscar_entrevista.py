from common.auth import validar_token
from common.dynamo import tabla_entrevistas
from common.entrevistas import _clave, _respuesta


def handler(event, context):
    item, error = validar_token(event)
    if error:
        return error
    entrevista = tabla_entrevistas().get_item(Key=_clave(event, item["tenant_id"])).get("Item")
    if not entrevista:
        return _respuesta(404, {"error": "Entrevista no encontrada"})
    return _respuesta(200, {"entrevista": entrevista})
