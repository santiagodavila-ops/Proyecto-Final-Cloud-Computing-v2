#!/usr/bin/env bash
# Script reproducible de reset total de cuenta AWS Learner Lab
# Requisitos: set -euo pipefail, --dry-run por defecto, confirmación con Account ID para --ejecutar.
# Conserva recursos del Learner Lab (Stack c220111a..., LabRole, default VPC/SG, vockey).
set -euo pipefail

TARGET_ACCOUNT="452254767800"
LAB_STACK="c220111a5553174l17447627t1w452254767800"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVIDENCIA_DIR="$DIR/evidencia_reset"
mkdir -p "$EVIDENCIA_DIR"

MODE="dry-run"
if [ "${1:-}" = "--ejecutar" ]; then
  MODE="ejecutar"
elif [ "${1:-}" = "--dry-run" ] || [ -z "${1:-}" ]; then
  MODE="dry-run"
else
  echo "Uso: $0 [--dry-run | --ejecutar]" >&2
  exit 1
fi

echo "=========================================================="
echo "RESET DE CUENTA AWS LEARNER LAB ($MODE)"
echo "=========================================================="

# 0. Verificación de identidad
CURRENT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
CURRENT_ARN=$(aws sts get-caller-identity --query Arn --output text)
echo "Cuenta actual : $CURRENT_ACCOUNT"
echo "Identidad STS : $CURRENT_ARN"

if [ "$CURRENT_ACCOUNT" != "$TARGET_ACCOUNT" ]; then
  echo "ERROR CRÍTICO: La cuenta actual ($CURRENT_ACCOUNT) no coincide con la cuenta autorizada ($TARGET_ACCOUNT)." >&2
  echo "Deteniendo ejecución por seguridad." >&2
  exit 1
fi

if [ "$MODE" = "ejecutar" ]; then
  echo ""
  echo "¡ADVERTENCIA! Este proceso eliminará todos los recursos de usuario en la cuenta $TARGET_ACCOUNT."
  if [ -n "${CONFIRM_ACCOUNT_ID:-}" ]; then
    INPUT_CONFIRM="$CONFIRM_ACCOUNT_ID"
    echo "Confirmación recibida vía variable CONFIRM_ACCOUNT_ID: $INPUT_CONFIRM"
  else
    read -r -p "Para confirmar el borrado, escribe el ID de la cuenta ($TARGET_ACCOUNT): " INPUT_CONFIRM
  fi

  if [ "$INPUT_CONFIRM" != "$TARGET_ACCOUNT" ]; then
    echo "Confirmación fallida. Cancelando reset." >&2
    exit 1
  fi
  echo "Confirmación correcta. Iniciando reset..."
fi

# 1. Asegurar evidencia de recursos del Lab
echo ">> Registrando recursos del stack de Lab ($LAB_STACK)..."
aws cloudformation list-stack-resources --stack-name "$LAB_STACK" > "$EVIDENCIA_DIR/00_stack_lab.txt"

# Extraer IDs/Nombres físicos de recursos de Lab para protegerlos
LAB_PHYSICAL_IDS=$(grep -o '"PhysicalResourceId": "[^"]*"' "$EVIDENCIA_DIR/00_stack_lab.txt" | cut -d'"' -f4 || true)

is_lab_resource() {
  local res="$1"
  for lab_res in $LAB_PHYSICAL_IDS; do
    if [ "$res" = "$lab_res" ]; then
      return 0
    fi
  done
  return 1
}

# 2. Paso a paso de limpieza
echo ""
echo ">> Paso 1: EC2, EIP, Volúmenes, Snapshots, AMIs y Key Pairs..."
INSTANCES=$(aws ec2 describe-instances --filters "Name=instance-state-name,Values=running,stopped,stopping,pending" --query 'Reservations[*].Instances[*].InstanceId' --output text || true)
for inst in $INSTANCES; do
  [ -z "$inst" ] || [ "$inst" = "None" ] && continue
  echo "[$MODE] EC2 Instance: $inst"
  if [ "$MODE" = "ejecutar" ]; then
    aws ec2 terminate-instances --instance-ids "$inst"
  fi
done

EIPS=$(aws ec2 describe-addresses --query 'Addresses[*].AllocationId' --output text || true)
for eip in $EIPS; do
  [ -z "$eip" ] || [ "$eip" = "None" ] && continue
  echo "[$MODE] Liberando EIP: $eip"
  if [ "$MODE" = "ejecutar" ]; then
    aws ec2 release-address --allocation-id "$eip"
  fi
done

VOLS=$(aws ec2 describe-volumes --filters Name=status,Values=available --query 'Volumes[*].VolumeId' --output text || true)
for vol in $VOLS; do
  [ -z "$vol" ] || [ "$vol" = "None" ] && continue
  echo "[$MODE] Borrando volumen disponible: $vol"
  if [ "$MODE" = "ejecutar" ]; then
    aws ec2 delete-volume --volume-id "$vol"
  fi
done

