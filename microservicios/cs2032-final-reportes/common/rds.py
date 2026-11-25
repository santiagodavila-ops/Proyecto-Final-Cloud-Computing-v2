"""Acceso a RDS MySQL (patrón Single Database, Multiple Schemas) para contar vacantes y postulaciones.

Un schema por tenant (tenant_1, tenant_2, ...). El tenant_id que sale del token
decide a qué schema se conecta; el nombre del schema va SOLO en el parámetro
`database` de la conexión, nunca dentro del SQL.
"""
import os
import re

import boto3
from botocore.config import Config
import pymysql

# Variables de entorno definidas en serverless.yml (fallback / compatibilidad)
RDS_HOST = os.environ.get("RDS_HOST")
RDS_USER = os.environ.get("RDS_USER")
RDS_PASSWORD = os.environ.get("RDS_PASSWORD")
RDS_PORT = int(os.environ.get("RDS_PORT", "3306")) if os.environ.get("RDS_PORT") else 3306

PATRON_TENANT = re.compile(r"^tenant_[a-z0-9_]+$")
# Únicas tablas que se pueden contar (constantes fijas: el nombre se interpola en el SQL)
TABLAS_CONTABLES = ("vacantes", "postulaciones")

# Cache en memoria para reutilizar credenciales entre invocaciones calientes (warm start)
_CREDS_CACHE = None


def _obtener_credenciales_rds(ssm_client=None):
    """Obtiene credenciales de RDS desde SSM Parameter Store con fallback a variables de entorno.

    Implementa caché en memoria para realizar la consulta a SSM únicamente durante el cold start
    del contenedor Lambda, optimizando latencia y evitando llamadas innecesarias al API de SSM.
    """
    global _CREDS_CACHE
    if _CREDS_CACHE is not None:
        return _CREDS_CACHE

    host = os.environ.get("RDS_HOST", RDS_HOST)
    user = os.environ.get("RDS_USER", RDS_USER)
    password = os.environ.get("RDS_PASSWORD", RDS_PASSWORD)
    try:
        port = int(os.environ.get("RDS_PORT", RDS_PORT or 3306))
    except (ValueError, TypeError):
        port = 3306

    stage = os.environ.get("STAGE", os.environ.get("SLS_STAGE", "dev"))
    prefix = os.environ.get("SSM_RDS_PREFIX", f"/cs2032/{stage}/rds")

    try:
        region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
        ssm = ssm_client or boto3.client(
            "ssm",
            region_name=region,
            config=Config(connect_timeout=2, read_timeout=3, retries={"max_attempts": 1}),
        )
        param_names = [
            f"{prefix}/host",
            f"{prefix}/user",
            f"{prefix}/password",
            f"{prefix}/port",
        ]
        respuesta = ssm.get_parameters(Names=param_names, WithDecryption=True)
        for param in respuesta.get("Parameters", []):
            nombre = param["Name"]
            valor = param["Value"]
            if nombre.endswith("/host"):
                host = valor
            elif nombre.endswith("/user"):
                user = valor
            elif nombre.endswith("/password"):
                password = valor
            elif nombre.endswith("/port"):
                try:
                    port = int(valor)
                except (ValueError, TypeError):
                    pass
    except Exception:
        # Fallback silencioso a variables de entorno si SSM no responde o no está disponible
        pass

    if not password:  # no cachear un fallo: el siguiente intento puede ver SSM
        raise RuntimeError("Sin credenciales de RDS: SSM no respondio y no hay RDS_PASSWORD")
    _CREDS_CACHE = {
        "host": host,
        "user": user,
        "password": password,
        "port": port,
    }
    return _CREDS_CACHE


def conexion_tenant(tenant_id):
    """Abre una conexión al schema del tenant. El llamador debe cerrarla (try/finally)."""
    if not isinstance(tenant_id, str) or not PATRON_TENANT.match(tenant_id):
        raise ValueError("tenant_id inválido")
    creds = _obtener_credenciales_rds()
    return pymysql.connect(
        host=creds["host"],
        user=creds["user"],
        password=creds["password"],
        port=creds["port"],
        database=tenant_id,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
        autocommit=False,
    )


def contar_por_estado(tenant_id, tabla):
    """Cuenta las filas de `vacantes` o `postulaciones` agrupadas por estado: {estado: conteo}."""
    if tabla not in TABLAS_CONTABLES:
        raise ValueError("tabla inválida")
    conexion = conexion_tenant(tenant_id)
    try:
        with conexion.cursor() as cursor:
            # `tabla` ya se validó contra la lista fija de arriba
            cursor.execute(f"SELECT estado, COUNT(*) AS total FROM {tabla} GROUP BY estado")
            filas = cursor.fetchall()
    finally:
        conexion.close()
    # Mismo criterio que antes: estado nulo se reporta como "sin_valor"; conteos como int
    return {(f["estado"] if f["estado"] is not None else "sin_valor"): int(f["total"]) for f in filas}
