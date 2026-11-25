#!/usr/bin/env bash
# Script para recolectar el inventario completo de la cuenta AWS
# Guarda la salida en el archivo especificado como primer argumento.
set -euo pipefail

OUT="${1:-despliegue/evidencia_reset/inventario.txt}"
mkdir -p "$(dirname "$OUT")"

exec > >(tee "$OUT") 2>&1

echo "========================================================"
echo "INVENTARIO DE RECURSOS AWS - $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "========================================================"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
CALLER_ARN=$(aws sts get-caller-identity --query Arn --output text)
echo "Cuenta: $ACCOUNT_ID"
echo "Identidad: $CALLER_ARN"
echo "Región: ${AWS_DEFAULT_REGION:-us-east-1}"
echo ""

echo "--- 1. CLOUDFORMATION STACKS ---"
aws cloudformation list-stacks --stack-status-filter \
  CREATE_IN_PROGRESS CREATE_FAILED CREATE_COMPLETE ROLLBACK_IN_PROGRESS ROLLBACK_FAILED ROLLBACK_COMPLETE DELETE_FAILED UPDATE_IN_PROGRESS UPDATE_COMPLETE_CLEANUP_IN_PROGRESS UPDATE_COMPLETE UPDATE_FAILED UPDATE_ROLLBACK_IN_PROGRESS UPDATE_ROLLBACK_FAILED UPDATE_ROLLBACK_COMPLETE \
  --query 'StackSummaries[*].{Name:StackName,Status:StackStatus}' --output table || true

echo ""
echo "--- 2. LAMBDA FUNCTIONS ---"
aws lambda list-functions --query 'Functions[*].{Name:FunctionName,Runtime:Runtime}' --output table || true

echo ""
echo "--- 3. API GATEWAY (REST & HTTP/V2) ---"
echo "[REST APIs (v1)]"
aws apigateway get-rest-apis --query 'items[*].{Id:id,Name:name}' --output table || true
echo "[HTTP/Websocket APIs (v2)]"
aws apigatewayv2 get-apis --query 'Items[*].{Id:ApiId,Name:Name,Protocol:ProtocolType}' --output table || true

echo ""
echo "--- 4. DYNAMODB TABLES ---"
aws dynamodb list-tables --query 'TableNames[*]' --output table || true

echo ""
echo "--- 5. S3 BUCKETS ---"
BUCKETS=$(aws s3api list-buckets --query 'Buckets[*].Name' --output text 2>/dev/null || true)
if [ -n "$BUCKETS" ] && [ "$BUCKETS" != "None" ]; then
  for b in $BUCKETS; do
    echo "Bucket: $b"
    echo "  Versioning:"
    aws s3api get-bucket-versioning --bucket "$b" --output json || true
    echo "  Summary:"
    aws s3 ls "s3://$b" --summarize --recursive 2>/dev/null | tail -n 2 || true
  done
else
  echo "No S3 buckets found."
fi

echo ""
echo "--- 6. RDS (INSTANCES, CLUSTERS, SNAPSHOTS, SUBNET GROUPS) ---"
echo "[DB Instances]"
aws rds describe-db-instances --query 'DBInstances[*].{ID:DBInstanceIdentifier,Engine:Engine,Status:DBInstanceStatus}' --output table || true
echo "[DB Clusters]"
aws rds describe-db-clusters --query 'DBClusters[*].{ID:DBClusterIdentifier,Engine:Engine,Status:Status}' --output table || true
echo "[Manual DB Snapshots]"
aws rds describe-db-snapshots --snapshot-type manual --query 'DBSnapshots[*].{ID:DBSnapshotIdentifier,Status:Status}' --output table || true
echo "[DB Subnet Groups]"
aws rds describe-db-subnet-groups --query 'DBSubnetGroups[*].{Name:DBSubnetGroupName,VpcId:VpcId}' --output table || true

echo ""
echo "--- 7. EC2 & NETWORKING ---"
echo "[EC2 Instances]"
aws ec2 describe-instances --query 'Reservations[*].Instances[*].{Id:InstanceId,State:State.Name,Type:InstanceType,Name:Tags[?Key==`Name`].Value|[0]}' --output table || true
echo "[EBS Volumes]"
aws ec2 describe-volumes --query 'Volumes[*].{Id:VolumeId,Size:Size,State:State,Attachments:Attachments[0].InstanceId}' --output table || true
echo "[Own EBS Snapshots]"
aws ec2 describe-snapshots --owner-ids self --query 'Snapshots[*].{Id:SnapshotId,VolumeId:VolumeId,State:State}' --output table || true
echo "[Own AMIs]"
aws ec2 describe-images --owners self --query 'Images[*].{Id:ImageId,Name:Name}' --output table || true
echo "[Key Pairs]"
aws ec2 describe-key-pairs --query 'KeyPairs[*].{Name:KeyName,Id:KeyPairId}' --output table || true
echo "[Elastic IPs]"
aws ec2 describe-addresses --query 'Addresses[*].{AllocationId:AllocationId,PublicIp:PublicIp,InstanceId:InstanceId}' --output table || true
echo "[NAT Gateways]"
aws ec2 describe-nat-gateways --query 'NatGateways[?State!=`deleted`].{Id:NatGatewayId,State:State,VpcId:VpcId}' --output table || true
echo "[Network Interfaces (ENIs)]"
aws ec2 describe-network-interfaces --query 'NetworkInterfaces[*].{Id:NetworkInterfaceId,Status:Status,Description:Description,PrivateIp:PrivateIpAddress}' --output table || true

