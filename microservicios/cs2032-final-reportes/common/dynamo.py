import os
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key  # noqa: F401  (re-exportado para los handlers)

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

# Variables de entorno definidas en serverless.yml (provider.environment)
REPORTES_TABLE = os.environ.get("REPORTES_TABLE")
TOKENS_TABLE = os.environ.get("TOKENS_TABLE")
USUARIOS_TABLE = os.environ.get("USUARIOS_TABLE")
CANDIDATOS_TABLE = os.environ.get("CANDIDATOS_TABLE")
ENTREVISTAS_TABLE = os.environ.get("ENTREVISTAS_TABLE")


def tabla_reportes():
    return dynamodb.Table(os.environ["REPORTES_TABLE"])


def tabla_tokens():
    return dynamodb.Table(os.environ["TOKENS_TABLE"])


# Tablas de otros microservicios (solo lectura)
def tabla_usuarios():
    return dynamodb.Table(os.environ["USUARIOS_TABLE"])


def tabla_candidatos():
    return dynamodb.Table(os.environ["CANDIDATOS_TABLE"])


def tabla_entrevistas():
    return dynamodb.Table(os.environ["ENTREVISTAS_TABLE"])


def a_json(valor):
    """Convierte los Decimal de DynamoDB a int/float (common.respuestas no los serializa)."""
    if isinstance(valor, Decimal):
        return int(valor) if valor % 1 == 0 else float(valor)
    if isinstance(valor, dict):
        return {k: a_json(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [a_json(v) for v in valor]
    return valor
