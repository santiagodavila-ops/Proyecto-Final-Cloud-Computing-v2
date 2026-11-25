import os

import boto3

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
s3 = boto3.client("s3", region_name="us-east-1")

# Variables de entorno definidas en serverless.yml (provider.environment)
CANDIDATOS_TABLE = os.environ.get("CANDIDATOS_TABLE")
TOKENS_TABLE = os.environ.get("TOKENS_TABLE")
BUCKET_CVS = os.environ.get("BUCKET_CVS")


def tabla_candidatos():
    return dynamodb.Table(os.environ["CANDIDATOS_TABLE"])


def tabla_tokens():
    return dynamodb.Table(os.environ["TOKENS_TABLE"])


def bucket_cvs():
    return os.environ["BUCKET_CVS"]


def cliente_s3():
    return s3
