#!/usr/bin/env bash
# Prueba de humo: login, GET protegido en las 5 APIs, 401 sin token, aislamiento multi-tenant y colas SQS.
# Uso: bash despliegue/06_smoke_test.sh   (requiere API_* y ADMIN_PASSWORD en despliegue/.env.local)
# Imprime tabla OK/FALLO y sale con código 1 si algo falla.
set -euo pipefail
source "$(dirname "$0")/lib.sh"
set -a; source "$DIR/.env.local"; set +a

RES=(); FALLOS=0
reg() { RES+=("$(printf '%-6s %s' "$1" "$2")"); [ "$1" = OK ] || FALLOS=$((FALLOS+1)); }
chk() {  # chk "descripcion" esperado obtenido
  if [ "$2" = "$3" ]; then reg OK "$1 ($3)"; else reg FALLO "$1 (esperado $2, obtenido $3)"; fi
}
http() {  # http METODO URL [TOKEN] [BODY] -> deja CODIGO y CUERPO
  local a=(-s -o /tmp/smoke_resp.json -w '%{http_code}' -X "$1" "$2")
  [ -n "${3:-}" ] && a+=(-H "Authorization: Bearer $3")
  [ -n "${4:-}" ] && a+=(-H 'Content-Type: application/json' -d "$4")
  CODIGO=$(curl "${a[@]}" || echo 000); CUERPO=$(cat /tmp/smoke_resp.json)
}
json() { python3 -c "import sys,json; print(json.load(sys.stdin)$1)" 2>/dev/null || true; }
login() {
  http POST "$API_USUARIOS/usuarios/login" "" "{\"email\":\"admin@$1.example\",\"password\":\"$ADMIN_PASSWORD\"}"
  echo "$CUERPO" | json "['token_acceso']"
}

echo "[06] Login de administradores ..."
T1=$(login tenant1); T2=$(login tenant2)
[ -n "$T1" ] && reg OK "login admin@tenant1.example" || reg FALLO "login admin@tenant1.example ($CODIGO)"
[ -n "$T2" ] && reg OK "login admin@tenant2.example" || reg FALLO "login admin@tenant2.example"

echo "[06] GET protegido en las 5 APIs ..."
RUTAS="usuarios:$API_USUARIOS/usuarios/validar candidatos:$API_CANDIDATOS/candidatos vacantes:$API_VACANTES/vacantes entrevistas:$API_ENTREVISTAS/entrevistas reportes:$API_REPORTES/reportes"
for r in $RUTAS; do
  http GET "${r#*:}" "$T1"; chk "GET ${r%%:*} con token" 200 "$CODIGO"
  http GET "${r#*:}" "";    chk "GET ${r%%:*} sin token" 401 "$CODIGO"
done

echo "[06] Aislamiento multi-tenant ..."
http POST "$API_VACANTES/vacantes" "$T1" '{"titulo":"Smoke test","descripcion":"borrar","area":"QA","modalidad":"remoto","salario":1000}'
VAC=$(echo "$CUERPO" | json "['vacante']['vacante_id']")
if [ -n "$VAC" ]; then
  reg OK "tenant1 crea vacante ($CODIGO)"
  http GET "$API_VACANTES/vacantes/$VAC" "$T2"; chk "tenant2 NO ve vacante de tenant1" 404 "$CODIGO"
  http GET "$API_VACANTES/vacantes" "$T2"
  if echo "$CUERPO" | grep -q "$VAC"; then reg FALLO "listado de tenant2 contiene vacante de tenant1"; else reg OK "listado de tenant2 sin vacante de tenant1"; fi
  http DELETE "$API_VACANTES/vacantes/$VAC" "$T1"; chk "limpieza: tenant1 borra su vacante" 200 "$CODIGO"
else
  reg FALLO "tenant1 crea vacante ($CODIGO)"
fi

echo "[06] Colas SQS ..."
for q in cola-notificaciones-entrevistas-$STAGE cola-notificaciones-entrevistas-dlq-$STAGE; do
  if aws sqs get-queue-url --region "$REGION" --queue-name "$q" >/dev/null 2>&1; then reg OK "cola $q existe"; else reg FALLO "cola $q no existe"; fi
done

echo; echo "===== RESULTADO ====="; printf '%s\n' "${RES[@]}"
echo "====================="
[ "$FALLOS" -eq 0 ] && echo "TODO OK" || { echo "$FALLOS comprobaciones FALLARON"; exit 1; }
