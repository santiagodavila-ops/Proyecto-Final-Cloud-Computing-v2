import json

from common.entrevistas import _ahora


def _procesar_registro(registro):
    # El body llega envuelto por SNS (raw message delivery desactivado)
    sobre = json.loads(registro["body"])
    mensaje = json.loads(sobre["Message"])
    if mensaje.get("evento") != "entrevista_agendada":
        raise ValueError(f"Evento no soportado: {mensaje.get('evento')}")
    # Simulación del recordatorio: NO se envían correos reales
    for destinatario, rol in (
        (mensaje.get("candidato_id"), "candidato"),
        (mensaje.get("entrevistador"), "entrevistador"),
    ):
        print(json.dumps({
            "accion": "recordatorio_simulado",
            "destinatario_rol": rol,
            "destinatario": destinatario,
            "tenant_id": mensaje.get("tenant_id"),
            "entrevista_id": mensaje.get("entrevista_id"),
            "vacante_id": mensaje.get("vacante_id"),
            "fecha_hora": mensaje.get("fecha_hora"),
            "modalidad": mensaje.get("modalidad"),
            "procesado_en": _ahora(),
        }))


def handler(event, context):
    # ReportBatchItemFailures: solo los registros fallidos vuelven a la cola
    fallidos = []
    for registro in event.get("Records", []):
        try:
            _procesar_registro(registro)
        except Exception as e:
            print(json.dumps({
                "nivel": "ERROR",
                "message_id": registro.get("messageId"),
                "error": str(e),
            }))
            fallidos.append({"itemIdentifier": registro["messageId"]})
    return {"batchItemFailures": fallidos}
