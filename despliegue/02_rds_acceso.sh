#!/usr/bin/env bash
# Propósito: abrir/cerrar acceso a RDS desde tu laptop (solo tu IP) para cargar datos.
# Uso: ./02_rds_acceso.sh on|off      (cierra con off al terminar)
# Requiere: 01_infra_base.sh ya ejecutado.
source "$(dirname "$0")/lib.sh"
need aws curl
rds_publico "${1:-}"
echo "Listo: acceso $1."
