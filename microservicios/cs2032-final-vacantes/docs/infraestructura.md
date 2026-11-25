# Infraestructura: VPC Endpoint de DynamoDB

- El endpoint Gateway de DynamoDB ahora está definido en `serverless.yml` (recurso `EndpointDynamoDB`, CloudFormation).
- Antes se creó a mano por CLI: `vpce-07b8eb29ed8017464` (VPC `vpc-0fac6f2d1ab59f1fa`, tabla de rutas `rtb-08cd040502a7dacae`).
- AWS no permite dos endpoints Gateway del mismo servicio en la misma VPC, así que hay que eliminar el manual ANTES del primer deploy:

```
aws ec2 delete-vpc-endpoints --region us-east-1 --vpc-endpoint-ids vpce-07b8eb29ed8017464
```

- Variables requeridas al desplegar: `RDS_VPC_ID` y `RDS_ROUTE_TABLE_IDS` (separadas por coma). El endpoint es gratuito.
