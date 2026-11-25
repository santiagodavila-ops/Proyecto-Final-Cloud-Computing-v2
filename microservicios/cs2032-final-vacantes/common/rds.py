"""Acceso a RDS MySQL (patrón Single Database, Multiple Schemas) para vacantes y postulaciones.

Un schema por tenant (tenant_1, tenant_2, ...). El tenant_id que sale del token
decide a qué schema se conecta; el nombre del schema va SOLO en el parámetro
`database` de la conexión, nunca dentro del SQL. Todas las consultas son parametrizadas.
"""
import base64
import json
import os
import re
import uuid
from datetime import datetime, timezone

import boto3
from botocore.config import Config
import pymysql
from pymysql.constants import CLIENT

# Variables de entorno definidas en serverless.yml (fallback / compatibilidad)
RDS_HOST = os.environ.get("RDS_HOST")
RDS_USER = os.environ.get("RDS_USER")
RDS_PASSWORD = os.environ.get("RDS_PASSWORD")
RDS_PORT = int(os.environ.get("RDS_PORT", "3306")) if os.environ.get("RDS_PORT") else 3306

PATRON_TENANT = re.compile(r"^tenant_[a-z0-9_]+$")
TAMANO_PAGINA = 100
# Columnas de vacantes que se pueden escribir desde la API (lista blanca para el UPDATE)
COLUMNAS_EDITABLES = ("titulo", "descripcion", "area", "ubicacion", "modalidad", "salario", "estado")
# Columnas de postulaciones que se pueden modificar desde la API (lista blanca para el UPDATE)
COLUMNAS_EDITABLES_POSTULACION = ("estado", "notas")
CAMPOS_FECHA = ("fecha_publicacion", "fecha_actualizacion", "fecha_postulacion")

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
        # rowcount de UPDATE = filas encontradas (no solo las que cambian de valor)
        client_flag=CLIENT.FOUND_ROWS,
        connect_timeout=5,
        autocommit=False,
    )


def _a_datetime(iso):
    """ISO 8601 (con zona) -> datetime UTC sin zona, como lo guarda DATETIME."""
    return datetime.fromisoformat(iso).astimezone(timezone.utc).replace(tzinfo=None)


def _fila_a_item(fila, tenant_id):
    """Convierte una fila SQL al mismo formato que devolvía DynamoDB."""
    vacante = {"tenant_id": tenant_id}
    for campo, valor in fila.items():
        if valor is None:
            continue  # en DynamoDB los atributos ausentes no aparecían
        if campo in CAMPOS_FECHA:
            valor = valor.replace(tzinfo=timezone.utc).isoformat()
        vacante[campo] = valor
    return vacante


def _seleccionar(cursor, vacante_id):
    cursor.execute("SELECT * FROM vacantes WHERE vacante_id = %s", (vacante_id,))
    return cursor.fetchone()


def listar_vacantes_rds(tenant_id, estado, cursor_pagina):
    """Devuelve (vacantes, cursor_siguiente, error_cursor). cursor_pagina es el valor opaco recibido."""
    inicio = 0
    if cursor_pagina:
        try:
            inicio = int(json.loads(base64.urlsafe_b64decode(cursor_pagina.encode()).decode())["offset"])
            if inicio < 0:
                raise ValueError
        except (ValueError, TypeError, KeyError):
            return None, None, True
    sql = "SELECT * FROM vacantes"
    params = []
    if estado:
        sql += " WHERE estado = %s"
        params.append(estado)
    sql += " ORDER BY fecha_publicacion, vacante_id LIMIT %s OFFSET %s"
    # Se pide una fila de más para saber si hay página siguiente
    params += [TAMANO_PAGINA + 1, inicio]
    conexion = conexion_tenant(tenant_id)
    try:
        with conexion.cursor() as cursor:
            cursor.execute(sql, params)
            filas = cursor.fetchall()
    finally:
        conexion.close()
    siguiente = None
    if len(filas) > TAMANO_PAGINA:
        filas = filas[:TAMANO_PAGINA]
        siguiente = base64.urlsafe_b64encode(
            json.dumps({"offset": inicio + TAMANO_PAGINA}).encode()).decode()
    return [_fila_a_item(f, tenant_id) for f in filas], siguiente, False


