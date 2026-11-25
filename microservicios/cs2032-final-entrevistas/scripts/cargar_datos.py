"""Carga entrevistas ficticias a partir de postulaciones reales.

Uso:
    python3 scripts/cargar_datos.py [stage] [cantidad_por_tenant]
    python3 scripts/cargar_datos.py dev 10000

Requiere que Vacantes/Postulaciones ya tenga datos en t_postulaciones-<stage>.
"""
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone

import boto3
from boto3.dynamodb.conditions import Key
from faker import Faker

STAGE = sys.argv[1] if len(sys.argv) > 1 else "dev"
CANTIDAD_POR_TENANT = int(sys.argv[2]) if len(sys.argv) > 2 else 10000
TENANTS = ["tenant_1", "tenant_2", "tenant_3"]

fake = Faker("es_ES")
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
tabla_entrevistas = dynamodb.Table(f"t_entrevistas-{STAGE}")
tabla_postulaciones = dynamodb.Table(f"t_postulaciones-{STAGE}")


def postulaciones(tenant_id):
    items, consulta = [], {
        "KeyConditionExpression": Key("tenant_id").eq(tenant_id),
        "ProjectionExpression": "postulacion_id, candidato_id, vacante_id",
    }
    while True:
        resp = tabla_postulaciones.query(**consulta)
        items += resp["Items"]
        if "LastEvaluatedKey" not in resp:
            return items
        consulta["ExclusiveStartKey"] = resp["LastEvaluatedKey"]


for tenant_id in TENANTS:
    base = postulaciones(tenant_id)
    if not base:
        print(f"{tenant_id}: no hay postulaciones, se omite", flush=True)
        continue
    entrevistadores = [fake.name() for _ in range(40)]
    with tabla_entrevistas.batch_writer() as lote:
        for numero in range(1, CANTIDAD_POR_TENANT + 1):
            postulacion = random.choice(base)
            fecha_hora = datetime.now(timezone.utc) + timedelta(
                days=random.randint(-180, 30), hours=random.randint(8, 18)
            )
            # Las entrevistas pasadas están realizadas o canceladas; las futuras, agendadas
            if fecha_hora > datetime.now(timezone.utc):
                estado = "agendada"
            else:
                estado = random.choices(["realizada", "cancelada"], [85, 15])[0]
            creada = (fecha_hora - timedelta(days=random.randint(1, 14))).isoformat()
            lote.put_item(Item={
                "tenant_id": tenant_id,
                "entrevista_id": str(uuid.uuid4()),
                "candidato_id": postulacion["candidato_id"],
                "vacante_id": postulacion["vacante_id"],
                "postulacion_id": postulacion["postulacion_id"],
                "entrevistador": random.choice(entrevistadores),
                "fecha_hora": fecha_hora.replace(minute=0, second=0, microsecond=0).isoformat(),
                "modalidad": random.choice(["presencial", "virtual"]),
                "estado": estado,
                "notas": fake.sentence() if estado == "realizada" else "",
                "fecha_creacion": creada,
                "fecha_actualizacion": creada,
            })
            if numero % 2000 == 0:
                print(f"{tenant_id}: {numero}/{CANTIDAD_POR_TENANT}", flush=True)
    print(f"Carga terminada: {tenant_id}", flush=True)

print("Listo.", flush=True)
