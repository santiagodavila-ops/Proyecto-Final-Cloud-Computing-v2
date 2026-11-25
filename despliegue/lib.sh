# Propósito: variables y funciones compartidas de los scripts de despliegue.
# Uso: source "$(dirname "$0")/lib.sh"   (no se ejecuta directamente)
# Define: REGION, STAGE, ACCOUNT_ID, DIR, REPO, need, rds_publico, y carga .env.local si existe.
set -euo pipefail

export REGION=us-east-1 STAGE=dev
export AWS_DEFAULT_REGION=$REGION AWS_PAGER=""
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$DIR/.." && pwd)"
export DIR REPO

# shellcheck disable=SC1091
[ -f "$DIR/.env.local" ] && source "$DIR/.env.local"

need() {  # need herr1 herr2 ... ; además valida credenciales AWS
  for t in "$@"; do command -v "$t" >/dev/null || { echo "ERROR: falta '$t' en el PATH" >&2; exit 1; }; done
  ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text) \
    || { echo "ERROR: credenciales AWS inválidas (renueva las del Learner Lab)" >&2; exit 1; }
  export ACCOUNT_ID
}

# Guarda/actualiza una variable en .env.local (permisos 600). Uso: env_set NOMBRE valor
env_set() {
  touch "$DIR/.env.local"; chmod 600 "$DIR/.env.local"
  grep -v "^export $1=" "$DIR/.env.local" > "$DIR/.env.local.tmp" || true
  echo "export $1=\"$2\"" >> "$DIR/.env.local.tmp"
  mv "$DIR/.env.local.tmp" "$DIR/.env.local"; chmod 600 "$DIR/.env.local"
}

# Acceso temporal a RDS desde esta laptop (para schema.sql / migrar_a_rds.py).
# on : RDS PubliclyAccessible + SG de admin (cs2032-rds-admin) con 3306 solo desde tu IP pública.
# off: cierra la regla y quita acceso público. El SG de las Lambdas nunca se abre al exterior.
rds_publico() {
  local id=cs2032-vacantes-$STAGE vpc admin ip
  vpc=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
  admin=$(aws ec2 describe-security-groups --filters Name=vpc-id,Values="$vpc" Name=group-name,Values=cs2032-rds-admin \
          --query 'SecurityGroups[0].GroupId' --output text)
  [ "$admin" != None ] || { echo "ERROR: no existe el SG cs2032-rds-admin (corre 01_infra_base.sh)" >&2; return 1; }
  case "${1:-}" in
    on)
      ip=$(curl -fsS https://checkip.amazonaws.com | tr -d '[:space:]')
      echo ">> Abriendo 3306 solo para $ip y activando acceso público en RDS..."
      aws ec2 authorize-security-group-ingress --group-id "$admin" --protocol tcp --port 3306 --cidr "$ip/32" 2>/dev/null || true
      aws rds wait db-instance-available --db-instance-identifier "$id" 2>/dev/null || true
      aws rds modify-db-instance --db-instance-identifier "$id" --publicly-accessible --apply-immediately >/dev/null
      sleep 5
      aws rds wait db-instance-available --db-instance-identifier "$id"
      ;;
    off)
      echo ">> Cerrando acceso público a RDS..."
      local cidrs
      cidrs=$(aws ec2 describe-security-groups --group-ids "$admin" \
              --query 'SecurityGroups[0].IpPermissions[].IpRanges[].CidrIp' --output text)
      for c in $cidrs; do
        aws ec2 revoke-security-group-ingress --group-id "$admin" --protocol tcp --port 3306 --cidr "$c" >/dev/null
      done
      aws rds wait db-instance-available --db-instance-identifier "$id" 2>/dev/null || true
      aws rds modify-db-instance --db-instance-identifier "$id" --no-publicly-accessible --apply-immediately >/dev/null
      sleep 5
      aws rds wait db-instance-available --db-instance-identifier "$id"
      ;;
    *) echo "uso: rds_publico on|off" >&2; return 1 ;;
  esac
}
