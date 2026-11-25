import os

import boto3

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

# Variables de entorno definidas en serverless.yml (provider.environment)
USUARIOS_TABLE = os.environ.get("USUARIOS_TABLE")
TOKENS_TABLE = os.environ.get("TOKENS_TABLE")


def tabla_usuarios():
    return dynamodb.Table(os.environ["USUARIOS_TABLE"])


def tabla_tokens():
    return dynamodb.Table(os.environ["TOKENS_TABLE"])


def obtener_usuario(tenant_id, usuario_id):
    # GetItem por la llave (tenant_id, usuario_id) de t_usuarios; None si no existe
    return tabla_usuarios().get_item(
        Key={"tenant_id": tenant_id, "usuario_id": usuario_id}
    ).get("Item")
