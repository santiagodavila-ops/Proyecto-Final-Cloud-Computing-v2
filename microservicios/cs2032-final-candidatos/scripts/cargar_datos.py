"""Carga candidatos ficticios por tenant.

Uso:
    python3 scripts/cargar_datos.py [stage] [cantidad_por_tenant]
    python3 scripts/cargar_datos.py dev 10000

Este script debe correr antes que Vacantes y Entrevistas: sus postulaciones
y entrevistas apuntan a candidato_id reales de t_candidatos-<stage>.
"""
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone

import boto3
from faker import Faker

STAGE = sys.argv[1] if len(sys.argv) > 1 else "dev"
CANTIDAD_POR_TENANT = int(sys.argv[2]) if len(sys.argv) > 2 else 10000
TENANTS = ["tenant_1", "tenant_2", "tenant_3"]

fake = Faker("es_ES")
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
tabla_candidatos = dynamodb.Table(f"t_candidatos-{STAGE}")


def fecha_aleatoria(dias_atras):
    return datetime.now(timezone.utc) - timedelta(
        days=random.randint(0, dias_atras), minutes=random.randint(0, 1440)
    )


for tenant_id in TENANTS:
    with tabla_candidatos.batch_writer() as lote:
        for numero in range(1, CANTIDAD_POR_TENANT + 1):
            registro = fecha_aleatoria(730)
            lote.put_item(Item={
                "tenant_id": tenant_id,
                "candidato_id": str(uuid.uuid4()),
                "nombre": fake.name(),
                "email": fake.unique.email(),
                "telefono": f"9{random.randint(10000000, 99999999)}",
                "profesion": fake.job(),
                "cv_url": "",
                "estado": random.choices(["activo", "inactivo"], [90, 10])[0],
                "fecha_registro": registro.isoformat(),
                "fecha_actualizacion": registro.isoformat(),
            })
            if numero % 2000 == 0:
                print(f"{tenant_id} candidatos: {numero}/{CANTIDAD_POR_TENANT}", flush=True)
    print(f"Carga terminada: {tenant_id}", flush=True)

print("Listo.", flush=True)