def crear_vacante_rds(tenant_id, cambios, marca):
    """Inserta una vacante abierta. `cambios` ya viene validado. Devuelve la vacante creada."""
    vacante_id = str(uuid.uuid4())
    columnas = {"vacante_id": vacante_id, "modalidad": "presencial", **cambios,
                "estado": "abierta", "fecha_publicacion": _a_datetime(marca),
                "fecha_actualizacion": _a_datetime(marca)}
    nombres = ", ".join(columnas)  # claves fijas del código, nunca datos del usuario
    marcadores = ", ".join(["%s"] * len(columnas))
    conexion = conexion_tenant(tenant_id)
    try:
        with conexion.cursor() as cursor:
            cursor.execute(f"INSERT INTO vacantes ({nombres}) VALUES ({marcadores})",
                           list(columnas.values()))
            fila = _seleccionar(cursor, vacante_id)
        conexion.commit()
    finally:
        conexion.close()
    return _fila_a_item(fila, tenant_id)


def buscar_vacante_rds(tenant_id, vacante_id):
    conexion = conexion_tenant(tenant_id)
    try:
        with conexion.cursor() as cursor:
            fila = _seleccionar(cursor, vacante_id)
    finally:
        conexion.close()
    return _fila_a_item(fila, tenant_id) if fila else None


def modificar_vacante_rds(tenant_id, vacante_id, cambios, marca):
    """Devuelve la vacante actualizada o None si no existe."""
    cambios = {c: v for c, v in cambios.items() if c in COLUMNAS_EDITABLES}
    cambios["fecha_actualizacion"] = _a_datetime(marca)
    asignaciones = ", ".join(f"{columna} = %s" for columna in cambios)  # columnas de lista blanca
    conexion = conexion_tenant(tenant_id)
    try:
        with conexion.cursor() as cursor:
            cursor.execute(f"UPDATE vacantes SET {asignaciones} WHERE vacante_id = %s",
                           list(cambios.values()) + [vacante_id])
            if cursor.rowcount == 0:
                conexion.rollback()
                return None
            fila = _seleccionar(cursor, vacante_id)
        conexion.commit()
    finally:
        conexion.close()
    return _fila_a_item(fila, tenant_id)


RESULTADO_ELIMINADA = "eliminada"
RESULTADO_NO_ENCONTRADA = "no_encontrada"
RESULTADO_CON_POSTULACIONES = "con_postulaciones"


def eliminar_vacante_rds(tenant_id, vacante_id):
    """Devuelve eliminada, no_encontrada o con_postulaciones.

    No se borran las postulaciones en cascada: si la vacante tiene alguna,
    no se elimina y el llamador responde 409.
    """
    conexion = conexion_tenant(tenant_id)
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT 1 FROM vacantes WHERE vacante_id = %s", (vacante_id,))
            if cursor.fetchone() is None:
                return RESULTADO_NO_ENCONTRADA
            cursor.execute("SELECT 1 FROM postulaciones WHERE vacante_id = %s LIMIT 1", (vacante_id,))
            if cursor.fetchone() is not None:
                return RESULTADO_CON_POSTULACIONES
            cursor.execute("DELETE FROM vacantes WHERE vacante_id = %s", (vacante_id,))
        conexion.commit()
        return RESULTADO_ELIMINADA
    finally:
        conexion.close()


# ---------------------------------------------------------------- postulaciones

def _decodificar_inicio(cursor_pagina):
    """Devuelve el offset del cursor opaco, 0 si no hay cursor o None si es inválido."""
    if not cursor_pagina:
        return 0
    try:
        inicio = int(json.loads(base64.urlsafe_b64decode(cursor_pagina.encode()).decode())["offset"])
        if inicio < 0:
            raise ValueError
    except (ValueError, TypeError, KeyError):
        return None
    return inicio


def _seleccionar_postulacion(cursor, postulacion_id):
    cursor.execute("SELECT * FROM postulaciones WHERE postulacion_id = %s", (postulacion_id,))
    return cursor.fetchone()


