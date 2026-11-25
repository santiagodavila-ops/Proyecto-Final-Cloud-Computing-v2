"""Genera docs/openapi/<microservicio>.json (OpenAPI 3) para el Swagger UI de docs.html.

Uso: python3 scripts/generar_openapi.py
"""
import json
from pathlib import Path

SALIDA = Path(__file__).resolve().parent.parent / "docs" / "openapi"

SERVIDORES = {
    "usuarios": "https://hwi0abum32.execute-api.us-east-1.amazonaws.com/dev",
    "candidatos": "https://d3q8s9iuzj.execute-api.us-east-1.amazonaws.com/dev",
    "vacantes": "https://7i7gtr9xv7.execute-api.us-east-1.amazonaws.com/dev",
    "entrevistas": "https://nhso47cnu1.execute-api.us-east-1.amazonaws.com/dev",
    "reportes": "https://zeagrg9231.execute-api.us-east-1.amazonaws.com/dev",
}

ERRORES = {
    "400": {"description": "Datos inválidos"},
    "401": {"description": "Token no enviado, inválido o expirado"},
    "404": {"description": "No existe en el tenant del token (aislamiento multi-tenant)"},
}


def ruta_param(nombre):
    return {"name": nombre, "in": "path", "required": True, "schema": {"type": "string"}}


def query(nombre, descripcion, enum=None):
    esquema = {"type": "string"}
    if enum:
        esquema["enum"] = enum
    return {"name": nombre, "in": "query", "required": False, "description": descripcion, "schema": esquema}


def op(resumen, ok="200", cuerpo=None, params=None, publico=False, descripcion=None,
       esquema_cuerpo=None, esquema_ok=None, descripcion_ok="OK", errores=None, bearer=False):
    """Arma una operación. esquema_* añaden schemas; errores reemplaza/añade respuestas de error;
    bearer=True fuerza el requisito de bearer en una operación que, por lo demás, sería pública."""
    respuesta_ok = {"description": descripcion_ok}
    if esquema_ok:
        respuesta_ok["content"] = {"application/json": {"schema": esquema_ok}}
    operacion = {"summary": resumen, "responses": {ok: respuesta_ok, **{k: v for k, v in {**ERRORES, **(errores or {})}.items() if v is not None}}}
    if descripcion:
        operacion["description"] = descripcion
    if params:
        operacion["parameters"] = params
    if cuerpo is not None:
        contenido = {"example": cuerpo}
        if esquema_cuerpo:
            contenido = {"schema": esquema_cuerpo, "example": cuerpo}
        operacion["requestBody"] = {"required": True, "content": {"application/json": contenido}}
    if publico:
        operacion["security"] = []
    elif bearer:
        operacion["security"] = [{"bearer": []}]
    return operacion


def cadena(descripcion=None, **extra):
    esquema = {"type": "string", **extra}
    if descripcion:
        esquema["description"] = descripcion
    return esquema


ROLES = ["administrador", "reclutador"]


CANDIDATO = {"nombre": "Lucía Ramos", "email": "lucia@correo.pe", "telefono": "999111222", "profesion": "Analista de datos"}
VACANTE = {"titulo": "Analista de Datos", "descripcion": "SQL y Python", "area": "Tecnología",
           "ubicacion": "Lima", "modalidad": "hibrido", "salario": 5500}
POSTULACIONES = ["postulado", "preseleccionado", "entrevista", "oferta", "contratado", "rechazado"]
ENTREVISTA = {"candidato_id": "<uuid>", "vacante_id": "<uuid>", "postulacion_id": "<uuid>",
              "entrevistador": "Carla Ruiz", "fecha_hora": "2026-11-20T15:00:00-05:00", "modalidad": "virtual"}

