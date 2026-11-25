#!/usr/bin/env bash
# Propósito: borra TODO (servicios serverless, RDS sin snapshot, endpoints, bucket de CVs, SG, SSM).
# Uso: ./99_destruir.sh   (pide confirmación escribiendo el ID de cuenta)
# Irreversible: los datos de RDS y los CVs se pierden.
source "$(dirname "$0")/lib.sh"
need aws sls
DBID=cs2032-vacantes-$STAGE
read -r -p "Esto BORRA todo en la cuenta $ACCOUNT_ID. Escribe el ID de cuenta para confirmar: " r
[ "$r" = "$ACCOUNT_ID" ] || { echo "Cancelado." >&2; exit 1; }

# 1. Servicios en orden inverso (necesitan RDS_* y SSM aún existentes)
for s in reportes entrevistas vacantes candidatos usuarios; do
  echo ">> sls remove $s"
  if [ "$s" = candidatos ]; then   # el bucket debe estar vacío para que CloudFormation lo borre
    aws s3 rm "s3://cs2032-candidatos-cv-$STAGE-$ACCOUNT_ID" --recursive 2>/dev/null || true
  fi
  (cd "$REPO/microservicios/cs2032-final-$s" && sls remove --stage "$STAGE")
done

# 2. RDS sin snapshot final
echo ">> Borrando RDS $DBID..."
if aws rds describe-db-instances --db-instance-identifier "$DBID" >/dev/null 2>&1; then
  aws rds delete-db-instance --db-instance-identifier "$DBID" --skip-final-snapshot --delete-automated-backups >/dev/null
  aws rds wait db-instance-deleted --db-instance-identifier "$DBID"
fi

# 3. Endpoints de interfaz
VPC=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
ids=$(aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values="$VPC" \
      --query "VpcEndpoints[?State!=\`deleted\` && (ServiceName=='com.amazonaws.$REGION.ssm' || ServiceName=='com.amazonaws.$REGION.kms')].VpcEndpointId" --output text)
if [ -n "$ids" ]; then
  echo ">> Borrando endpoints $ids"; aws ec2 delete-vpc-endpoints --vpc-endpoint-ids $ids >/dev/null
  for i in $(seq 1 30); do   # el SG no se puede borrar mientras queden ENIs
    left=$(aws ec2 describe-vpc-endpoints --vpc-endpoint-ids $ids --query 'length(VpcEndpoints[?State!=`deleted`])' --output text)
    [ "$left" = 0 ] && break; sleep 10
  done
fi

# 4. SG (las ENIs de las Lambdas pueden tardar minutos en liberarse: reintenta ~10 min)
for n in cs2032-rds-admin cs2032-lambda-rds; do
  g=$(aws ec2 describe-security-groups --filters Name=vpc-id,Values="$VPC" Name=group-name,Values=$n \
      --query 'SecurityGroups[0].GroupId' --output text)
  [ "$g" != None ] || continue
  for i in $(seq 1 60); do
    # quita reglas que se referencian a sí mismo (si no, no se puede borrar)
    aws ec2 revoke-security-group-ingress --group-id "$g" --protocol tcp --port 3306 --source-group "$g" 2>/dev/null || true
    aws ec2 revoke-security-group-ingress --group-id "$g" --protocol tcp --port 443 --source-group "$g" 2>/dev/null || true
    aws ec2 delete-security-group --group-id "$g" 2>/dev/null && { echo ">> SG $n borrado"; break; }
    [ "$i" -lt 60 ] || { echo "ERROR: no pude borrar SG $n ($g); hay ENIs en uso, reintenta más tarde" >&2; exit 1; }
    sleep 10
  done
done

# 5. SSM
aws ssm delete-parameters --names /cs2032/$STAGE/rds/{host,user,password,port} >/dev/null
rm -f "$DIR/.env.local"
echo ">> Todo borrado."
