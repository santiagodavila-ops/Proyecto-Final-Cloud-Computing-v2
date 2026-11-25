#!/usr/bin/env bash
# Compila EmpleaCRM y publica el contenido de dist en la aplicación Amplify del proyecto.
set -euo pipefail
app_nombre=cs2032-crm-empleabilidad
rama=main
region=us-east-1
temporal=$(mktemp -d)
trap 'rm -rf -- "$temporal"' EXIT
if [[ $# -eq 0 ]]; then
  cd "$(dirname "$0")/.."
  npm ci --include=dev --no-audit --no-fund
  npm run build
  archivo="$temporal/frontend.zip"
  (cd dist && zip -qr "$archivo" .)
elif [[ $# -eq 2 && "$1" == "--zip" && -f "$2" ]]; then
  archivo=$2
else
  echo "Uso: bash scripts/desplegar_amplify.sh [--zip archivo-compilado.zip]" >&2
  exit 2
fi

app_id=$(aws amplify list-apps --region "$region" \
  --query "apps[?name=='$app_nombre'].appId | [0]" --output text)
if [[ -z "$app_id" || "$app_id" == None ]]; then
  app_id=$(aws amplify create-app --region "$region" --name "$app_nombre" --platform WEB \
    --query app.appId --output text)
fi
# En una rama existente basta el permiso de despliegue del script original.
preparar_subida() {
  aws amplify create-deployment --region "$region" --app-id "$app_id" --branch-name "$rama" \
    --query '[jobId, zipUploadUrl]' --output text
}
if ! datos_subida=$(preparar_subida 2>"$temporal/error-aws"); then
  if ! grep -q 'NotFoundException' "$temporal/error-aws"; then
    cat "$temporal/error-aws" >&2
    exit 1
  fi
  if ! aws amplify create-branch --region "$region" --app-id "$app_id" --branch-name "$rama" \
    --stage PRODUCTION >/dev/null 2>"$temporal/error-rama"; then
    if ! grep -qi 'already exists' "$temporal/error-rama"; then
      cat "$temporal/error-rama" >&2
      exit 1
    fi
  fi
  datos_subida=$(preparar_subida)
fi
read -r job_id url_subida <<< "$datos_subida"
curl --fail --silent --show-error -X PUT -H 'Content-Type: application/zip' \
  --upload-file "$archivo" "$url_subida"
aws amplify start-deployment --region "$region" --app-id "$app_id" --branch-name "$rama" --job-id "$job_id" >/dev/null
echo "Despliegue $job_id en curso."
while true; do
  estado=$(aws amplify get-job --region "$region" --app-id "$app_id" --branch-name "$rama" \
    --job-id "$job_id" --query job.summary.status --output text)
  case "$estado" in
    SUCCEED) break ;;
    FAILED|CANCELLED) echo "El despliegue terminó con estado $estado." >&2; exit 1 ;;
    *) sleep 4 ;;
  esac
done
dominio=$(aws amplify get-app --region "$region" --app-id "$app_id" --query app.defaultDomain --output text)
echo "Aplicación publicada en https://$rama.$dominio"
