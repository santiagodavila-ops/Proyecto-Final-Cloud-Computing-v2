"""Helpers propios del servicio de entrevistas (validaciones y respuesta con Decimal)."""
import json
from datetime import datetime, timezone
from decimal import Decimal

MODALIDADES = ("presencial", "virtual")
ESTADOS = ("agendada", "realizada", "cancelada")
TAMANO_PAGINA = 100


def _json_default(valor):
    if isinstance(valor, Decimal):
        return int(valor) if valor % 1 == 0 else float(valor)
    return str(valor)


def _respuesta(codigo, datos):
    # DynamoDB devuelve Decimal: se serializa con _json_default
    return {
        "statusCode": codigo,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(datos, default=_json_default),
    }


def _ahora():
    return datetime.now(timezone.utc).isoformat()


def _leer_body(event):
    try:
        datos = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return None, _respuesta(400, {"error": "El contenido no es JSON válido"})
    if not isinstance(datos, dict):
        return None, _respuesta(400, {"error": "Se esperaba un objeto JSON"})
    return datos, None


def _clave(event, tenant_id):
    return {
        "tenant_id": tenant_id,
        "entrevista_id": (event.get("pathParameters") or {}).get("entrevista_id"),
    }


def _texto(valor):
    return isinstance(valor, str) and valor.strip() != ""


def _fecha_valida(valor):
    if not _texto(valor):
        return False
    try:
        datetime.fromisoformat(valor)
    except ValueError:
        return False
    return True


def _validar(datos, parcial):
    """Devuelve (cambios_limpios, mensaje_error)."""
    cambios = {}
    for campo in ("entrevistador", "notas"):
        if campo in datos:
            if not isinstance(datos[campo], str) or (campo == "entrevistador" and not _texto(datos[campo])):
                return None, f"Valor inválido para {campo}"
            cambios[campo] = datos[campo].strip()
        elif not parcial and campo == "entrevistador":
            return None, "Falta un valor válido para entrevistador"
    if "fecha_hora" in datos or not parcial:
        if not _fecha_valida(datos.get("fecha_hora")):
            return None, "fecha_hora debe tener formato ISO 8601 (ej. 2026-11-20T15:00:00-05:00)"
        cambios["fecha_hora"] = datos["fecha_hora"]
    if "modalidad" in datos or not parcial:
        if datos.get("modalidad") not in MODALIDADES:
            return None, f"modalidad debe ser uno de {list(MODALIDADES)}"
        cambios["modalidad"] = datos["modalidad"]
    if "estado" in datos:
        if not parcial:
            return None, "Una entrevista nueva siempre se crea agendada"
        if datos["estado"] not in ESTADOS:
            return None, f"estado debe ser uno de {list(ESTADOS)}"
        cambios["estado"] = datos["estado"]
    return cambios, None
