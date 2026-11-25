import json
import boto3
import os
import sys

session = boto3.Session(region_name="us-east-1")
cw = session.client("cloudwatch")
sns = session.client("sns")

ACCOUNT_ID = session.client("sts").get_caller_identity()["Account"]
TOPIC_NAME = "topico-alertas-cloudwatch-dev"
EMAIL_ENDPOINT = os.environ.get("ALERT_EMAIL")
if not EMAIL_ENDPOINT:
    sys.exit("ERROR: define la variable de entorno ALERT_EMAIL")
# create_topic es idempotente: crea el tópico si no existe y si existe devuelve el mismo ARN
TOPIC_ARN = sns.create_topic(Name=TOPIC_NAME)["TopicArn"]
RDS_INSTANCE = "cs2032-vacantes-dev"
DLQ_NAME = "cola-notificaciones-entrevistas-dlq-dev"
MAIN_QUEUE_NAME = "cola-notificaciones-entrevistas-dev"

API_NAMES = [
    "dev-cs2032-vacantes",
    "dev-cs2032-candidatos",
    "dev-cs2032-entrevistas",
    "dev-cs2032-usuarios",
    "dev-cs2032-reportes"
]

CRITICAL_LAMBDAS = [
    "cs2032-usuarios-dev-loginUsuario",
    "cs2032-usuarios-dev-validarTokenAcceso",
    "cs2032-vacantes-dev-crearPostulacion",
    "cs2032-vacantes-dev-listarVacantes",
    "cs2032-entrevistas-dev-crearEntrevista",
    "cs2032-entrevistas-dev-procesarNotificacion",
    "cs2032-candidatos-dev-crearCandidato",
    "cs2032-reportes-dev-generarReporte"
]

def step1_configure_sns():
    print("[1] Verificando y configurando SNS Topic...")
    # Check topic policy
    attrs = sns.get_topic_attributes(TopicArn=TOPIC_ARN)["Attributes"]
    policy = json.loads(attrs.get("Policy", "{}"))
    
    # Check if CloudWatch publish statement is already present
    has_cw = any(s.get("Sid") == "AllowCloudWatchAlarms" for s in policy.get("Statement", []))
    if not has_cw:
        cw_stmt = {
            "Sid": "AllowCloudWatchAlarms",
            "Effect": "Allow",
            "Principal": {"Service": "cloudwatch.amazonaws.com"},
            "Action": "SNS:Publish",
            "Resource": TOPIC_ARN
        }
        policy.setdefault("Statement", []).append(cw_stmt)
        sns.set_topic_attributes(TopicArn=TOPIC_ARN, AttributeName="Policy", AttributeValue=json.dumps(policy))
        print("  -> Politica de SNS actualizada para permitir envios de CloudWatch Alarms.")
    else:
        print("  -> Politica de SNS ya incluye CloudWatch Alarms.")

    # Check subscriptions
    subs = sns.list_subscriptions_by_topic(TopicArn=TOPIC_ARN)["Subscriptions"]
    sub_emails = [s["Endpoint"] for s in subs if s["Protocol"] == "email"]
    if EMAIL_ENDPOINT not in sub_emails:
        res = sns.subscribe(
            TopicArn=TOPIC_ARN,
            Protocol="email",
            Endpoint=EMAIL_ENDPOINT
        )
        print(f"  -> Suscripcion creada para {EMAIL_ENDPOINT}: {res.get('SubscriptionArn')}")
    else:
        print(f"  -> Suscripcion ya existente para {EMAIL_ENDPOINT}")

