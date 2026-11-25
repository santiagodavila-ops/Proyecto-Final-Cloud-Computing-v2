"""Carga datos ficticios: vacantes y postulaciones por tenant.

Uso:
    python3 scripts/cargar_datos.py [stage] [cantidad_por_tenant]
    python3 scripts/cargar_datos.py dev 10000

Las postulaciones apuntan a candidatos reales de t_candidatos-<stage> y a las
vacantes recién creadas, para que Entrevistas y Reportes tengan datos coherentes.

Destino de los datos: en producción vacantes y postulaciones viven en RDS MySQL
(un schema por tenant), pero este script NO escribe en RDS. Escribe en DynamoDB,
que es la fuente de la migración:
    - vacantes       -> t_vacantes-<stage>
    - postulaciones  -> t_postulaciones-<stage>
Después se pasan a RDS con scripts/migrar_a_rds.py (lee esas dos tablas).
Los candidatos siguen en DynamoDB (t_candidatos-<stage>) y solo se leen.
"""
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from faker import Faker

STAGE = sys.argv[1] if len(sys.argv) > 1 else "dev"
CANTIDAD_POR_TENANT = int(sys.argv[2]) if len(sys.argv) > 2 else 10000
TENANTS = ["tenant_1", "tenant_2", "tenant_3"]

AREAS = [
    "Tecnología", "Finanzas", "Marketing", "Ventas", "Recursos Humanos",
    "Operaciones", "Logística", "Legal", "Salud", "Educación",
]
CIUDADES = ["Lima", "Arequipa", "Trujillo", "Cusco", "Piura", "Chiclayo", "Remoto"]
MODALIDADES = ["presencial", "remoto", "hibrido"]
# Distribución realista del pipeline: la mayoría se queda en etapas tempranas
ESTADOS_POSTULACION = ["postulado", "preseleccionado", "entrevista", "oferta", "contratado", "rechazado"]
PESOS_POSTULACION = [35, 20, 15, 7, 8, 15]

fake = Faker("es_ES")
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
tabla_vacantes = dynamodb.Table(f"t_vacantes-{STAGE}")
tabla_postulaciones = dynamodb.Table(f"t_postulaciones-{STAGE}")
tabla_candidatos = dynamodb.Table(f"t_candidatos-{STAGE}")


def ids_candidatos(tenant_id):
    ids, consulta = [], {
        "KeyConditionExpression": Key("tenant_id").eq(tenant_id),
        "ProjectionExpression": "candidato_id",
    }
    while True:
        resp = tabla_candidatos.query(**consulta)
        ids += [item["candidato_id"] for item in resp["Items"]]
        if "LastEvaluatedKey" not in resp:
            return ids
        consulta["ExclusiveStartKey"] = resp["LastEvaluatedKey"]


def fecha_aleatoria(dias_atras):
    return datetime.now(timezone.utc) - timedelta(
        days=random.randint(0, dias_atras), minutes=random.randint(0, 1440)
    )


for tenant_id in TENANTS:
    candidatos = ids_candidatos(tenant_id)
    if not candidatos:
        print(f"{tenant_id}: no hay candidatos, se omiten postulaciones", flush=True)

    vacantes = []
    with tabla_vacantes.batch_writer() as lote:
        for numero in range(1, CANTIDAD_POR_TENANT + 1):
            publicada = fecha_aleatoria(365)
            vacante = {
                "tenant_id": tenant_id,
                "vacante_id": str(uuid.uuid4()),
                "titulo": fake.job(),
                "descripcion": fake.paragraph(nb_sentences=3),
                "area": random.choice(AREAS),
                "ubicacion": random.choice(CIUDADES),
                "modalidad": random.choice(MODALIDADES),
                "salario": Decimal(random.randrange(1200, 15000, 100)),
                "estado": random.choices(["abierta", "cerrada"], [70, 30])[0],
                "fecha_publicacion": publicada.isoformat(),
                "fecha_actualizacion": publicada.isoformat(),
            }
            lote.put_item(Item=vacante)
            vacantes.append(vacante)
            if numero % 2000 == 0:
                print(f"{tenant_id} vacantes: {numero}/{CANTIDAD_POR_TENANT}", flush=True)

    if candidatos:
        with tabla_postulaciones.batch_writer() as lote:
            for numero in range(1, CANTIDAD_POR_TENANT + 1):
                vacante = random.choice(vacantes)
                postulada = fecha_aleatoria(180)
                lote.put_item(Item={
                    "tenant_id": tenant_id,
                    "postulacion_id": str(uuid.uuid4()),
                    "vacante_id": vacante["vacante_id"],
                    "candidato_id": random.choice(candidatos),
                    "titulo_vacante": vacante["titulo"],
                    "estado": random.choices(ESTADOS_POSTULACION, PESOS_POSTULACION)[0],
                    "notas": "",
                    "fecha_postulacion": postulada.isoformat(),
                    "fecha_actualizacion": postulada.isoformat(),
                })
                if numero % 2000 == 0:
                    print(f"{tenant_id} postulaciones: {numero}/{CANTIDAD_POR_TENANT}", flush=True)

    print(f"Carga terminada: {tenant_id}", flush=True)

print("Listo.", flush=True)
