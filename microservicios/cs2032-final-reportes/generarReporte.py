from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal

from boto3.dynamodb.conditions import Key

from common.auth import validar_token
from common.dynamo import (
    a_json,
    tabla_candidatos,
    tabla_entrevistas,
    tabla_reportes,
    tabla_usuarios,
)
from common.rds import contar_por_estado
from common.respuestas import _respuesta

RESUMEN_GENERAL = "resumen_general"


def _contar(tabla, tenant_id):
    """Cuenta los ítems de un tenant (Query por partition key, recorriendo todas las páginas)."""
    consulta = {"KeyConditionExpression": Key("tenant_id").eq(tenant_id), "Select": "COUNT"}
    total = 0
    while True:
        resp = tabla.query(**consulta)
        total += resp["Count"]
        if "LastEvaluatedKey" not in resp:
            return total
        consulta["ExclusiveStartKey"] = resp["LastEvaluatedKey"]


def _contar_por(tabla, tenant_id, campo):
    """Cuenta los ítems de un tenant agrupados por el valor de `campo`."""
    consulta = {
        "KeyConditionExpression": Key("tenant_id").eq(tenant_id),
        "ProjectionExpression": "#campo",
        "ExpressionAttributeNames": {"#campo": campo},
    }
    conteo = Counter()
    while True:
        resp = tabla.query(**consulta)
        conteo.update(item.get(campo, "sin_valor") for item in resp["Items"])
        if "LastEvaluatedKey" not in resp:
            return dict(conteo)
        consulta["ExclusiveStartKey"] = resp["LastEvaluatedKey"]


def handler(event, context):
    """Recalcula el resumen general del tenant leyendo RDS (vacantes y postulaciones) y las tablas DynamoDB de los otros microservicios."""
    item, error = validar_token(event)
    if error:
        return error
    tenant_id = item["tenant_id"]
    vacantes = contar_por_estado(tenant_id, "vacantes")
    postulaciones = contar_por_estado(tenant_id, "postulaciones")
    entrevistas = _contar_por(tabla_entrevistas(), tenant_id, "estado")
    total_postulaciones = sum(postulaciones.values())
    total_contratados = postulaciones.get("contratado", 0)
    tasa = round(total_contratados * 100 / total_postulaciones, 2) if total_postulaciones else 0
    reporte = {
        "tenant_id": tenant_id,
        "tipo_reporte": RESUMEN_GENERAL,
        "total_usuarios": _contar(tabla_usuarios(), tenant_id),
        "total_candidatos": _contar(tabla_candidatos(), tenant_id),
        "total_vacantes": sum(vacantes.values()),
        "vacantes_por_estado": vacantes,
        "total_postulaciones": total_postulaciones,
        "postulaciones_por_estado": postulaciones,
        "total_entrevistas": sum(entrevistas.values()),
        "entrevistas_por_estado": entrevistas,
        "total_contratados": total_contratados,
        "tasa_contratacion": Decimal(str(tasa)),
        "observaciones": "",
        "fecha_actualizacion": datetime.now(timezone.utc).isoformat(),
    }
    tabla_reportes().put_item(Item=reporte)
    return _respuesta(201, {"reporte": a_json(reporte)})