def step2_create_alarms():
    print("\n[2] Creando Alarmas de CloudWatch...")
    
    # Alarm 1: DLQ
    print("  -> Creando alarma-dlq-mensajes-visibles-dev...")
    cw.put_metric_alarm(
        AlarmName="alarma-dlq-mensajes-visibles-dev",
        AlarmDescription="Alerta critica: Mensajes detectados en la Dead Letter Queue (DLQ) cola-notificaciones-entrevistas-dlq-dev",
        ActionsEnabled=True,
        AlarmActions=[TOPIC_ARN],
        OKActions=[TOPIC_ARN],
        MetricName="ApproximateNumberOfMessagesVisible",
        Namespace="AWS/SQS",
        Statistic="Sum",
        Dimensions=[{"Name": "QueueName", "Value": DLQ_NAME}],
        Period=60,
        EvaluationPeriods=1,
        DatapointsToAlarm=1,
        Threshold=1.0,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        TreatMissingData="notBreaching"
    )

    # Alarm 2: API Gateway 5XX across all 5 REST APIs
    print("  -> Creando alarma-apigateway-5xx-dev...")
    api_queries = []
    fill_terms = []
    for i, api_name in enumerate(API_NAMES, 1):
        m_id = f"m{i}"
        api_queries.append({
            "Id": m_id,
            "MetricStat": {
                "Metric": {
                    "Namespace": "AWS/ApiGateway",
                    "MetricName": "5XXError",
                    "Dimensions": [{"Name": "ApiName", "Value": api_name}]
                },
                "Period": 300,
                "Stat": "Sum"
            },
            "ReturnData": False
        })
        fill_terms.append(f"FILL({m_id}, 0)")
    
    expr = " + ".join(fill_terms)
    api_queries.append({
        "Id": "e1",
        "Expression": expr,
        "Label": "Total5XXErrorsAllApis",
        "ReturnData": True
    })

    cw.put_metric_alarm(
        AlarmName="alarma-apigateway-5xx-dev",
        AlarmDescription="Alerta critica: Errores 5XX detectados en los endpoints de las 5 APIs REST de API Gateway (>= 1 en 5 min)",
        ActionsEnabled=True,
        AlarmActions=[TOPIC_ARN],
        OKActions=[TOPIC_ARN],
        EvaluationPeriods=1,
        DatapointsToAlarm=1,
        Threshold=1.0,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        TreatMissingData="notBreaching",
        Metrics=api_queries
    )

    # Alarm 3: Lambda Errors for critical functions
    print("  -> Creando alarma-lambda-errores-dev...")
    lambda_queries = []
    l_fill_terms = []
    for i, fn_name in enumerate(CRITICAL_LAMBDAS, 1):
        m_id = f"l{i}"
        lambda_queries.append({
            "Id": m_id,
            "MetricStat": {
                "Metric": {
                    "Namespace": "AWS/Lambda",
                    "MetricName": "Errors",
                    "Dimensions": [{"Name": "FunctionName", "Value": fn_name}]
                },
                "Period": 300,
                "Stat": "Sum"
            },
            "ReturnData": False
        })
        l_fill_terms.append(f"FILL({m_id}, 0)")
    
    l_expr = " + ".join(l_fill_terms)
    lambda_queries.append({
        "Id": "e1",
        "Expression": l_expr,
        "Label": "TotalCriticalLambdaErrors",
        "ReturnData": True
    })

    cw.put_metric_alarm(
        AlarmName="alarma-lambda-errores-dev",
        AlarmDescription="Alerta de errores en funciones Lambda criticas de la plataforma (>= 2 errores en 5 minutos)",
        ActionsEnabled=True,
        AlarmActions=[TOPIC_ARN],
        OKActions=[TOPIC_ARN],
        EvaluationPeriods=1,
        DatapointsToAlarm=1,
        Threshold=2.0,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        TreatMissingData="notBreaching",
        Metrics=lambda_queries
    )

    # Alarm 4: Lambda Throttles
    print("  -> Creando alarma-lambda-throttles-dev...")
    cw.put_metric_alarm(
        AlarmName="alarma-lambda-throttles-dev",
        AlarmDescription="Alerta de estrangulamiento (throttling) de concurrencia en funciones Lambda de la plataforma (>= 1 en 5 minutos)",
        ActionsEnabled=True,
        AlarmActions=[TOPIC_ARN],
        OKActions=[TOPIC_ARN],
        MetricName="Throttles",
        Namespace="AWS/Lambda",
        Statistic="Sum",
        Period=300,
        EvaluationPeriods=1,
        DatapointsToAlarm=1,
        Threshold=1.0,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        TreatMissingData="notBreaching"
    )

    # Alarm 5: RDS High CPU
    print("  -> Creando alarma-rds-cpu-dev...")
    cw.put_metric_alarm(
        AlarmName="alarma-rds-cpu-dev",
        AlarmDescription="Alerta de alto consumo de CPU en la instancia RDS MySQL cs2032-vacantes-dev (>= 80% en 5 minutos)",
        ActionsEnabled=True,
        AlarmActions=[TOPIC_ARN],
        OKActions=[TOPIC_ARN],
        MetricName="CPUUtilization",
        Namespace="AWS/RDS",
        Statistic="Average",
        Dimensions=[{"Name": "DBInstanceIdentifier", "Value": RDS_INSTANCE}],
        Period=300,
        EvaluationPeriods=1,
        DatapointsToAlarm=1,
        Threshold=80.0,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        TreatMissingData="missing"
    )

    # Alarm 6: RDS Database Connections
    print("  -> Creando alarma-rds-conexiones-dev...")
    cw.put_metric_alarm(
        AlarmName="alarma-rds-conexiones-dev",
        AlarmDescription="Alerta de alto numero de conexiones a RDS cs2032-vacantes-dev (>= 60 conexiones concurrentes, limite db.t3.micro)",
        ActionsEnabled=True,
        AlarmActions=[TOPIC_ARN],
        OKActions=[TOPIC_ARN],
        MetricName="DatabaseConnections",
        Namespace="AWS/RDS",
        Statistic="Average",
        Dimensions=[{"Name": "DBInstanceIdentifier", "Value": RDS_INSTANCE}],
        Period=300,
        EvaluationPeriods=1,
        DatapointsToAlarm=1,
        Threshold=60.0,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        TreatMissingData="notBreaching"
    )
    print("  -> Todas las alarmas creadas exitosamente.")

