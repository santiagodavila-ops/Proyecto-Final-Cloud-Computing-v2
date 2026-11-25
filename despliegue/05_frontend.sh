#!/usr/bin/env bash
# Reemplaza las URLs antiguas de las 5 APIs por las de .env.local y despliega el frontend en Amplify.
# Uso: bash despliegue/05_frontend.sh   (idempotente; requiere API_* en despliegue/.env.local)
# Solo se toca config/docs/tests/postman/README; no se modifica nada versionado con secretos.
set -euo pipefail
source "$(dirname "$0")/lib.sh"
set -a; source "$DIR/.env.local"; set +a
for v in API_USUARIOS API_CANDIDATOS API_VACANTES API_ENTREVISTAS API_REPORTES; do
  [ -n "${!v:-}" ] || { echo "ERROR: falta $v en .env.local" >&2; exit 1; }
done

M="$REPO/microservicios"
ARCHIVOS=$(grep -rlE "jas1g5t9tl|celozfy9cj|lx1fmyf70f|ik4kelr8a2|4zdu9n20s6|hwi0abum32|d3q8s9iuzj|7i7gtr9xv7|nhso47cnu1|zeagrg9231" \
  "$M/cs2032-final-frontend/config.js" "$M/cs2032-final-frontend/scripts" "$M/cs2032-final-frontend/docs" \
  "$M"/cs2032-final-*/prueba_integracion.sh "$M"/cs2032-final-*/postman \
  "$M"/cs2032-final-*/README.md 2>/dev/null || true)

if [ -z "$ARCHIVOS" ]; then
  echo "[05] No quedan URLs antiguas (ya reemplazadas)."
else
  echo "[05] Reemplazando URLs en $(echo "$ARCHIVOS" | wc -l | tr -d ' ') archivos ..."
  # sed -i '' es la forma BSD/macOS; en GNU se usa sin argumento
  if sed --version >/dev/null 2>&1; then SEDI=(sed -E -i); else SEDI=(sed -E -i ''); fi
  while IFS= read -r f; do
    "${SEDI[@]}" \
      -e "s#https://(jas1g5t9tl|hwi0abum32)\.execute-api\.us-east-1\.amazonaws\.com/dev#${API_USUARIOS}#g" \
      -e "s#https://(celozfy9cj|d3q8s9iuzj)\.execute-api\.us-east-1\.amazonaws\.com/dev#${API_CANDIDATOS}#g" \
      -e "s#https://(lx1fmyf70f|7i7gtr9xv7)\.execute-api\.us-east-1\.amazonaws\.com/dev#${API_VACANTES}#g" \
      -e "s#https://(ik4kelr8a2|nhso47cnu1)\.execute-api\.us-east-1\.amazonaws\.com/dev#${API_ENTREVISTAS}#g" \
      -e "s#https://(4zdu9n20s6|zeagrg9231)\.execute-api\.us-east-1\.amazonaws\.com/dev#${API_REPORTES}#g" "$f"
  done <<< "$ARCHIVOS"
fi

echo "[05] Desplegando frontend en Amplify ..."
cd "$M/cs2032-final-frontend"   # desplegar_amplify.sh usa rutas relativas (index.html, docs/openapi...)
bash scripts/desplegar_amplify.sh