KEYPAIRS=$(aws ec2 describe-key-pairs --query 'KeyPairs[?KeyName!=`vockey`].KeyName' --output text || true)
for kp in $KEYPAIRS; do
  [ -z "$kp" ] || [ "$kp" = "None" ] && continue
  echo "[$MODE] Borrando keypair de usuario: $kp"
  if [ "$MODE" = "ejecutar" ]; then
    aws ec2 delete-key-pair --key-name "$kp"
  fi
done

echo ""
echo ">> Paso 2: RDS..."
RDS_INSTANCES=$(aws rds describe-db-instances --query 'DBInstances[*].DBInstanceIdentifier' --output text || true)
for rds in $RDS_INSTANCES; do
  [ -z "$rds" ] || [ "$rds" = "None" ] && continue
  echo "[$MODE] Borrando RDS: $rds"
  if [ "$MODE" = "ejecutar" ]; then
    aws rds modify-db-instance --db-instance-identifier "$rds" --no-deletion-protection --apply-immediately 2>/dev/null || true
    aws rds delete-db-instance --db-instance-identifier "$rds" --skip-final-snapshot --delete-automated-backups
    echo "Esperando que $rds se elimine..."
    aws rds wait db-instance-deleted --db-instance-identifier "$rds"
  fi
done

echo ""
echo ">> Paso 3: CloudFormation Stacks (excepto stack de Lab)..."
STACKS=$(aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE ROLLBACK_COMPLETE DELETE_FAILED --query "StackSummaries[?StackName!=\`$LAB_STACK\`].StackName" --output text || true)
for stk in $STACKS; do
  [ -z "$stk" ] || [ "$stk" = "None" ] && continue
  echo "[$MODE] Borrando Stack: $stk"
  if [ "$MODE" = "ejecutar" ]; then
    aws cloudformation delete-stack --stack-name "$stk"
    echo "Esperando eliminación de stack $stk..."
    aws cloudformation wait stack-delete-complete --stack-name "$stk"
  fi
done

echo ""
echo ">> Paso 4: Lambdas huérfanas..."
LAMBDAS=$(aws lambda list-functions --query 'Functions[*].FunctionName' --output text || true)
for fn in $LAMBDAS; do
  [ -z "$fn" ] || [ "$fn" = "None" ] && continue
  if is_lab_resource "$fn"; then
    echo "Conservando función de Lab: $fn"
  else
    echo "[$MODE] Borrando función Lambda: $fn"
    if [ "$MODE" = "ejecutar" ]; then
      aws lambda delete-function --function-name "$fn"
    fi
  fi
done

echo ""
echo ">> Paso 5: API Gateway..."
APIS=$(aws apigateway get-rest-apis --query 'items[*].id' --output text || true)
for api in $APIS; do
  [ -z "$api" ] || [ "$api" = "None" ] && continue
  echo "[$MODE] Borrando REST API: $api"
  if [ "$MODE" = "ejecutar" ]; then
    aws apigateway delete-rest-api --rest-api-id "$api"
    sleep 5
  fi
done

echo ""
echo ">> Paso 6: DynamoDB..."
TABLES=$(aws dynamodb list-tables --query 'TableNames[*]' --output text || true)
for tbl in $TABLES; do
  [ -z "$tbl" ] || [ "$tbl" = "None" ] && continue
  echo "[$MODE] Borrando tabla DynamoDB: $tbl"
  if [ "$MODE" = "ejecutar" ]; then
    aws dynamodb delete-table --table-name "$tbl"
  fi
done

echo ""
echo ">> Paso 7: S3 Buckets..."
BUCKETS=$(aws s3api list-buckets --query 'Buckets[*].Name' --output text || true)
for bkt in $BUCKETS; do
  [ -z "$bkt" ] || [ "$bkt" = "None" ] && continue
  echo "[$MODE] Vaciando y borrando bucket: $bkt"
  if [ "$MODE" = "ejecutar" ]; then
    aws s3 rm "s3://$bkt" --recursive || true
    # Eliminar versiones y delete markers si versioning estaba activo
    VERSIONS=$(aws s3api list-object-versions --bucket "$bkt" --output json 2>/dev/null || true)
    if [ -n "$VERSIONS" ]; then
      echo "Eliminando versiones en $bkt..."
      aws s3api delete-objects --bucket "$bkt" --delete "$(echo "$VERSIONS" | jq -c '{Objects: [.Versions[]? | {Key: .Key, VersionId: .VersionId}] + [.DeleteMarkers[]? | {Key: .Key, VersionId: .VersionId}] | select(length > 0)}')" 2>/dev/null || true
    fi
    aws s3 rb "s3://$bkt" --force || true
  fi
done

echo ""
echo ">> Paso 8: SQS y SNS..."
QUEUES=$(aws sqs list-queues --query 'QueueUrls[*]' --output text || true)
for q in $QUEUES; do
  [ -z "$q" ] || [ "$q" = "None" ] && continue
  echo "[$MODE] Borrando cola SQS: $q"
  if [ "$MODE" = "ejecutar" ]; then
    aws sqs delete-queue --queue-url "$q"
  fi
