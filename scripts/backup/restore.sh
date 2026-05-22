#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# HVAC Platform Database Restore Script
#
# Restores a PostgreSQL/TimescaleDB database from a pg_dump custom-format
# (.dump) file.  The target database is dropped and recreated before restore.
#
# Usage:
#   ./restore.sh --file backups/2026-05-22/asset_db_2026-05-22_120000.dump --db asset_db
#   ./restore.sh -f ./my.dump -d health_db
# ---------------------------------------------------------------------------

set -euo pipefail

# ── Color helpers ───────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Configuration ───────────────────────────────────────────────────────────
DB_USER="${DB_USER:-hvac}"
DB_PASSWORD="${DB_PASSWORD:-hvac_dev}"
export PGPASSWORD="$DB_PASSWORD"

# ── Defaults ────────────────────────────────────────────────────────────────
DUMP_FILE=""
DB_NAME=""
SKIP_CONFIRM=false

# ── Usage ───────────────────────────────────────────────────────────────────
usage() {
  cat <<EOF
Usage: $0 --file <dump_path> --db <name> [OPTIONS]

Required:
  -f, --file <path>      Path to the .dump file created by backup.sh.
  -d, --db <name>        Target database name (asset_db, energy_db, etc.).

Options:
  -y, --yes              Skip confirmation prompt (useful for automation).
  -h, --help             Show this help message.

Available database names:
  asset_db   env_db    sim_db     agent_db
  acq_db     edge_db   energy_db  health_db

Examples:
  $0 -f ./backups/2026-05-22/energy_db_2026-05-22_120000.dump -d energy_db
  $0 -f ./health.dump -d health_db -y   # skip confirmation
EOF
  exit 0
}

# ── Parse arguments ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    -f|--file)
      DUMP_FILE="$2"
      shift 2
      ;;
    -d|--db)
      DB_NAME="$2"
      shift 2
      ;;
    -y|--yes)
      SKIP_CONFIRM=true
      shift
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo -e "${RED}[ERROR]${NC} Unknown option: $1"
      usage
      ;;
  esac
done

# ── Validation ──────────────────────────────────────────────────────────────
if [[ -z "$DUMP_FILE" ]]; then
  echo -e "${RED}[ERROR]${NC} --file is required"
  usage
fi

if [[ -z "$DB_NAME" ]]; then
  echo -e "${RED}[ERROR]${NC} --db is required"
  usage
fi

if [[ ! -f "$DUMP_FILE" ]]; then
  echo -e "${RED}[ERROR]${NC} Dump file not found: ${DUMP_FILE}"
  exit 1
fi

# ── Container resolution (same logic as backup.sh) ──────────────────────────
get_service_name() {
  local db="$1"
  local override_var="CONTAINER_${db}"
  if [[ -n "${!override_var:-}" ]]; then
    echo "${!override_var}"
    return
  fi
  case "$db" in
    asset_db)   echo "postgres_asset" ;;
    env_db)     echo "timescaledb" ;;
    sim_db)     echo "postgres_sim" ;;
    agent_db)   echo "postgres_agent" ;;
    acq_db)     echo "timescaledb_acq" ;;
    edge_db)    echo "postgres_edge" ;;
    energy_db)  echo "energy_db" ;;
    health_db)  echo "health_db" ;;
    *)
      echo -e "${RED}[ERROR]${NC} Unknown database: $db" >&2
      echo ""
      ;;
  esac
}

resolve_container() {
  local db="$1"
  local service
  service=$(get_service_name "$db")
  [[ -z "$service" ]] && return 1

  local running
  running=$(docker ps --format '{{.Names}}' 2>/dev/null)

  # 1) Exact match
  if echo "$running" | grep -qFx "$service"; then
    echo "$service"
    return 0
  fi

  # 2) Containers containing the service name
  local match
  match=$(echo "$running" | grep -F "$service" | head -1 || true)
  if [[ -n "$match" ]]; then
    echo "$match"
    return 0
  fi

  # 3) Docker Compose project-style naming
  match=$(echo "$running" | grep -E "_${service}_[0-9]+$" | head -1 || true)
  if [[ -n "$match" ]]; then
    echo "$match"
    return 0
  fi

  # 4) Stopped container lookup
  match=$(docker ps -a --format '{{.Names}}' 2>/dev/null | grep -E "(^|_)${service}(_[0-9]+)?$" | head -1 || true)
  if [[ -n "$match" ]]; then
    echo "$match"
    return 0
  fi

  return 1
}

# ── Resolve target container ────────────────────────────────────────────────
SERVICE_NAME=$(get_service_name "$DB_NAME")
if [[ -z "$SERVICE_NAME" ]]; then
  echo -e "${RED}[ERROR]${NC} Unknown database: ${DB_NAME}"
  exit 1
fi

CONTAINER=$(resolve_container "$DB_NAME") || true
if [[ -z "$CONTAINER" ]]; then
  echo -e "${RED}[ERROR]${NC} No container found for ${DB_NAME} (service: ${SERVICE_NAME})"
  echo ""
  echo "  Make sure the database container is created (even if stopped)."
  echo "  You may need to run: docker compose up -d ${SERVICE_NAME}"
  exit 1
