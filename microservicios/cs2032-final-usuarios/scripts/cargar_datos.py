"""Completa la tabla de usuarios del CRM hasta 10 000 registros por empresa."""
import hashlib
import secrets
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import partial
from itertools import count, islice

import boto3
from faker import Faker
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, PartialCredentialsError

REGION = "us-east-1"
STAGE = sys.argv[1] if len(sys.argv) > 1 else "dev"
TABLA = f"t_usuarios-{STAGE}"
EMPRESAS = ("tenant_1", "tenant_2", "tenant_3")
META = int(sys.argv[2]) if len(sys.argv) > 2 else 10_000
if META < 1:
    raise SystemExit("La meta por tenant debe ser mayor que cero.")


def leer_usuarios(db):
    identificadores = {empresa: set() for empresa in EMPRESAS}
    correos = set()
    paginas = db.get_paginator("scan").paginate(
        TableName=TABLA,
        ProjectionExpression="#t, #u, #e",
        ExpressionAttributeNames={"#t": "tenant_id", "#u": "usuario_id", "#e": "email"},
        ConsistentRead=True,
    )
    for pagina in paginas:
        for fila in pagina["Items"]:
            empresa = fila["tenant_id"]["S"]
            if empresa in identificadores:
                identificadores[empresa].add(fila["usuario_id"]["S"])
            correo = fila.get("email", {}).get("S", "").strip().lower()
            if correo:
                correos.add(correo)
    return identificadores, correos


def cuentas_disponibles(empresa, identificadores, correos):
    nombres = Faker("es_ES")
    for numero in count(1):
        email = f"carga.{empresa}.{numero:05d}@usuarios.cs2032.test"
        usuario_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, email))
        if usuario_id not in identificadores and email not in correos:
            yield empresa, nombres.name(), email, usuario_id


def hash_ficticio():
    # Mismo formato que common/passwords.py. Cada cuenta tiene su propia clave aleatoria.
    clave = secrets.token_urlsafe(32).encode("utf-8")
    sal = secrets.token_bytes(16)
    resumen = hashlib.pbkdf2_hmac("sha256", clave, sal, 310_000)
    return f"pbkdf2_sha256$310000${sal.hex()}${resumen.hex()}"


def insertar(db, cuenta):
    empresa, nombre, email, usuario_id = cuenta
    usuario = {
        "tenant_id": empresa,
        "usuario_id": usuario_id,
        "nombre": nombre,
        "email": email,
        "password_hash": hash_ficticio(),
        "rol": "reclutador",
        "fecha_registro": datetime.now(timezone.utc).isoformat(),
    }
    try:
        db.put_item(
            TableName=TABLA,
            Item={campo: {"S": valor} for campo, valor in usuario.items()},
            ConditionExpression="attribute_not_exists(#t)",
            ExpressionAttributeNames={"#t": "tenant_id"},
        )
    except db.exceptions.ConditionalCheckFailedException:
        # Otra ejecución ya insertó la misma cuenta.
        return 0
    return 1


def cargar():
    db = boto3.client("dynamodb", region_name=REGION, config=Config(
        retries={"mode": "standard", "max_attempts": 8}
    ))
    tabla = db.describe_table(TableName=TABLA)["Table"]
    print(f"Destino: {tabla['TableArn']}", flush=True)
    esquema = {clave["KeyType"]: clave["AttributeName"] for clave in tabla["KeySchema"]}
    if esquema != {"HASH": "tenant_id", "RANGE": "usuario_id"}:
        raise SystemExit("La tabla tiene claves distintas de tenant_id y usuario_id. Carga detenida.")

    guardados, correos = leer_usuarios(db)
    for empresa in EMPRESAS:
        actuales = len(guardados[empresa])
        print(f"{empresa}: {actuales} existentes, faltan {max(0, META - actuales)}.", flush=True)

    for empresa in EMPRESAS:
        faltan = max(0, META - len(guardados[empresa]))
        posibles = cuentas_disponibles(empresa, guardados[empresa], correos)
        pendientes = islice(posibles, faltan)
        nuevas = 0
        with ThreadPoolExecutor(max_workers=2) as equipo:
            guardar = partial(insertar, db)
            while lote := list(islice(pendientes, 100)):
                nuevas += sum(equipo.map(guardar, lote))
                print(f"{empresa}: {nuevas} nuevas en esta ejecución.", flush=True)

    finales, _ = leer_usuarios(db)
    print("\nRecuento final leído de DynamoDB:")
    for empresa, ids in finales.items():
        print(f"  {empresa}: {len(ids)}")
    if any(len(ids) < META for ids in finales.values()):
        raise SystemExit("La carga quedó incompleta. Vuelve a ejecutar el mismo archivo para continuar.")
    print(f"CARGA VERIFICADA: {sum(map(len, finales.values()))} usuarios en las tres empresas.")


if __name__ == "__main__":
    try:
        cargar()
    except (NoCredentialsError, PartialCredentialsError):
        sys.exit("La VM no tiene credenciales AWS activas. Revisa el rol IAM de la instancia o renueva la sesión del laboratorio y repite la carga.")
    except ClientError as error:
        detalle = error.response["Error"]
        sys.exit(f"AWS devolvió {detalle['Code']}: {detalle['Message']}")
    except BotoCoreError as error:
        sys.exit(f"No se pudo completar la conexión con AWS: {error}")
