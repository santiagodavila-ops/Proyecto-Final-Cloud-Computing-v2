"""Helpers propios del servicio de vacantes/postulaciones (no son parte del contrato de auth)."""
from datetime import datetime, timezone
from decimal import Decimal

from common.respuestas import _respuesta, texto

ESTADOS_VACANTE = ("abierta", "cerrada")
MODALIDADES_VACANTE = ("presencial", "remoto", "hibrido")
# Pipeline de la postulación (la "oportunidad" del CRM)
ESTADOS_POSTULACION = (
    "postulado",
    "preseleccionado",
    "entrevista",
    "oferta",
    "contratado",
    "rechazado",
)


def ahora():
    return datetime.now(timezone.utc).isoformat()


def respuesta(codigo, datos):
    """Como common.respuestas._respuesta, pero convierte los Decimal de DynamoDB a int/float."""
    return _respuesta(codigo, _sin_decimales(datos))


def _sin_decimales(valor):
    if isinstance(valor, Decimal):
        return int(valor) if valor % 1 == 0 else float(valor)
    if isinstance(valor, dict):
        return {k: _sin_decimales(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_sin_decimales(v) for v in valor]
    return valor


def path_param(event, nombre):
    return (event.get("pathParameters") or {}).get(nombre)


def validar_vacante(datos, parcial):
    """Devuelve (cambios_limpios, mensaje_error)."""
    cambios = {}
    for campo in ("titulo", "descripcion", "area", "ubicacion"):
        if campo in datos:
            if not texto(datos[campo]):
                return None, f"Valor inválido para {campo}"
            cambios[campo] = datos[campo].strip()
        elif not parcial and campo in ("titulo", "descripcion"):
            return None, f"Falta un valor válido para {campo}"
    if "modalidad" in datos:
        if datos["modalidad"] not in MODALIDADES_VACANTE:
            return None, f"modalidad debe ser uno de {list(MODALIDADES_VACANTE)}"
        cambios["modalidad"] = datos["modalidad"]
    if "salario" in datos:
        salario = datos["salario"]
        if isinstance(salario, bool) or not isinstance(salario, (int, float)) or salario < 0:
            return None, "salario debe ser un número positivo"
        cambios["salario"] = Decimal(str(salario))
    if "estado" in datos:
        if not parcial:
            return None, "Una vacante nueva siempre se crea abierta"
        if datos["estado"] not in ESTADOS_VACANTE:
            return None, f"estado debe ser uno de {list(ESTADOS_VACANTE)}"
        cambios["estado"] = datos["estado"]
    return cambios, None


def existe_candidato(tenant_id, candidato_id):
    from common.dynamo import tabla_candidatos
    return "Item" in tabla_candidatos().get_item(
        Key={"tenant_id": tenant_id, "candidato_id": candidato_id},
        ProjectionExpression="candidato_id",
    )