def step3_create_dashboard():
    print("\n[3] Creando Dashboard Centralizado dashboard-cs2032-dev...")
    
    dashboard_body = {
        "widgets": [
            {
                "type": "text",
                "x": 0,
                "y": 0,
                "width": 24,
                "height": 3,
                "properties": {
                    "markdown": "# 📊 CS2032 Serverless Recruitment Platform - Central Monitoring Dashboard\n**Environment:** DEV | **Region:** us-east-1 | **Account:** " + ACCOUNT_ID + "\n*Monitored Subsystems: API Gateway (5 REST APIs), AWS Lambda (30 microservices), Amazon SQS & DLQ, Amazon RDS MySQL (cs2032-vacantes-dev)*"
                }
            },
            {
                "type": "alarm",
                "x": 0,
                "y": 3,
                "width": 24,
                "height": 3,
                "properties": {
                    "title": "🚨 Platform Health & Operational Alarms Status",
                    "alarms": [
                        "arn:aws:cloudwatch:us-east-1:" + ACCOUNT_ID + ":alarm:alarma-dlq-mensajes-visibles-dev",
                        "arn:aws:cloudwatch:us-east-1:" + ACCOUNT_ID + ":alarm:alarma-apigateway-5xx-dev",
                        "arn:aws:cloudwatch:us-east-1:" + ACCOUNT_ID + ":alarm:alarma-lambda-errores-dev",
                        "arn:aws:cloudwatch:us-east-1:" + ACCOUNT_ID + ":alarm:alarma-lambda-throttles-dev",
                        "arn:aws:cloudwatch:us-east-1:" + ACCOUNT_ID + ":alarm:alarma-rds-cpu-dev",
                        "arn:aws:cloudwatch:us-east-1:" + ACCOUNT_ID + ":alarm:alarma-rds-conexiones-dev"
                    ]
                }
            },
            {
                "type": "metric",
                "x": 0,
                "y": 6,
                "width": 12,
                "height": 6,
                "properties": {
                    "title": "📬 SQS DLQ Messages (cola-notificaciones-entrevistas-dlq-dev)",
                    "view": "timeSeries",
                    "stacked": False,
                    "metrics": [
                        ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", DLQ_NAME, {"color": "#d62728", "label": "DLQ Visible Messages"}],
                        [".", "ApproximateNumberOfMessagesNotVisible", ".", ".", {"color": "#ff7f0e", "label": "DLQ In-Flight Messages"}]
                    ],
                    "region": "us-east-1",
                    "period": 60,
                    "stat": "Maximum",
                    "annotations": {
                        "horizontal": [
                            {"value": 1, "color": "#d62728", "label": "Alarm Threshold (>= 1 msg)"}
                        ]
                    }
                }
            },
            {
                "type": "metric",
                "x": 12,
                "y": 6,
                "width": 12,
                "height": 6,
                "properties": {
                    "title": "📬 SQS Main Queue Traffic & Depth (cola-notificaciones-entrevistas-dev)",
                    "view": "timeSeries",
                    "stacked": False,
                    "metrics": [
                        ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", MAIN_QUEUE_NAME, {"color": "#1f77b4", "label": "Queue Depth"}],
                        [".", "NumberOfMessagesSent", ".", ".", {"color": "#2ca02c", "label": "Messages Sent", "stat": "Sum"}],
                        [".", "NumberOfMessagesReceived", ".", ".", {"color": "#9467bd", "label": "Messages Received", "stat": "Sum"}],
                        [".", "NumberOfMessagesDeleted", ".", ".", {"color": "#8c564b", "label": "Messages Processed/Deleted", "stat": "Sum"}]
                    ],
                    "region": "us-east-1",
                    "period": 300,
                    "stat": "Maximum"
                }
            },
            {
                "type": "metric",
                "x": 0,
                "y": 12,
                "width": 12,
                "height": 6,
                "properties": {
                    "title": "🌐 API Gateway - 4XX & 5XX Error Rates Across 5 APIs",
                    "view": "timeSeries",
                    "stacked": False,
                    "metrics": [
                        ["AWS/ApiGateway", "5XXError", "ApiName", "dev-cs2032-vacantes", {"color": "#d62728", "stat": "Sum"}],
                        [".", "5XXError", "ApiName", "dev-cs2032-candidatos", {"color": "#ff9896", "stat": "Sum"}],
                        [".", "5XXError", "ApiName", "dev-cs2032-entrevistas", {"color": "#c5b0d5", "stat": "Sum"}],
                        [".", "5XXError", "ApiName", "dev-cs2032-usuarios", {"color": "#c49c94", "stat": "Sum"}],
                        [".", "5XXError", "ApiName", "dev-cs2032-reportes", {"color": "#f7b6d2", "stat": "Sum"}],
                        [".", "4XXError", "ApiName", "dev-cs2032-vacantes", {"color": "#ff7f0e", "stat": "Sum"}],
                        [".", "4XXError", "ApiName", "dev-cs2032-candidatos", {"color": "#bcbd22", "stat": "Sum"}],
                        [".", "4XXError", "ApiName", "dev-cs2032-entrevistas", {"color": "#17becf", "stat": "Sum"}],
                        [".", "4XXError", "ApiName", "dev-cs2032-usuarios", {"color": "#aec7e8", "stat": "Sum"}],
                        [".", "4XXError", "ApiName", "dev-cs2032-reportes", {"color": "#ffbb78", "stat": "Sum"}]
                    ],
                    "region": "us-east-1",
                    "period": 300
                }
            },
            {
                "type": "metric",
                "x": 12,
                "y": 12,
                "width": 12,
                "height": 6,
                "properties": {
                    "title": "🌐 API Gateway - Total Request Count & Latency",
                    "view": "timeSeries",
                    "stacked": False,
                    "metrics": [
                        ["AWS/ApiGateway", "Count", "ApiName", "dev-cs2032-vacantes", {"stat": "Sum", "label": "Reqs Vacantes"}],
                        [".", "Count", "ApiName", "dev-cs2032-candidatos", {"stat": "Sum", "label": "Reqs Candidatos"}],
                        [".", "Count", "ApiName", "dev-cs2032-entrevistas", {"stat": "Sum", "label": "Reqs Entrevistas"}],
                        [".", "Count", "ApiName", "dev-cs2032-usuarios", {"stat": "Sum", "label": "Reqs Usuarios"}],
                        [".", "Count", "ApiName", "dev-cs2032-reportes", {"stat": "Sum", "label": "Reqs Reportes"}],
                        ["AWS/ApiGateway", "Latency", "ApiName", "dev-cs2032-vacantes", {"yAxis": "right", "stat": "Average", "label": "Latency Vacantes (ms)"}],
                        [".", "Latency", "ApiName", "dev-cs2032-entrevistas", {"yAxis": "right", "stat": "Average", "label": "Latency Entrevistas (ms)"}]
                    ],
                    "region": "us-east-1",
                    "period": 300
                }
            },
            {
                "type": "metric",
                "x": 0,
                "y": 18,
                "width": 8,
                "height": 6,
                "properties": {
                    "title": "⚡ AWS Lambda - Invocations (Critical Services)",
                    "view": "timeSeries",
                    "stacked": False,
                    "metrics": [
                        ["AWS/Lambda", "Invocations", "FunctionName", "cs2032-usuarios-dev-loginUsuario", {"stat": "Sum"}],
                        [".", "Invocations", "FunctionName", "cs2032-vacantes-dev-crearPostulacion", {"stat": "Sum"}],
                        [".", "Invocations", "FunctionName", "cs2032-entrevistas-dev-crearEntrevista", {"stat": "Sum"}],
                        [".", "Invocations", "FunctionName", "cs2032-entrevistas-dev-procesarNotificacion", {"stat": "Sum"}],
                        [".", "Invocations", "FunctionName", "cs2032-candidatos-dev-crearCandidato", {"stat": "Sum"}],
                        [".", "Invocations", "FunctionName", "cs2032-reportes-dev-generarReporte", {"stat": "Sum"}]
                    ],
                    "region": "us-east-1",
                    "period": 300
                }
            },
            {
                "type": "metric",
                "x": 8,
                "y": 18,
                "width": 8,
                "height": 6,
                "properties": {
                    "title": "⚡ AWS Lambda - Errors & Throttles",
                    "view": "timeSeries",
                    "stacked": False,
                    "metrics": [
                        ["AWS/Lambda", "Errors", {"stat": "Sum", "color": "#d62728", "label": "Global Lambda Errors"}],
                        [".", "Throttles", {"stat": "Sum", "color": "#ff7f0e", "label": "Global Lambda Throttles"}],
                        ["AWS/Lambda", "Errors", "FunctionName", "cs2032-entrevistas-dev-procesarNotificacion", {"stat": "Sum", "label": "Errors procesarNotificacion"}],
                        [".", "Errors", "FunctionName", "cs2032-vacantes-dev-crearPostulacion", {"stat": "Sum", "label": "Errors crearPostulacion"}],
                        [".", "Errors", "FunctionName", "cs2032-usuarios-dev-loginUsuario", {"stat": "Sum", "label": "Errors loginUsuario"}]
                    ],
                    "region": "us-east-1",
                    "period": 300,
                    "annotations": {
                        "horizontal": [
                            {"value": 2, "color": "#d62728", "label": "Error Alarm Threshold (>= 2)"}
                        ]
                    }
                }
            },
            {
                "type": "metric",
                "x": 16,
                "y": 18,
                "width": 8,
                "height": 6,
                "properties": {
                    "title": "⚡ AWS Lambda - Execution Duration (p50, p95, Average)",
                    "view": "timeSeries",
                    "stacked": False,
                    "metrics": [
                        ["AWS/Lambda", "Duration", "FunctionName", "cs2032-usuarios-dev-loginUsuario", {"stat": "Average", "label": "Avg loginUsuario (ms)"}],
                        [".", "Duration", "FunctionName", "cs2032-entrevistas-dev-procesarNotificacion", {"stat": "Average", "label": "Avg procesarNotificacion (ms)"}],
                        [".", "Duration", "FunctionName", "cs2032-vacantes-dev-crearPostulacion", {"stat": "p95", "label": "p95 crearPostulacion (ms)"}],
                        [".", "Duration", "FunctionName", "cs2032-reportes-dev-generarReporte", {"stat": "Average", "label": "Avg generarReporte (ms)"}]
                    ],
                    "region": "us-east-1",
                    "period": 300
                }
            },
            {
                "type": "metric",
                "x": 0,
                "y": 24,
                "width": 12,
                "height": 6,
                "properties": {
                    "title": "🗄️ Amazon RDS - CPU Utilization (cs2032-vacantes-dev)",
                    "view": "timeSeries",
                    "stacked": False,
                    "metrics": [
                        ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", RDS_INSTANCE, {"color": "#1f77b4", "label": "CPU Utilization (%)"}]
                    ],
                    "region": "us-east-1",
                    "period": 300,
                    "stat": "Average",
                    "yAxis": {
                        "left": {
                            "min": 0,
                            "max": 100
                        }
                    },
                    "annotations": {
                        "horizontal": [
                            {"value": 80, "color": "#d62728", "label": "High CPU Alarm Threshold (80%)"}
                        ]
                    }
                }
            },
            {
                "type": "metric",
                "x": 12,
                "y": 24,
                "width": 12,
                "height": 6,
                "properties": {
                    "title": "🗄️ Amazon RDS - Database Connections & Freeable Memory",
                    "view": "timeSeries",
                    "stacked": False,
                    "metrics": [
                        ["AWS/RDS", "DatabaseConnections", "DBInstanceIdentifier", RDS_INSTANCE, {"color": "#ff7f0e", "label": "Active DB Connections", "stat": "Average"}],
                        [".", "FreeableMemory", ".", ".", {"yAxis": "right", "color": "#2ca02c", "label": "Freeable Memory (Bytes)", "stat": "Average"}]
                    ],
                    "region": "us-east-1",
                    "period": 300,
                    "annotations": {
                        "horizontal": [
                            {"value": 60, "color": "#d62728", "label": "Connection Alarm Threshold (>= 60)"}
                        ]
                    }
                }
            }
        ]
    }
    
    res = cw.put_dashboard(
        DashboardName="dashboard-cs2032-dev",
        DashboardBody=json.dumps(dashboard_body)
    )
    print("  -> Dashboard put_dashboard response:", res)

if __name__ == "__main__":
    step1_configure_sns()
    step2_create_alarms()
    step3_create_dashboard()
    print("\n✅ Proceso completado exitosamente.")
