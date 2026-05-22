#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# HVAC Platform Database Backup Script
#
# Backs up PostgreSQL/TimescaleDB databases running in Docker containers.
# Each dump is created as a pg_dump custom-format (.dump) file with
# compression, suitable for pg_restore.
#
# Usage:
#   ./backup.sh                         # Backup all databases
#   ./backup.sh --all                   # Backup all databases (explicit)
#   ./backup.sh --db asset_db           # Backup a single database
#   ./backup.sh --output-dir /var/bak   # Custom output directory
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
DO_ALL=true
DB_SINGLE=""
OUTPUT_DIR=""

# ── Usage ───────────────────────────────────────────────────────────────────
usage() {
  cat <<EOF
Usage: $0 [OPTIONS]

Options:
  --all                  Backup all databases (default).
  --db <name>            Backup a single database by name.
  --output-dir <path>    Write dumps to this directory
                         (default: ./backups/YYYY-MM-DD/).
  -h, --help             Show this help message.

Available database names:
  asset_db   env_db    sim_db     agent_db
  acq_db     edge_db   energy_db  health_db
EOF
  exit 0
}

# ── Parse arguments ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --db)
      DB_SINGLE="$2"
      DO_ALL=false
      shift 2
      ;;
    --all)
      DO_ALL=true
      shift
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
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

# ── Timestamp & output directory ────────────────────────────────────────────
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)
DATE_DIR=$(date +%Y-%m-%d)

if [[ -z "$OUTPUT_DIR" ]]; then
  OUTPUT_DIR="./backups/${DATE_DIR}"
fi
mkdir -p "$OUTPUT_DIR"

# ── Database → container mapping ────────────────────────────────────────────
# Maps each logical database name to its docker-compose service name.
# If containers were started via "docker compose", actual container names
# may include a project prefix (e.g. hvac-agents-postgres_asset-1).
# The resolve_container function below handles this transparently.
#
# If your containers use different names, either:
#   1. Set CONTAINER_<db> env vars, e.g. CONTAINER_asset_db=my_custom_name
#   2. Edit the case statement below

