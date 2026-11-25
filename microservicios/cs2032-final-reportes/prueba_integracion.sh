#!/usr/bin/env bash
# Prueba de integración de los 5 microservicios (stage dev).
# Flujo: login (token_acceso) -> candidato -> vacante -> postular -> entrevista -> reporte,
# más aislamiento entre tenants y rechazo sin token.
# Usuarios demo: demo.tenant_N@cs2032.test / Demo-cs2032 (el login no envía tenant_id).
# Uso: bash prueba_integracion.sh
set -u

USUARIOS=https://hwi0abum32.execute-api.us-east-1.amazonaws.com/dev
CANDIDATOS=https://d3q8s9iuzj.execute-api.us-east-1.amazonaws.com/dev
VACANTES=https://7i7gtr9xv7.execute-api.us-east-1.amazonaws.com/dev
ENTREVISTAS=https://nhso47cnu1.execute-api.us-east-1.amazonaws.com/dev
REPORTES=https://zeagrg9231.execute-api.us-east-1.amazonaws.com/dev
PASSWORD=Demo-cs2032

FALLOS=0
campo() { python3 -c "import sys,json;d=json.load(sys.stdin);print(eval('d'+sys.argv[1]))" "$1"; }

# llamar METODO URL TOKEN [BODY] -> deja el cuerpo en $CUERPO y el código en $CODIGO
llamar() {
  local args=(-s -o /tmp/resp.json -w '%{http_code}' -X "$1" "$2")
  [ -n "$3" ] && args+=(-H "Authorization: Bearer $3")
  [ $# -ge 4 ] && args+=(-H 'Content-Type: application/json' -d "$4")
  CODIGO=$(curl "${args[@]}")
  CUERPO=$(cat /tmp/resp.json)
}

esperar() {  # esperar CODIGO_ESPERADO DESCRIPCION
  if [ "$CODIGO" = "$1" ]; then echo "  OK   $CODIGO  $2"
  else echo "  FALLA $CODIGO (esperado $1)  $2 -> $CUERPO"; FALLOS=$((FALLOS+1)); fi
}

login() {  # login TENANT -> imprime token_acceso (el usuario demo ya debe existir: crear usuarios exige un administrador)
  local email="demo.$1@cs2032.test"
  llamar POST "$USUARIOS/usuarios/login" "" "{\"email\":\"$email\",\"password\":\"$PASSWORD\"}"
  echo "$CUERPO" | campo "['token_acceso']"
}

echo "== Usuarios / Autenticación"
T1=$(login tenant_1); T2=$(login tenant_2)
[ -n "$T1" ] && [ -n "$T2" ] && echo "  OK   login tenant_1 y tenant_2" || { echo "  FALLA login"; exit 1; }
llamar GET "$USUARIOS/usuarios/validar" "$T1"; esperar 200 "validar token tenant_1"

echo "== Candidatos"
llamar POST "$CANDIDATOS/candidatos" "$T1" '{"nombre":"Lucía Prueba","email":"lucia@cs2032.test","telefono":"999000111","profesion":"Analista"}'
esperar 201 "crear candidato"; CAND=$(echo "$CUERPO" | campo "['candidato']['candidato_id']")

echo "== Vacantes"
llamar POST "$VACANTES/vacantes" "$T1" '{"titulo":"Analista de Datos","descripcion":"SQL y Python","area":"Tecnología","modalidad":"hibrido","salario":5500}'
esperar 201 "crear vacante"; VAC=$(echo "$CUERPO" | campo "['vacante']['vacante_id']")
llamar GET "$VACANTES/vacantes" "$T1"; esperar 200 "listar vacantes"
llamar GET "$VACANTES/vacantes?estado=abierta" "$T1"; esperar 200 "listar vacantes abiertas"
llamar GET "$VACANTES/vacantes/$VAC" "$T1"; esperar 200 "buscar vacante"
llamar PUT "$VACANTES/vacantes/$VAC" "$T1" '{"salario":6000,"ubicacion":"Lima"}'; esperar 200 "modificar vacante"
llamar POST "$VACANTES/vacantes" "$T1" '{"titulo":"x"}'; esperar 400 "crear vacante incompleta"

echo "== Postulaciones (pipeline)"
llamar POST "$VACANTES/postulaciones" "$T1" "{\"vacante_id\":\"$VAC\",\"candidato_id\":\"$CAND\"}"
esperar 201 "postular candidato"; POS=$(echo "$CUERPO" | campo "['postulacion']['postulacion_id']")
for estado in preseleccionado entrevista; do
  llamar PUT "$VACANTES/postulaciones/$POS" "$T1" "{\"estado\":\"$estado\"}"; esperar 200 "avanzar a $estado"
done
llamar GET "$VACANTES/postulaciones?estado=entrevista" "$T1"; esperar 200 "listar postulaciones en entrevista (GSI)"
llamar GET "$VACANTES/postulaciones?vacante_id=$VAC" "$T1"; esperar 200 "postulaciones de la vacante (GSI)"
echo "$CUERPO" | grep -q "$POS" && echo "  OK        la postulación aparece en su vacante" || { echo "  FALLA     postulación no listada"; FALLOS=$((FALLOS+1)); }
llamar POST "$VACANTES/postulaciones" "$T1" "{\"vacante_id\":\"$VAC\",\"candidato_id\":\"no-existe\"}"; esperar 404 "postular candidato inexistente"

echo "== Entrevistas"
llamar POST "$ENTREVISTAS/entrevistas" "$T1" "{\"candidato_id\":\"$CAND\",\"vacante_id\":\"$VAC\",\"postulacion_id\":\"$POS\",\"entrevistador\":\"Carla Ruiz\",\"fecha_hora\":\"2026-11-20T15:00:00-05:00\",\"modalidad\":\"virtual\"}"
esperar 201 "agendar entrevista"; ENT=$(echo "$CUERPO" | campo "['entrevista']['entrevista_id']")
llamar GET "$ENTREVISTAS/entrevistas?candidato_id=$CAND" "$T1"; esperar 200 "listar entrevistas del candidato"
llamar GET "$ENTREVISTAS/entrevistas/$ENT" "$T1"; esperar 200 "buscar entrevista"
llamar PUT "$ENTREVISTAS/entrevistas/$ENT" "$T1" '{"estado":"realizada","notas":"Buen perfil técnico"}'; esperar 200 "marcar realizada"
for estado in oferta contratado; do
  llamar PUT "$VACANTES/postulaciones/$POS" "$T1" "{\"estado\":\"$estado\"}"; esperar 200 "avanzar a $estado"
done

echo "== Reportes"
llamar POST "$REPORTES/reportes/generar" "$T1" '{}'; esperar 201 "generar resumen_general"
echo "$CUERPO" | python3 -c "import sys,json;r=json.load(sys.stdin)['reporte'];print('       ', {k:r[k] for k in ('total_usuarios','total_candidatos','total_vacantes','total_postulaciones','total_entrevistas','total_contratados','tasa_contratacion')})"
llamar GET "$REPORTES/reportes/resumen_general" "$T1"; esperar 200 "consultar resumen_general"
llamar PUT "$REPORTES/reportes/resumen_general" "$T1" '{"observaciones":"Revisado en demo"}'; esperar 200 "modificar observaciones"
llamar GET "$REPORTES/reportes?prefijo=diario_" "$T1"; esperar 200 "listar reportes diarios"

echo "== Aislamiento entre tenants y seguridad"
llamar GET "$VACANTES/vacantes/$VAC" "$T2"; esperar 404 "tenant_2 no ve la vacante de tenant_1"
llamar GET "$VACANTES/postulaciones/$POS" "$T2"; esperar 404 "tenant_2 no ve la postulación de tenant_1"
llamar GET "$ENTREVISTAS/entrevistas/$ENT" "$T2"; esperar 404 "tenant_2 no ve la entrevista de tenant_1"
llamar DELETE "$VACANTES/vacantes/$VAC" "$T2"; esperar 404 "tenant_2 no puede borrar la vacante de tenant_1"
for url in "$VACANTES/vacantes" "$VACANTES/postulaciones" "$ENTREVISTAS/entrevistas" "$REPORTES/reportes"; do
  llamar GET "$url" ""; esperar 401 "sin token: ${url#https://}"
done
llamar GET "$REPORTES/reportes" "token-falso"; esperar 401 "token inválido"

echo "== Limpieza de los datos de prueba"
llamar DELETE "$ENTREVISTAS/entrevistas/$ENT" "$T1"; esperar 200 "eliminar entrevista"
llamar DELETE "$VACANTES/postulaciones/$POS" "$T1"; esperar 200 "eliminar postulación"
llamar DELETE "$VACANTES/vacantes/$VAC" "$T1"; esperar 200 "eliminar vacante"
llamar GET "$VACANTES/vacantes/$VAC" "$T1"; esperar 404 "vacante ya no existe"
llamar DELETE "$CANDIDATOS/candidatos/$CAND" "$T1"; esperar 200 "eliminar candidato"

echo
[ "$FALLOS" = 0 ] && echo "RESULTADO: todas las pruebas pasaron" || echo "RESULTADO: $FALLOS pruebas fallaron"
exit "$FALLOS"