done

SNS_TOPICS=$(aws sns list-topics --query 'Topics[*].TopicArn' --output text || true)
for top in $SNS_TOPICS; do
  [ -z "$top" ] || [ "$top" = "None" ] && continue
  if is_lab_resource "$top" || [[ "$top" == *":RedshiftSNS" ]]; then
    echo "Conservando tópico SNS de Lab: $top"
  else
    echo "[$MODE] Borrando tópico SNS: $top"
    if [ "$MODE" = "ejecutar" ]; then
      aws sns delete-topic --topic-arn "$top"
    fi
  fi
done

# Suscripciones SNS huérfanas
SNS_SUBS=$(aws sns list-subscriptions --query 'Subscriptions[?TopicArn!=`arn:aws:sns:us-east-1:452254767800:RedshiftSNS`].SubscriptionArn' --output text || true)
for sub in $SNS_SUBS; do
  [ -z "$sub" ] || [ "$sub" = "None" ] || [ "$sub" = "PendingConfirmation" ] && continue
  echo "[$MODE] Borrando suscripción SNS huérfana: $sub"
  if [ "$MODE" = "ejecutar" ]; then
    aws sns unsubscribe --subscription-arn "$sub" || true
  fi
done

echo ""
echo ">> Paso 9: SSM Parameters..."
SSM_PARAMS=$(aws ssm describe-parameters --query 'Parameters[*].Name' --output text || true)
for param in $SSM_PARAMS; do
  [ -z "$param" ] || [ "$param" = "None" ] && continue
  echo "[$MODE] Borrando parámetro SSM: $param"
  if [ "$MODE" = "ejecutar" ]; then
    aws ssm delete-parameter --name "$param" || true
  fi
done

echo ""
echo ">> Paso 10: CloudWatch (Alarmas, Dashboards, Logs huérfanos)..."
ALARMS=$(aws cloudwatch describe-alarms --query 'MetricAlarms[*].AlarmName' --output text || true)
for alm in $ALARMS; do
  [ -z "$alm" ] || [ "$alm" = "None" ] && continue
  echo "[$MODE] Borrando alarma: $alm"
  if [ "$MODE" = "ejecutar" ]; then
    aws cloudwatch delete-alarms --alarm-names "$alm"
  fi
done

DASHBOARDS=$(aws cloudwatch list-dashboards --query 'DashboardEntries[*].DashboardName' --output text || true)
for dsh in $DASHBOARDS; do
  [ -z "$dsh" ] || [ "$dsh" = "None" ] && continue
  echo "[$MODE] Borrando dashboard: $dsh"
  if [ "$MODE" = "ejecutar" ]; then
    aws cloudwatch delete-dashboards --dashboard-names "$dsh"
  fi
done

LOG_GROUPS=$(aws logs describe-log-groups --query 'logGroups[*].logGroupName' --output text || true)
for lg in $LOG_GROUPS; do
  [ -z "$lg" ] || [ "$lg" = "None" ] && continue
  if [[ "$lg" == *"/RedshiftEventSubscription"* ]] || [[ "$lg" == *"/RedshiftOverwatch"* ]] || [[ "$lg" == *"/RoleCreationFunction"* ]]; then
    echo "Conservando log group de Lab: $lg"
  else
    echo "[$MODE] Borrando log group: $lg"
    if [ "$MODE" = "ejecutar" ]; then
      aws logs delete-log-group --log-group-name "$lg" || true
    fi
  fi
done

echo ""
echo ">> Paso 11: VPC Endpoints y Security Groups no default..."
VPCE=$(aws ec2 describe-vpc-endpoints --query 'VpcEndpoints[*].VpcEndpointId' --output text || true)
for vpce_id in $VPCE; do
  [ -z "$vpce_id" ] || [ "$vpce_id" = "None" ] && continue
  echo "[$MODE] Borrando VPC endpoint: $vpce_id"
  if [ "$MODE" = "ejecutar" ]; then
    aws ec2 delete-vpc-endpoints --vpc-endpoint-ids "$vpce_id" || true
  fi
done

SGS=$(aws ec2 describe-security-groups --query 'SecurityGroups[?GroupName!=`default`].GroupId' --output text || true)
for sg in $SGS; do
  [ -z "$sg" ] || [ "$sg" = "None" ] && continue
  echo "[$MODE] Borrando Security Group: $sg"
  if [ "$MODE" = "ejecutar" ]; then
    aws ec2 delete-security-group --group-id "$sg" || true
  fi
done

echo ""
echo "=========================================================="
if [ "$MODE" = "ejecutar" ]; then
  echo "Reset finalizado. Tomando inventario posterior..."
  bash "$DIR/tomar_inventario.sh" "$EVIDENCIA_DIR/99_inventario_despues.txt"
else
  echo "Dry-run finalizado. No se borró nada."
fi
echo "=========================================================="