echo ""
echo "--- 8. ELB (LOAD BALANCERS) ---"
aws elbv2 describe-load-balancers --query 'LoadBalancers[*].{Name:LoadBalancerName,Type:Type,VpcId:VpcId}' --output table 2>/dev/null || true
aws elb describe-load-balancers --query 'LoadBalancerDescriptions[*].{Name:LoadBalancerName,VpcId:VpcId}' --output table 2>/dev/null || true

echo ""
echo "--- 9. ECR REPOSITORIES ---"
aws ecr describe-repositories --query 'repositories[*].{Name:repositoryName,Uri:repositoryUri}' --output table 2>/dev/null || true

echo ""
echo "--- 10. SECRETS MANAGER ---"
aws secretsmanager list-secrets --query 'SecretList[*].{Name:Name,Description:Description}' --output table 2>/dev/null || true

echo ""
echo "--- 11. EVENTBRIDGE RULES ---"
aws events list-rules --query 'Rules[*].{Name:Name,State:State}' --output table || true

echo ""
echo "--- 12. REDSHIFT / GLUE / KINESIS ---"
aws redshift describe-clusters --query 'Clusters[*].{Id:ClusterIdentifier,Status:ClusterStatus}' --output table 2>/dev/null || true
aws glue get-databases --query 'DatabaseList[*].Name' --output table 2>/dev/null || true
aws kinesis list-streams --query 'StreamNames[*]' --output table 2>/dev/null || true

echo ""
echo "--- 13. SQS & SNS ---"
echo "[SQS Queues]"
aws sqs list-queues --query 'QueueUrls[*]' --output table || true
echo "[SNS Topics]"
aws sns list-topics --query 'Topics[*].TopicArn' --output table || true
echo "[SNS Subscriptions]"
aws sns list-subscriptions --query 'Subscriptions[*].{TopicArn:TopicArn,Protocol:Protocol,Endpoint:Endpoint}' --output table || true

echo ""
echo "--- 14. SYSTEMS MANAGER (SSM) PARAMETERS ---"
aws ssm describe-parameters --query 'Parameters[*].{Name:Name,Type:Type}' --output table || true

echo ""
echo "--- 15. CLOUDWATCH (ALARMS, DASHBOARDS, LOG GROUPS) ---"
echo "[Alarms]"
aws cloudwatch describe-alarms --query 'MetricAlarms[*].{Name:AlarmName,State:StateValue}' --output table || true
echo "[Dashboards]"
aws cloudwatch list-dashboards --query 'DashboardEntries[*].DashboardName' --output table || true
echo "[Log Groups]"
aws logs describe-log-groups --query 'logGroups[*].logGroupName' --output table || true

echo ""
echo "--- 16. VPC, SECURITY GROUPS & ENDPOINTS ---"
echo "[VPCs]"
aws ec2 describe-vpcs --query 'Vpcs[*].{Id:VpcId,IsDefault:IsDefault,Cidr:CidrBlock}' --output table || true
echo "[VPC Endpoints]"
aws ec2 describe-vpc-endpoints --query 'VpcEndpoints[*].{Id:VpcEndpointId,ServiceName:ServiceName,State:State}' --output table || true
echo "[Security Groups]"
aws ec2 describe-security-groups --query 'SecurityGroups[*].{Id:GroupId,Name:GroupName,VpcId:VpcId}' --output table || true

echo ""
echo "--- 17. IAM (USERS & NON-SERVICE ROLES) ---"
echo "[IAM Users]"
aws iam list-users --query 'Users[*].{Name:UserName,Id:UserId}' --output table || true
echo "[IAM Roles (non-service)]"
aws iam list-roles --query 'Roles[?!starts_with(Path, `/aws-service-role/`)].{Name:RoleName,Path:Path}' --output table || true

echo "========================================================"
echo "FIN DEL INVENTARIO"
echo "========================================================"
