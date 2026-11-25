#!/usr/bin/env bash
# Crea alarmas CloudWatch, tópico SNS y dashboard (scripts/observability/setup_cloudwatch_alarms_and_dashboard.py).
# Uso: bash despliegue/04_observabilidad.sh [correo_alertas]   (o ALERT_EMAIL en .env.local)
# Requiere python3 y credenciales AWS activas; instala boto3 en un venv local si falta.
set -euo pipefail
source "$(dirname "$0")/lib.sh"
[ -f "$DIR/.env.local" ] && { set -a; source "$DIR/.env.local"; set +a; }
export ALERT_EMAIL="${1:-${ALERT_EMAIL:-}}"
[ -n "$ALERT_EMAIL" ] || { echo "ERROR: indica el correo: $0 correo@dominio o ALERT_EMAIL en .env.local" >&2; exit 1; }

PY=python3
if ! $PY -c 'import boto3' 2>/dev/null; then
  echo "[04] boto3 no disponible, creando venv en $DIR/.venv ..."
  [ -d "$DIR/.venv" ] || python3 -m venv "$DIR/.venv"
  "$DIR/.venv/bin/pip" install -q boto3
  PY="$DIR/.venv/bin/python"
fi
echo "[04] Configurando observabilidad (alertas a $ALERT_EMAIL) ..."
"$PY" "$REPO/scripts/observability/setup_cloudwatch_alarms_and_dashboard.py"
echo "[04] Listo. Confirma la suscripción SNS desde el correo recibido."