SERVICIOS = {
    "usuarios": ("MS1 · Usuarios / Autenticación", {
        "/usuarios": {"post": op(
            "Crear usuario (solo administrador)", "201",
            {"nombre": "Ana Torres", "email": "ana@empresa.pe", "password": "Secreta-123", "rol": "reclutador"},
            descripcion="Requiere token_acceso de un usuario con rol administrador. El usuario se crea en el "
                        "tenant del token; no se envía tenant_id.",
            bearer=True, descripcion_ok="Usuario creado",
            esquema_cuerpo={"type": "object", "required": ["nombre", "email", "password"], "properties": {
                "nombre": cadena(), "email": cadena(), "password": cadena(),
                "rol": cadena(enum=ROLES, default="reclutador")}},
            errores={"404": None, "403": {"description": "Solo un administrador puede crear usuarios"},
                     "409": {"description": "Ya existe un usuario con ese correo"}})},
        "/usuarios/login": {"post": op(
            "Login: devuelve token_acceso (15 min) y token_refresh (7 días)", "200",
            {"email": "demo.tenant_1@cs2032.test", "password": "Demo-cs2032"}, publico=True,
            descripcion="Usa token_acceso en Authorization: Bearer. Cuando expire (401), renuévalo con "
                        "POST /usuarios/refresh. El campo token es un alias deprecado de token_acceso.",
            errores={"404": None, "401": {"description": "Credenciales inválidas"}},
            esquema_ok={"type": "object", "properties": {
                "token_acceso": cadena("JWT de acceso (15 minutos)"),
                "token_refresh": cadena("Token de renovación (7 días)"),
                "expira_acceso": cadena("Vencimiento del token_acceso"),
                "expira_refresh": cadena("Vencimiento del token_refresh"),
                "tenant_id": cadena(), "usuario_id": cadena(),
                "token": {**cadena("Alias deprecado de token_acceso"), "deprecated": True},
                "rol": cadena("Rol del usuario", enum=ROLES)}})},
        "/usuarios/validar": {"get": op("Validar token y obtener su tenant_id")},
        "/usuarios/refresh": {"post": op(
            "Renovar token_acceso con el token_refresh", "200",
            {"token_refresh": "<token_refresh devuelto por /usuarios/login>"}, publico=True,
            descripcion="Devuelve un nuevo token_acceso (15 min). No requiere Authorization.",
            esquema_cuerpo={"type": "object", "required": ["token_refresh"], "properties": {"token_refresh": cadena()}},
            esquema_ok={"type": "object", "properties": {"token_acceso": cadena(), "expira_acceso": cadena()}},
            errores={"404": None, "401": {"description": "token_refresh expirado o inválido: hay que volver a iniciar sesión"}})},
    }),
    "candidatos": ("MS2 · Candidatos (+ CV en S3)", {
        "/candidatos": {
            "get": op("Listar candidatos del tenant (100 por página)", params=[query("ultimo_id", "Cursor de paginación")]),
            "post": op("Crear candidato", "201", CANDIDATO),
        },
        "/candidatos/{candidato_id}": {
            "parameters": [ruta_param("candidato_id")],
            "get": op("Buscar candidato"),
            "put": op("Modificar candidato", cuerpo={"profesion": "Científica de datos", "estado": "activo"}),
            "delete": op("Eliminar candidato"),
        },
        "/candidatos/{candidato_id}/cv-url": {
            "parameters": [ruta_param("candidato_id")],
            "post": op("Generar URL prefirmada de S3 para subir el CV (o confirmar con {\"confirmar\": true})", cuerpo={}),
        },
    }),
    "vacantes": ("MS3 · Vacantes / Postulaciones", {
        "/vacantes": {
            "get": op("Listar vacantes", params=[query("estado", "Filtro", ["abierta", "cerrada"]), query("cursor", "Paginación")]),
            "post": op("Publicar vacante", "201", VACANTE),
        },
        "/vacantes/{vacante_id}": {
            "parameters": [ruta_param("vacante_id")],
            "get": op("Buscar vacante"),
            "put": op("Modificar vacante", cuerpo={"salario": 6000, "estado": "cerrada"}),
            "delete": op("Eliminar vacante"),
        },
        "/postulaciones": {
            "get": op("Listar postulaciones (GSI indice_estado / indice_vacante)", params=[
                query("estado", "Etapa del pipeline", POSTULACIONES), query("vacante_id", "Filtrar por vacante"),
                query("cursor", "Paginación")]),
            "post": op("Postular candidato a vacante", "201", {"vacante_id": "<uuid>", "candidato_id": "<uuid>", "notas": ""}),
        },
        "/postulaciones/{postulacion_id}": {
            "parameters": [ruta_param("postulacion_id")],
            "get": op("Buscar postulación"),
            "put": op("Mover en el pipeline", cuerpo={"estado": "preseleccionado", "notas": "Buen perfil"}),
            "delete": op("Eliminar postulación"),
        },
    }),
    "entrevistas": ("MS4 · Entrevistas / Seguimiento", {
        "/entrevistas": {
            "get": op("Listar entrevistas", params=[query("estado", "Filtro", ["agendada", "realizada", "cancelada"]),
                                                   query("candidato_id", "Filtro"), query("vacante_id", "Filtro"),
                                                   query("cursor", "Paginación")]),
            "post": op("Agendar entrevista", "201", ENTREVISTA),
        },
        "/entrevistas/{entrevista_id}": {
            "parameters": [ruta_param("entrevista_id")],
            "get": op("Buscar entrevista"),
            "put": op("Modificar entrevista", cuerpo={"estado": "realizada", "notas": "Buen perfil técnico"}),
            "delete": op("Eliminar entrevista"),
        },
    }),
    "reportes": ("MS5 · Reportes", {
        "/reportes/generar": {"post": op("Recalcular resumen_general leyendo las tablas de MS1–MS4", "201", {})},
        "/reportes": {"get": op("Listar reportes", params=[query("prefijo", "Ej. diario_2026-10"), query("cursor", "Paginación")])},
        "/reportes/{tipo_reporte}": {
            "parameters": [ruta_param("tipo_reporte")],
            "get": op("Buscar reporte (ej. resumen_general)"),
            "put": op("Editar observaciones", cuerpo={"observaciones": "Revisado en demo"}),
            "delete": op("Eliminar reporte"),
        },
    }),
}

SALIDA.mkdir(parents=True, exist_ok=True)
for clave, (titulo, rutas) in SERVICIOS.items():
    documento = {
        "openapi": "3.0.3",
        "info": {
            "title": titulo,
            "version": "1.0.0",
            "description": "CRM de Empleabilidad · CS2032 Grupo 1. El tenant se obtiene del token "
                           "(Authorization: Bearer), nunca del body ni de la URL.",
        },
        "servers": [{"url": SERVIDORES[clave], "description": "API Gateway · stage dev"}],
        "components": {"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}},
        "security": [{"bearer": []}],
        "paths": rutas,
    }
    (SALIDA / f"{clave}.json").write_text(json.dumps(documento, ensure_ascii=False, indent=2), encoding="utf-8")
    print("generado", clave)
