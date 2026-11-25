"""Migra las tablas DynamoDB t_vacantes-<stage> y t_postulaciones-<stage> a RDS MySQL (un schema por tenant).

Primero se migran las vacantes de cada tenant y luego sus postulaciones (clave foránea a vacantes).

Uso (NO se ejecuta automáticamente; requiere acceso de red a RDS y credenciales AWS):
    export VACANTES_TABLE=t_vacantes-dev POSTULACIONES_TABLE=t_postulaciones-dev
    export RDS_HOST=... RDS_USER=... RDS_PASSWORD=... [RDS_PORT=3306]
    python3 scripts/migrar_a_rds.py

Es idempotente: INSERT ... ON DUPLICATE KEY UPDATE por vacante_id / postulacion_id.
"""
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone

import boto3
import pymysql

TENANTS_VALIDOS = ("tenant_1", "tenant_2", "tenant_3")
COLUMNAS = ("vacante_id", "titulo", "descripcion", "area", "ubicacion", "modalidad",
            "salario", "candidato_id", "estado", "fecha_publicacion", "fecha_actualizacion")
CAMPOS_FECHA = ("fecha_publicacion", "fecha_actualizacion")

COLUMNAS_POSTULACION = ("postulacion_id", "vacante_id", "candidato_id", "titulo_vacante", "estado",
                        "notas", "fecha_postulacion", "fecha_actualizacion")
CAMPOS_FECHA_POSTULACION = ("fecha_postulacion", "fecha_actualizacion")

TABLA = os.environ.get("VACANTES_TABLE")
TABLA_POSTULACIONES = os.environ.get("POSTULACIONES_TABLE")
if not TABLA or not TABLA_POSTULACIONES:
    sys.exit("Faltan VACANTES_TABLE y POSTULACIONES_TABLE (ej. t_vacantes-dev, t_postulaciones-dev)")

# columnas fijas del código (no datos externos); los valores van como parámetros
SQL = (
    f"INSERT INTO vacantes ({', '.join(COLUMNAS)}) VALUES ({', '.join(['%s'] * len(COLUMNAS))}) "
    "ON DUPLICATE KEY UPDATE "
    + ", ".join(f"{c} = VALUES({c})" for c in COLUMNAS if c != "vacante_id")
)
SQL_POSTULACION = (
    f"INSERT INTO postulaciones ({', '.join(COLUMNAS_POSTULACION)}) "
    f"VALUES ({', '.join(['%s'] * len(COLUMNAS_POSTULACION))}) "
    "ON DUPLICATE KEY UPDATE "
    + ", ".join(f"{c} = VALUES({c})" for c in COLUMNAS_POSTULACION if c != "postulacion_id")
)


def leer_tabla(nombre_tabla):
    """Escanea la tabla completa y agrupa los items por tenant_id."""
    tabla = boto3.resource("dynamodb", region_name="us-east-1").Table(nombre_tabla)
    por_tenant = defaultdict(list)
    clave = None
    while True:
        resultado = tabla.scan(**({"ExclusiveStartKey": clave} if clave else {}))
        for item in resultado["Items"]:
            por_tenant[item.get("tenant_id")].append(item)
        clave = resultado.get("LastEvaluatedKey")
        if not clave:
            return por_tenant


def a_fecha(valor):
    if not valor:
        return None
    return datetime.fromisoformat(valor).astimezone(timezone.utc).replace(tzinfo=None)


def a_fila(item):
    fila = []
    for columna in COLUMNAS:
        valor = item.get(columna)
        if columna in CAMPOS_FECHA:
            valor = a_fecha(valor)
        elif columna == "modalidad" and not valor:
            valor = "presencial"
        elif columna == "estado" and not valor:
            valor = "abierta"
        fila.append(valor)
    return tuple(fila)


def a_fila_postulacion(item):
    fila = []
    for columna in COLUMNAS_POSTULACION:
        valor = item.get(columna)
        if columna in CAMPOS_FECHA_POSTULACION:
            valor = a_fecha(valor)
        elif columna == "estado" and not valor:
            valor = "postulado"
        fila.append(valor)
    return tuple(fila)


def migrar(cursor, etiqueta, tenant_id, items, sql, convertir, id_campo):
    """Inserta los items de un tenant e imprime el resumen."""
    migrados, fallidos = 0, 0
    for item in items:
        try:
            cursor.execute(sql, convertir(item))
            migrados += 1
        except (pymysql.MySQLError, ValueError) as exc:
            fallidos += 1
            print(f"  {tenant_id}/{item.get(id_campo)}: {exc}")
    print(f"{tenant_id} {etiqueta}: {len(items)} leídos, {migrados} migrados, {fallidos} con error")


def main():
    por_tenant = leer_tabla(TABLA)
    postulaciones = leer_tabla(TABLA_POSTULACIONES)
    for tenant_id in sorted(k for k in por_tenant if k not in TENANTS_VALIDOS):
        print(f"{tenant_id}: omitido (tenant no válido), {len(por_tenant[tenant_id])} items")
    for tenant_id in sorted(k for k in postulaciones if k not in TENANTS_VALIDOS):
        print(f"{tenant_id}: postulaciones omitidas (tenant no válido), {len(postulaciones[tenant_id])} items")
    for tenant_id in TENANTS_VALIDOS:
        items = por_tenant.get(tenant_id, [])
        if not re.match(r"^tenant_[a-z0-9_]+$", tenant_id):
            continue
        conexion = pymysql.connect(
            host=os.environ["RDS_HOST"], user=os.environ["RDS_USER"],
            password=os.environ["RDS_PASSWORD"], port=int(os.environ.get("RDS_PORT", "3306")),
            database=tenant_id, charset="utf8mb4",
        )
        try:
            with conexion.cursor() as cursor:
                # Las vacantes primero: postulaciones.vacante_id es clave foránea
                migrar(cursor, "vacantes", tenant_id, items, SQL, a_fila, "vacante_id")
                migrar(cursor, "postulaciones", tenant_id, postulaciones.get(tenant_id, []),
                       SQL_POSTULACION, a_fila_postulacion, "postulacion_id")
            conexion.commit()
        finally:
            conexion.close()


if __name__ == "__main__":
    main()