def listar_postulaciones_rds(tenant_id, estado, vacante_id, cursor_pagina):
    """Devuelve (postulaciones, cursor_siguiente, error_cursor). Filtros opcionales por estado y vacante."""
    inicio = _decodificar_inicio(cursor_pagina)
    if inicio is None:
        return None, None, True
    condiciones, params = [], []
    if estado:
        condiciones.append("estado = %s")
        params.append(estado)
    if vacante_id:
        condiciones.append("vacante_id = %s")
        params.append(vacante_id)
    sql = "SELECT * FROM postulaciones"
    if condiciones:
        sql += " WHERE " + " AND ".join(condiciones)  # fragmentos fijos del código
    sql += " ORDER BY fecha_postulacion, postulacion_id LIMIT %s OFFSET %s"
    # Se pide una fila de más para saber si hay página siguiente
    params += [TAMANO_PAGINA + 1, inicio]
    conexion = conexion_tenant(tenant_id)
    try:
        with conexion.cursor() as cursor:
            cursor.execute(sql, params)
            filas = cursor.fetchall()
    finally:
        conexion.close()
    siguiente = None
    if len(filas) > TAMANO_PAGINA:
        filas = filas[:TAMANO_PAGINA]
        siguiente = base64.urlsafe_b64encode(
            json.dumps({"offset": inicio + TAMANO_PAGINA}).encode()).decode()
    return [_fila_a_item(f, tenant_id) for f in filas], siguiente, False


def crear_postulacion_rds(tenant_id, vacante, candidato_id, notas, marca):
    """Inserta una postulación en estado 'postulado'. `vacante` ya fue validada (existe y está abierta).

    La clave foránea a vacantes garantiza la integridad aunque la vacante se borre entre medias.
    """
    postulacion_id = str(uuid.uuid4())
    conexion = conexion_tenant(tenant_id)
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                "INSERT INTO postulaciones (postulacion_id, vacante_id, candidato_id, titulo_vacante, "
                "estado, notas, fecha_postulacion, fecha_actualizacion) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (postulacion_id, vacante["vacante_id"], candidato_id, vacante["titulo"], "postulado",
                 notas, _a_datetime(marca), _a_datetime(marca)))
            fila = _seleccionar_postulacion(cursor, postulacion_id)
        conexion.commit()
    finally:
        conexion.close()
    return _fila_a_item(fila, tenant_id)


def buscar_postulacion_rds(tenant_id, postulacion_id):
    conexion = conexion_tenant(tenant_id)
    try:
        with conexion.cursor() as cursor:
            fila = _seleccionar_postulacion(cursor, postulacion_id)
    finally:
        conexion.close()
    return _fila_a_item(fila, tenant_id) if fila else None


def modificar_postulacion_rds(tenant_id, postulacion_id, cambios, marca):
    """Devuelve la postulación actualizada o None si no existe."""
    cambios = {c: v for c, v in cambios.items() if c in COLUMNAS_EDITABLES_POSTULACION}
    cambios["fecha_actualizacion"] = _a_datetime(marca)
    asignaciones = ", ".join(f"{columna} = %s" for columna in cambios)  # columnas de lista blanca
    conexion = conexion_tenant(tenant_id)
    try:
        with conexion.cursor() as cursor:
            cursor.execute(f"UPDATE postulaciones SET {asignaciones} WHERE postulacion_id = %s",
                           list(cambios.values()) + [postulacion_id])
            if cursor.rowcount == 0:
                conexion.rollback()
                return None
            fila = _seleccionar_postulacion(cursor, postulacion_id)
        conexion.commit()
    finally:
        conexion.close()
    return _fila_a_item(fila, tenant_id)


def eliminar_postulacion_rds(tenant_id, postulacion_id):
    """True si se eliminó, False si no existía."""
    conexion = conexion_tenant(tenant_id)
    try:
        with conexion.cursor() as cursor:
            cursor.execute("DELETE FROM postulaciones WHERE postulacion_id = %s", (postulacion_id,))
            borrada = cursor.rowcount > 0
        conexion.commit()
    finally:
        conexion.close()
    return borrada
