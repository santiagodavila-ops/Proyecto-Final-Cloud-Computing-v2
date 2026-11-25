import os

import boto3

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

# Variables de entorno definidas en serverless.yml (provider.environment)
CANDIDATOS_TABLE = os.environ.get("CANDIDATOS_TABLE")
TOKENS_TABLE = os.environ.get("TOKENS_TABLE")


def tabla_candidatos():
    # Solo lectura: se usa para verificar que el candidato existe
    return dynamodb.Table(os.environ["CANDIDATOS_TABLE"])


def tabla_tokens():
    return dynamodb.Table(os.environ["TOKENS_TABLE"])
