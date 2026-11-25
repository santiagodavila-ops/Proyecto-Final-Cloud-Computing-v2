#!/usr/bin/env bash
# Crea los administradores iniciales y carga datos ficticios (DynamoDB) + migra vacantes/postulaciones a RDS.
# Uso: bash despliegue/03_datos.sh [cantidad_por_tenant]   (default 10000; sugerido 1000 para pruebas rápidas)
# Orden: admins -> candidatos -> vacantes/postulaciones -> entrevistas -> reportes -> RDS (schema + migración).
set -euo pipefail
source "$(dirname "$0")/lib.sh"
[ -f "$DIR/.env.local" ] || { echo "Falta $DIR/.env.local: corre primero 01 y 02"; exit 1; }
CANTIDAD="${1:-10000}"
SVC="$REPO/microservicios"

set_env() { grep -v "^$1=" "$DIR/.env.local" > "$DIR/.env.local.tmp" || true; echo "$1=$2" >> "$DIR/.env.local.tmp"; mv "$DIR/.env.local.tmp" "$DIR/.env.local"; }
set -a; source "$DIR/.env.local"; set +a

echo "==> Preparando venv local (faker, pymysql, boto3)"
[ -d "$DIR/.venv" ] || python3 -m venv "$DIR/.venv"
"$DIR/.venv/bin/pip" install -q faker pymysql boto3
PY="$DIR/.venv/bin/python"

if [ -z "${ADMIN_PASSWORD:-}" ]; then
  ADMIN_PASSWORD=$("$PY" -c 'import secrets; print(secrets.token_urlsafe(12))')
  set_env ADMIN_PASSWORD "$ADMIN_PASSWORD"
  echo "    ADMIN_PASSWORD generada y guardada en despliegue/.env.local"
fi
export ADMIN_PASSWORD

echo "==> [1/6] Administradores iniciales (admin@tenant{1,2,3}.example)"
"$PY" "$DIR/seed_admin.py" "$STAGE"

echo "==> [2/6] Candidatos ($CANTIDAD por tenant)  -- debe ir antes que vacantes y entrevistas"
(cd "$SVC/cs2032-final-candidatos" && "$PY" scripts/cargar_datos.py "$STAGE" "$CANTIDAD")

echo "==> [3/6] Vacantes y postulaciones en DynamoDB (leen candidatos)"
(cd "$SVC/cs2032-final-vacantes" && "$PY" scripts/cargar_datos.py "$STAGE" "$CANTIDAD")

echo "==> [4/6] Entrevistas (leen postulaciones)"
(cd "$SVC/cs2032-final-entrevistas" && "$PY" scripts/cargar_datos.py "$STAGE" "$CANTIDAD")

echo "==> [5/6] Reportes históricos"
(cd "$SVC/cs2032-final-reportes" && "$PY" scripts/cargar_datos.py "$STAGE" "$CANTIDAD")

echo "==> [6/6] RDS: schemas por tenant y migración desde DynamoDB"
bash "$DIR/02_rds_acceso.sh" on
trap 'bash "$DIR/02_rds_acceso.sh" off' EXIT
export RDS_USER RDS_PASSWORD RDS_PORT
RDS_USER=$(aws ssm get-parameter --region "$REGION" --name "/cs2032/$STAGE/rds/user" --with-decryption --query Parameter.Value --output text)
RDS_PASSWORD=$(aws ssm get-parameter --region "$REGION" --name "/cs2032/$STAGE/rds/password" --with-decryption --query Parameter.Value --output text)
RDS_PORT=$(aws ssm get-parameter --region "$REGION" --name "/cs2032/$STAGE/rds/port" --with-decryption --query Parameter.Value --output text)
RDS_PORT="${RDS_PORT:-3306}"
export VACANTES_TABLE="t_vacantes-$STAGE" POSTULACIONES_TABLE="t_postulaciones-$STAGE"
# schema.sql es idempotente (CREATE ... IF NOT EXISTS); migrar_a_rds.py exige que las tablas existan
"$PY" - "$SVC/cs2032-final-vacantes/sql/schema.sql" <<'PYEOF'
import os, sys, pymysql
c = pymysql.connect(host=os.environ["RDS_HOST"], user=os.environ["RDS_USER"],
                    password=os.environ["RDS_PASSWORD"], port=int(os.environ["RDS_PORT"]), connect_timeout=15)
sql = "\n".join(l for l in open(sys.argv[1]) if not l.lstrip().startswith("--"))
with c.cursor() as cur:
    for stmt in filter(None, (s.strip() for s in sql.split(";"))):
        cur.execute(stmt)
c.commit()
print("    schema.sql aplicado")
PYEOF
(cd "$SVC/cs2032-final-vacantes" && "$PY" scripts/migrar_a_rds.py)

echo "==> Datos cargados. Login: admin@tenant1.example / (ADMIN_PASSWORD en despliegue/.env.local)"
