"""Crea el primer administrador de cada tenant escribiendo directo en t_usuarios-<stage>.
Uso: ADMIN_PASSWORD=... python seed_admin.py [stage]   (idempotente: si el email existe, no hace nada)
Reutiliza common/passwords.py de usuarios (PBKDF2-SHA256, 310000 iteraciones).
"""
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import boto3
from boto3.dynamodb.conditions import Key

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "microservicios" / "cs2032-final-usuarios"))
from common.passwords import hashear_password  # noqa: E402

STAGE = sys.argv[1] if len(sys.argv) > 1 else "dev"
PASSWORD = os.environ["ADMIN_PASSWORD"]
tabla = boto3.resource("dynamodb", region_name="us-east-1").Table(f"t_usuarios-{STAGE}")

for n in (1, 2, 3):
    email = f"admin@tenant{n}.example"
    # El correo es único global: se consulta el GSI indice_email, igual que crear_usuario
    if tabla.query(IndexName="indice_email", KeyConditionExpression=Key("email").eq(email), Limit=1)["Items"]:
        print(f"  tenant_{n}: {email} ya existe, se omite")
        continue
    tabla.put_item(Item={
        "tenant_id": f"tenant_{n}",
        "usuario_id": str(uuid.uuid4()),
        "nombre": f"Administrador Tenant {n}",
        "email": email,
        "password_hash": hashear_password(PASSWORD),
        "rol": "administrador",
        "fecha_registro": datetime.now(timezone.utc).isoformat(),
    })
    print(f"  tenant_{n}: {email} creado")
