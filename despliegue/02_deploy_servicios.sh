#!/usr/bin/env bash
# Despliega los 5 microservicios en orden (usuarios -> candidatos -> vacantes -> entrevistas -> reportes).
# Requiere haber corrido 01_infra_base.sh (SSM + .env.local con RDS_*). Guarda las URLs API_* en .env.local.
# Uso: bash despliegue/02_deploy_servicios.sh
set -euo pipefail
source "$(dirname "$0")/lib.sh"
[ -f "$DIR/.env.local" ] || { echo "Falta $DIR/.env.local: corre primero 01_infra_base.sh"; exit 1; }
set -a; source "$DIR/.env.local"; set +a

echo "==> Verificando variables RDS_* y parámetros SSM"
for v in RDS_SG_IDS RDS_SUBNET_IDS RDS_VPC_ID RDS_ROUTE_TABLE_IDS RDS_HOST; do
  [ -n "${!v:-}" ] || { echo "Falta la variable $v en .env.local"; exit 1; }
done
for p in host user port password; do
  aws ssm get-parameter --region "$REGION" --name "/cs2032/$STAGE/rds/$p" >/dev/null \
    || { echo "Falta el parámetro SSM /cs2032/$STAGE/rds/$p"; exit 1; }
done

# Desplegar en este orden: vacantes/entrevistas/reportes usan el authorizer del servicio usuarios
for s in usuarios candidatos vacantes entrevistas reportes; do
  d="$REPO/microservicios/cs2032-final-$s"
  echo "==> [$s] desplegando"
  cd "$d"
  if [ -f package.json ] && [ ! -d node_modules ]; then
    echo "    npm install (serverless-python-requirements)"
    npm install --no-audit --no-fund
  fi
  serverless deploy --stage "$STAGE"
done

echo "==> Obteniendo URLs de API Gateway"
for s in usuarios candidatos vacantes entrevistas reportes; do
  id=$(aws apigateway get-rest-apis --region "$REGION" \
    --query "items[?name=='$STAGE-cs2032-$s'].id | [0]" --output text)
  [ -n "$id" ] && [ "$id" != "None" ] || { echo "No se encontró la API $STAGE-cs2032-$s"; exit 1; }
  url="https://$id.execute-api.$REGION.amazonaws.com/$STAGE"
  env_set "API_$(echo "$s" | tr a-z A-Z)" "$url"
  echo "    API_$(echo "$s" | tr a-z A-Z)=$url"
done
echo "==> Listo. Siguiente paso: bash despliegue/03_datos.sh [cantidad_por_tenant]"
