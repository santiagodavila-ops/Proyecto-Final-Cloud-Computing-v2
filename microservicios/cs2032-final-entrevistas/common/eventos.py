"""Publicación de eventos del servicio de entrevistas en SNS (arquitectura basada en eventos)."""
import json
import os

import boto3

sns = boto3.client("sns", region_name="us-east-1")

# Campos de la entrevista que viajan en el evento (nombres reales del código)
CAMPOS_EVENTO = (
    "tenant_id",
    "entrevista_id",
    "candidato_id",
    "vacante_id",
    "fecha_hora",
    "modalidad",
    "entrevistador",
)


def publicar_entrevista_agendada(item):
    """Publica el evento entrevista_agendada. Devuelve True si se publicó, False si falló.

    No lanza excepciones: la entrevista ya está guardada y un fallo de SNS
    no debe romper la petición del cliente.
    """
    try:
        mensaje = {"evento": "entrevista_agendada"}
        for campo in CAMPOS_EVENTO:
            if item.get(campo):
                mensaje[campo] = item[campo]
        sns.publish(
            TopicArn=os.environ["TOPICO_ENTREVISTAS_ARN"],
            Message=json.dumps(mensaje),
            Subject="entrevista_agendada",
        )
        return True
    except Exception as e:
        print(json.dumps({
            "nivel": "ERROR",
            "mensaje": "No se pudo publicar entrevista_agendada en SNS",
            "entrevista_id": item.get("entrevista_id"),
            "error": str(e),
        }))
        return False
