"""Helpers de negocio compartidos por las funciones del servicio de candidatos."""
from datetime import datetime, timezone

from common.dynamo import tabla_candidatos
from common.respuestas import texto

ESTADOS_CANDIDATO = ("activo", "inactivo")
TAMANO_PAGINA = 100
CAMPOS_EDITABLES = ("nombre", "email", "telefono", "profesion", "estado")


def ahora():
    return datetime.now(timezone.utc).isoformat()


def path_param(event, nombre):
    return (event.get("pathParameters") or {}).get(nombre)


def validar_candidato(datos, parcial):
    """Devuelve (cambios_limpios, mensaje_error)."""
    cambios = {}
    for campo in ("nombre", "email", "telefono", "profesion"):
        if campo in datos:
            if not texto(datos[campo]):
                return None, f"Valor inválido para {campo}"
            cambios[campo] = datos[campo].strip()
        elif not parcial:
            return None, f"Falta {campo}"
    if "email" in cambios and "@" not in cambios["email"]:
        return None, "email no tiene un formato válido"
    if "estado" in datos:
        if datos["estado"] not in ESTADOS_CANDIDATO:
            return None, f"estado debe ser uno de {list(ESTADOS_CANDIDATO)}"
        cambios["estado"] = datos["estado"]
    return cambios, None


def obtener_candidato(tenant_id, candidato_id):
    return tabla_candidatos().get_item(
        Key={"tenant_id": tenant_id, "candidato_id": candidato_id}
    ).get("Item")
