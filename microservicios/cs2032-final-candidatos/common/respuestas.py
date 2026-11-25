import json
from decimal import Decimal


def _a_numero(valor):
    """DynamoDB devuelve números como Decimal, que json no serializa."""
    if isinstance(valor, Decimal):
        return int(valor) if valor == valor.to_integral_value() else float(valor)
    raise TypeError(f"Tipo no serializable: {type(valor).__name__}")


def _respuesta(codigo, datos):
    return {
        "statusCode": codigo,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(datos, default=_a_numero),
    }


def leer_body(event):
    """Devuelve (datos, error). Valida que el body sea un objeto JSON."""
    try:
        datos = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return None, _respuesta(400, {"error": "El contenido no es JSON válido"})
    if not isinstance(datos, dict):
        return None, _respuesta(400, {"error": "Se esperaba un objeto JSON"})
    return datos, None


def texto(valor):
    return isinstance(valor, str) and valor.strip() != ""