get_service_name() {
  local db="$1"
  # Allow per-DB override via environment
  local override_var="CONTAINER_${db}"
  if [[ -n "${!override_var:-}" ]]; then
    echo "${!override_var}"
    return
  fi
  # Default docker-compose service names
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

# Resolve a database name to an actual running container name.
# Tries (in order):
#   1. Exact match on running containers
#   2. Containers whose name contains the service name
#   3. Docker Compose project-style name: <project>_<service>_1
resolve_container() {
  local db="$1"
  local service
  service=$(get_service_name "$db")
  [[ -z "$service" ]] && return 1

  # Get all running container names
  local running
  running=$(docker ps --format '{{.Names}}' 2>/dev/null)

  # 1) Exact match
  if echo "$running" | grep -qFx "$service"; then
    echo "$service"
    return 0
  fi

  # 2) Match container names that contain the service name
  local match
  match=$(echo "$running" | grep -F "$service" | head -1 || true)
  if [[ -n "$match" ]]; then
    echo "$match"
    return 0
  fi

  # 3) Try docker-compose project-style name (any prefix_<service>_N)
  match=$(echo "$running" | grep -E "_${service}_[0-9]+$" | head -1 || true)
  if [[ -n "$match" ]]; then
    echo "$match"
    return 0
  fi

  # 4) Check if container exists but is stopped; try to find it
  match=$(docker ps -a --format '{{.Names}}' 2>/dev/null | grep -E "(^|_)${service}(_[0-9]+)?$" | head -1 || true)
  if [[ -n "$match" ]]; then
    echo "$match"
    return 0
  fi

  return 1
}

# ── Database list ───────────────────────────────────────────────────────────
ALL_DBS=("asset_db" "env_db" "sim_db" "agent_db" "acq_db" "edge_db" "energy_db" "health_db")

if [[ "$DO_ALL" == true ]]; then
  DBS=("${ALL_DBS[@]}")
else
  # Validate single DB name
  found=false
  for db in "${ALL_DBS[@]}"; do
    if [[ "$db" == "$DB_SINGLE" ]]; then
      found=true
      break
    fi
  done
  if [[ "$found" == false ]]; then
    echo -e "${RED}[ERROR]${NC} Unknown database: ${DB_SINGLE}"
    echo "Valid names: ${ALL_DBS[*]}"
    exit 1
  fi
  DBS=("$DB_SINGLE")
fi
TOTAL=${#DBS[@]}

# ── Backup a single database ────────────────────────────────────────────────
backup_one() {
  local db_name="$1"

  # Resolve container
  local container
  if ! container=$(resolve_container "$db_name"); then
    echo -e "${RED}[FAIL]${NC} ${db_name}: no container found (service: $(get_service_name "$db_name"))"
    return 1
  fi

  local dump_file="${db_name}_${TIMESTAMP}.dump"
  local container_tmp="/tmp/${dump_file}"
  local output_path="${OUTPUT_DIR}/${dump_file}"

  # Ensure container is running
  if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -qFx "$container"; then
    echo -e "${YELLOW}[WARN]${NC} ${db_name}: container '${container}' is not running"
    if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qFx "$container"; then
      echo -e "       Starting container ${container}..."
      if ! docker start "$container" >/dev/null 2>&1; then
        echo -e "${RED}[FAIL]${NC} ${db_name}: cannot start container ${container}"
        return 1
      fi
      # Wait for PostgreSQL to become ready
      echo -n "       Waiting for PostgreSQL..."
      local waited=0
      while ! docker exec "$container" pg_isready -U "$DB_USER" -d "$db_name" >/dev/null 2>&1; do
        sleep 1
        waited=$((waited + 1))
        if [[ $waited -ge 30 ]]; then
          echo ""
          echo -e "${RED}[FAIL]${NC} ${db_name}: PostgreSQL did not become ready within 30s"
          return 1
        fi
      done
      echo " ready"
    else
      echo -e "${RED}[FAIL]${NC} ${db_name}: container '${container}' does not exist"
      return 1
    fi
  fi

  echo -e "${CYAN}[INFO]${NC} Backing up ${BOLD}${db_name}${NC} from container ${container}..."

  # Run pg_dump inside the container (custom format, compressed)
  local pg_dump_err
  pg_dump_err=$(docker exec "$container" \
    pg_dump -U "$DB_USER" -d "$db_name" -Fc -f "$container_tmp" 2>&1) \
    && pg_dump_ok=true || pg_dump_ok=false

  if [[ "$pg_dump_ok" == false ]]; then
    echo -e "${RED}[FAIL]${NC} ${db_name}: pg_dump error"
    echo "       ${pg_dump_err}"
    return 1
  fi

  # Copy dump out of the container
  if ! docker cp "${container}:${container_tmp}" "$output_path" 2>/dev/null; then
    echo -e "${RED}[FAIL]${NC} ${db_name}: docker cp failed"
    docker exec "$container" rm -f "$container_tmp" 2>/dev/null || true
    return 1
  fi

  # Cleanup temp file inside container
  docker exec "$container" rm -f "$container_tmp" 2>/dev/null || true

  local size
  size=$(du -h "$output_path" 2>/dev/null | cut -f1 || echo "?")
  echo -e "${GREEN}[ OK ]${NC} ${db_name} -> ${output_path} (${size})"
  return 0
}

# ── Main ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║     HVAC Platform Database Backup                    ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Timestamp : ${TIMESTAMP}"
echo -e "Output dir: ${OUTPUT_DIR}"
echo -e "Databases : ${DBS[*]}"
echo ""

FAILURES=0
SUCCESSES=0
declare -a FAILED_DBS=()
declare -a SUCCESS_DBS=()

for db in "${DBS[@]}"; do
  if backup_one "$db"; then
    SUCCESSES=$((SUCCESSES + 1))
    SUCCESS_DBS+=("$db")
  else
    FAILURES=$((FAILURES + 1))
    FAILED_DBS+=("$db")
  fi
  echo ""
done

# ── Summary ─────────────────────────────────────────────────────────────────
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║     Backup Summary                                   ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Total:    ${TOTAL:-0}"
echo -e "Success:  ${GREEN}${SUCCESSES}${NC}"
echo -e "Failed:   ${RED}${FAILURES}${NC}"

if [[ ${#SUCCESS_DBS[@]} -gt 0 ]]; then
  echo ""
  echo -e "${GREEN}Successful backups:${NC}"
  for db in "${SUCCESS_DBS[@]}"; do
    local_file="${OUTPUT_DIR}/${db}_${TIMESTAMP}.dump"
    if [[ -f "$local_file" ]]; then
      sz=$(du -h "$local_file" 2>/dev/null | cut -f1)
      echo -e "  ${GREEN}[OK]${NC} ${db}  (${sz})"
    fi
  done
fi

if [[ ${#FAILED_DBS[@]} -gt 0 ]]; then
  echo ""
  echo -e "${RED}Failed backups:${NC}"
  for db in "${FAILED_DBS[@]}"; do
    echo -e "  ${RED}[XX]${NC} ${db}"
  done
fi

# List all dump files in output dir
echo ""
echo "Contents of ${OUTPUT_DIR}:"
if ls "${OUTPUT_DIR}"/*.dump &>/dev/null; then
  ls -lh "${OUTPUT_DIR}"/*.dump 2>/dev/null | awk '{print "  " $NF "  (" $5 ")"}'
else
  echo "  (no .dump files)"
fi
echo ""

if [[ $FAILURES -gt 0 ]]; then
  exit 1
fi
exit 0
