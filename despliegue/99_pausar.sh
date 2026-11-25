#!/usr/bin/env bash
# Propósito: pausar para ahorrar crédito: detiene RDS y borra los endpoints de interfaz SSM/KMS (cobran por hora).
# Uso: ./99_pausar.sh   (RDS stop dura máx. 7 días; luego AWS lo reinicia solo)
# Para reanudar: aws rds start-db-instance ... y ./01_infra_base.sh (recrea los endpoints).
source "$(dirname "$0")/lib.sh"
need aws
DBID=cs2032-vacantes-$STAGE
echo ">> Deteniendo RDS $DBID..."
aws rds stop-db-instance --db-instance-identifier "$DBID" >/dev/null
for svc in ssm kms; do
  ids=$(aws ec2 describe-vpc-endpoints --filters Name=service-name,Values=com.amazonaws.$REGION.$svc \
        --query 'VpcEndpoints[?State!=`deleted`].VpcEndpointId' --output text)
  [ -z "$ids" ] || { echo ">> Borrando endpoint $svc: $ids"; aws ec2 delete-vpc-endpoints --vpc-endpoint-ids $ids >/dev/null; }
done
echo ">> Pausado. Reanudar: aws rds start-db-instance --db-instance-identifier $DBID && ./01_infra_base.sh"