fi

# Ensure container is running
if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -qFx "$CONTAINER"; then
  echo -e "${YELLOW}[WARN]${NC} Container '${CONTAINER}' is not running. Starting it..."
  if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qFx "$CONTAINER"; then
    if ! docker start "$CONTAINER" >/dev/null 2>&1; then
      echo -e "${RED}[ERROR]${NC} Cannot start container ${CONTAINER}"
      exit 1
    fi
    echo -n "  Waiting for PostgreSQL..."
    waited=0
    while ! docker exec "$CONTAINER" pg_isready -U "$DB_USER" >/dev/null 2>&1; do
      sleep 1
      waited=$((waited + 1))
      if [[ $waited -ge 30 ]]; then
        echo ""
        echo -e "${RED}[ERROR]${NC} PostgreSQL did not become ready within 30s"
        exit 1
      fi
    done
    echo " ready"
  else
    echo -e "${RED}[ERROR]${NC} Container '${CONTAINER}' does not exist."
    echo "  Run: docker compose up -d ${SERVICE_NAME}"
    exit 1
  fi
fi

# ── Confirmation ────────────────────────────────────────────────────────────
DUMP_SIZE=$(du -h "$DUMP_FILE" 2>/dev/null | cut -f1)

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║     HVAC Platform Database Restore                   ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Target DB : ${BOLD}${DB_NAME}${NC}"
echo -e "  Container : ${CONTAINER}"
echo -e "  Dump file : ${DUMP_FILE} (${DUMP_SIZE})"
echo ""
echo -e "${RED}${BOLD}  WARNING: This will DROP and RECREATE the database!${NC}"
echo -e "${RED}           All current data in ${DB_NAME} will be lost.${NC}"
echo ""

if [[ "$SKIP_CONFIRM" == false ]]; then
  read -r -p "  Type 'yes' to confirm restore: " confirm
  if [[ "$confirm" != "yes" ]]; then
    echo -e "${YELLOW}[ABORT]${NC} Restore cancelled."
    exit 0
  fi
  echo ""
fi

# ── Drop & recreate database ────────────────────────────────────────────────
echo -e "${CYAN}[STEP]${NC} Dropping existing database ${DB_NAME}..."

# Terminate existing connections before drop
docker exec "$CONTAINER" psql -U "$DB_USER" -d postgres -c \
  "SELECT pg_terminate_backend(pg_stat_activity.pid)
   FROM pg_stat_activity
   WHERE pg_stat_activity.datname = '${DB_NAME}'
     AND pid <> pg_backend_pid();" >/dev/null 2>&1 || true

if docker exec "$CONTAINER" psql -U "$DB_USER" -d postgres -c \
    "DROP DATABASE IF EXISTS \"${DB_NAME}\";" >/dev/null 2>&1; then
  echo -e "${GREEN}[ OK ]${NC} Database ${DB_NAME} dropped"
else
  echo -e "${RED}[FAIL]${NC} Could not drop database ${DB_NAME}"
  exit 1
fi

echo -e "${CYAN}[STEP]${NC} Creating fresh database ${DB_NAME}..."

if docker exec "$CONTAINER" psql -U "$DB_USER" -d postgres -c \
    "CREATE DATABASE \"${DB_NAME}\" OWNER \"${DB_USER}\";" >/dev/null 2>&1; then
  echo -e "${GREEN}[ OK ]${NC} Database ${DB_NAME} created"
else
  echo -e "${RED}[FAIL]${NC} Could not create database ${DB_NAME}"
  exit 1
fi

# ── Restore ─────────────────────────────────────────────────────────────────
echo -e "${CYAN}[STEP]${NC} Restoring ${DB_NAME} from ${DUMP_FILE}..."

# pg_restore with:
#   -c  clean (drop) objects before recreating them
#   -O  skip ownership (restore as hvac user)
#   -x  skip ACL grants (avoid permission errors in dev)
RESTORE_ERR=$(docker exec -i "$CONTAINER" \
  pg_restore -U "$DB_USER" -d "$DB_NAME" -c -O -x < "$DUMP_FILE" 2>&1) \
  && restore_ok=true || restore_ok=false

if [[ "$restore_ok" == true ]]; then
  echo -e "${GREEN}[ OK ]${NC} Restore completed successfully"
else
  # pg_restore often emits warnings that go to stderr but aren't fatal.
  # Check if the database has tables as a sanity check.
  table_count=$(docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tAc \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema');" 2>/dev/null || echo "0")
  if [[ "$table_count" -gt 0 ]]; then
    echo -e "${GREEN}[ OK ]${NC} Restore completed (${table_count} tables, warnings ignored)"
  else
    echo -e "${RED}[FAIL]${NC} Restore produced no tables. stderr output:"
    echo "$RESTORE_ERR" | tail -20
    exit 1
  fi
fi

echo ""
echo -e "${GREEN}${BOLD}Restore finished: ${DB_NAME}${NC}"
exit 0
