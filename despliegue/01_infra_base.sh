#!/usr/bin/env bash
# Propósito: crea la infra base manual (SG, RDS MySQL, SSM, endpoints SSM/KMS) y carga schema.sql.
# Uso: ./01_infra_base.sh   (idempotente; escribe despliegue/.env.local con RDS_* para serverless)
# Carga de schema: RDS queda público solo con tu IP durante la carga (SG cs2032-rds-admin) y luego se cierra.
source "$(dirname "$0")/lib.sh"
need aws curl python3 openssl

DBID=cs2032-vacantes-$STAGE
SSMP=/cs2032/$STAGE/rds
echo ">> Cuenta $ACCOUNT_ID, región $REGION"

# --- 1. Red: VPC por defecto, subnets (1 por AZ) y route tables ---
VPC=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
[ "$VPC" != None ] || { echo "ERROR: no hay VPC por defecto" >&2; exit 1; }
SUBNETS=$(aws ec2 describe-subnets --filters Name=vpc-id,Values="$VPC" Name=default-for-az,Values=true \
          --query 'Subnets[].SubnetId' --output text | tr '\t' ',')
NAZ=$(aws ec2 describe-subnets --filters Name=vpc-id,Values="$VPC" Name=default-for-az,Values=true \
      --query 'length(Subnets[].AvailabilityZone)' --output text)
[ "$NAZ" -ge 2 ] || { echo "ERROR: se requieren >=2 AZ, hay $NAZ" >&2; exit 1; }
RTBS=$(aws ec2 describe-route-tables --filters Name=vpc-id,Values="$VPC" \
       --query 'RouteTables[].RouteTableId' --output text | tr '\t' ',')
echo ">> VPC $VPC | subnets $SUBNETS | route tables $RTBS"

# --- 2. Security groups ---
sg() {  # sg nombre descripcion -> imprime id (crea si no existe)
  local id
  id=$(aws ec2 describe-security-groups --filters Name=vpc-id,Values="$VPC" Name=group-name,Values="$1" \
       --query 'SecurityGroups[0].GroupId' --output text)
  [ "$id" != None ] || id=$(aws ec2 create-security-group --group-name "$1" --description "$2" --vpc-id "$VPC" \
       --query GroupId --output text)
  echo "$id"
}
SG_APP=$(sg cs2032-lambda-rds "Lambdas + RDS + endpoints (solo trafico interno)")
SG_ADMIN=$(sg cs2032-rds-admin "Acceso admin temporal a RDS desde laptop")
# 3306 (RDS) y 443 (endpoints) solo desde el propio SG; ya existente => se ignora el error
for p in 3306 443; do
  aws ec2 authorize-security-group-ingress --group-id "$SG_APP" --protocol tcp --port $p --source-group "$SG_APP" 2>/dev/null || true
done
echo ">> SG app $SG_APP | SG admin $SG_ADMIN"

# --- 3. RDS ---
if aws rds describe-db-instances --db-instance-identifier "$DBID" >/dev/null 2>&1; then
  echo ">> RDS $DBID ya existe, se reutiliza"
  DBPASS=$(aws ssm get-parameter --name $SSMP/password --with-decryption --query Parameter.Value --output text 2>/dev/null \
           || echo "${DB_PASSWORD:-}")
  [ -n "$DBPASS" ] || { echo "ERROR: no encuentro la password (ni en SSM ni en .env.local)" >&2; exit 1; }
else
  DBPASS=$(openssl rand -hex 16)   # solo hex: sin caracteres problemáticos
  env_set DB_PASSWORD "$DBPASS"
  echo ">> Creando RDS $DBID (db.t3.micro, MySQL 8.0, 20GB gp3, Single-AZ, sin backups)..."
  aws rds create-db-instance --db-instance-identifier "$DBID" --db-instance-class db.t3.micro \
    --engine mysql --engine-version 8.0 --allocated-storage 20 --storage-type gp3 \
    --master-username admin --master-user-password "$DBPASS" --no-multi-az --backup-retention-period 0 \
    --no-publicly-accessible --no-auto-minor-version-upgrade \
    --vpc-security-group-ids "$SG_APP" "$SG_ADMIN" >/dev/null
fi
echo ">> Esperando a que RDS esté disponible (~5-10 min)..."
aws rds wait db-instance-available --db-instance-identifier "$DBID"
RDS_HOST=$(aws rds describe-db-instances --db-instance-identifier "$DBID" --query 'DBInstances[0].Endpoint.Address' --output text)
echo ">> RDS listo: $RDS_HOST"

# --- 4. SSM (SecureString; los serverless.yml los leen al desplegar) ---
put() { aws ssm put-parameter --name "$SSMP/$1" --type SecureString --value "$2" --overwrite >/dev/null; }
put host "$RDS_HOST"; put user admin; put password "$DBPASS"; put port 3306
echo ">> Parámetros SSM $SSMP/{host,user,password,port} guardados"

# --- 5. VPC endpoints de interfaz SSM y KMS (las Lambdas en VPC no tienen NAT) ---
for svc in ssm kms; do
  n=$(aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values="$VPC" Name=service-name,Values=com.amazonaws.$REGION.$svc \
      --query 'length(VpcEndpoints[?State!=`deleted`])' --output text)
  if [ "$n" = 0 ]; then
    echo ">> Creando endpoint $svc..."
    aws ec2 create-vpc-endpoint --vpc-id "$VPC" --vpc-endpoint-type Interface --service-name com.amazonaws.$REGION.$svc \
      --subnet-ids ${SUBNETS//,/ } --security-group-ids "$SG_APP" --private-dns-enabled \
      --tag-specifications "ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=cs2032-$svc-$STAGE}]" >/dev/null
  else echo ">> Endpoint $svc ya existe"; fi
done

# --- 6. .env.local para serverless ---
env_set RDS_SG_IDS "$SG_APP"
env_set RDS_SUBNET_IDS "$SUBNETS"
env_set RDS_VPC_ID "$VPC"
env_set RDS_ROUTE_TABLE_IDS "$RTBS"
env_set RDS_HOST "$RDS_HOST"
echo ">> Variables escritas en $DIR/.env.local"

# --- 7. Cargar schema.sql (acceso temporal desde la laptop) ---
if [ ! -x "$DIR/.venv/bin/python" ]; then
  python3 -m venv "$DIR/.venv"; "$DIR/.venv/bin/pip" -q install pymysql
fi
rds_publico on
trap 'rds_publico off' EXIT   # se cierra aunque falle la carga
echo ">> Esperando propagación del acceso público..."
for i in $(seq 1 30); do
  "$DIR/.venv/bin/python" -I - "$RDS_HOST" "$DBPASS" "$REPO/microservicios/cs2032-final-vacantes/sql/schema.sql" <<'PY' && break || { echo "   reintento $i..."; sleep 10; }
import sys, pymysql
from pymysql.constants import CLIENT
h, p, f = sys.argv[1:4]
c = pymysql.connect(host=h, user="admin", password=p, port=3306, connect_timeout=8, client_flag=CLIENT.MULTI_STATEMENTS)
cur = c.cursor(); cur.execute(open(f, encoding="utf-8").read())
while cur.nextset(): pass
c.commit(); print(">> schema.sql aplicado (CREATE ... IF NOT EXISTS)")
PY
  [ "$i" -lt 30 ] || { echo "ERROR: no pude conectar a RDS" >&2; exit 1; }
done
echo ">> Infra base lista. Siguiente: source despliegue/.env.local y sls deploy."
