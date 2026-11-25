"""Carga reportes históricos ficticios: métricas diarias por área.

Uso:
    python3 scripts/cargar_datos.py [stage] [cantidad_por_tenant]
    python3 scripts/cargar_datos.py dev 10000

Cada ítem es un reporte con tipo_reporte = diario_<AAAA-MM-DD>_<area>,
por ejemplo diario_2026-10-15_tecnologia. 20 áreas x 500 días = 10,000 por tenant.
El reporte "resumen_general" no se carga aquí: se calcula con POST /reportes/generar.
"""
import random
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import boto3

STAGE = sys.argv[1] if len(sys.argv) > 1 else "dev"
CANTIDAD_POR_TENANT = int(sys.argv[2]) if len(sys.argv) > 2 else 10000
TENANTS = ["tenant_1", "tenant_2", "tenant_3"]
AREAS = [
    "tecnologia", "finanzas", "marketing", "ventas", "recursos_humanos",
    "operaciones", "logistica", "legal", "salud", "educacion",
    "administracion", "atencion_cliente", "ingenieria", "produccion", "calidad",
    "compras", "diseno", "datos", "seguridad", "comunicaciones",
]

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
tabla = dynamodb.Table(f"t_reportes-{STAGE}")
dias = -(-CANTIDAD_POR_TENANT // len(AREAS))
hoy = date.today()

for tenant_id in TENANTS:
    numero = 0
    with tabla.batch_writer() as lote:
        for desfase in range(1, dias + 1):
            fecha = (hoy - timedelta(days=desfase)).isoformat()
            for area in AREAS:
                if numero == CANTIDAD_POR_TENANT:
                    break
                postulaciones = random.randint(0, 40)
                entrevistas = random.randint(0, postulaciones)
                contratados = random.randint(0, entrevistas // 3)
                lote.put_item(Item={
                    "tenant_id": tenant_id,
                    "tipo_reporte": f"diario_{fecha}_{area}",
                    "fecha": fecha,
                    "area": area,
                    "nuevos_candidatos": random.randint(0, 60),
                    "nuevas_vacantes": random.randint(0, 8),
                    "total_postulaciones": postulaciones,
                    "total_entrevistas": entrevistas,
                    "total_contratados": contratados,
                    "tasa_contratacion": Decimal(str(round(contratados * 100 / postulaciones, 2)))
                    if postulaciones else Decimal("0"),
                    "observaciones": "",
                    "fecha_actualizacion": datetime.now(timezone.utc).isoformat(),
                })
                numero += 1
    print(f"{tenant_id}: {numero} reportes cargados", flush=True)

print("Listo.", flush=True)
