#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# HVAC Platform Backup Cleanup Script
#
# Removes old backup directories, keeping only the most recent N daily dirs.
# Backup directories are expected to be named YYYY-MM-DD (created by backup.sh).
#
# Usage:
#   ./cleanup.sh --keep 7                    # Keep the latest 7 days
#   ./cleanup.sh --keep 4 --dir /var/bak     # Custom backup root directory
#   ./cleanup.sh --dry-run --keep 7          # Preview what would be deleted
# ---------------------------------------------------------------------------

set -euo pipefail

# ── Color helpers ───────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Defaults ────────────────────────────────────────────────────────────────
KEEP=0
BACKUP_ROOT="./backups"
DRY_RUN=false

# ── Usage ───────────────────────────────────────────────────────────────────
usage() {
  cat <<EOF
Usage: $0 --keep <N> [OPTIONS]

Options:
  --keep <N>          Number of most recent daily backup dirs to keep
                      (required).
  --dir <path>        Root directory containing dated backup subdirectories
                      (default: ./backups).
  --dry-run           Show which directories would be deleted without
                      actually removing them.
  -h, --help          Show this help message.

Examples:
  $0 --keep 7
  $0 --keep 4 --dir /var/backups/hvac
  $0 --dry-run --keep 7
EOF
  exit 0
}

# ── Parse arguments ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --keep)
      KEEP="$2"
      shift 2
      ;;
    --dir)
      BACKUP_ROOT="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
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
if [[ "$KEEP" -le 0 ]]; then
  echo -e "${RED}[ERROR]${NC} --keep must be a positive integer"
  exit 1
fi

if [[ ! -d "$BACKUP_ROOT" ]]; then
  echo -e "${YELLOW}[WARN]${NC} Backup directory does not exist: ${BACKUP_ROOT}"
  echo "  Nothing to clean up."
  exit 0
fi

# ── Find backup directories ─────────────────────────────────────────────────
# Look for directories matching YYYY-MM-DD pattern
# shellcheck disable=SC2012
DIRS=$(ls -1d "${BACKUP_ROOT}"/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] 2>/dev/null | sort -r || true)

if [[ -z "$DIRS" ]]; then
  echo -e "${YELLOW}[WARN]${NC} No dated backup directories found in ${BACKUP_ROOT}"
  echo "  Nothing to clean up."
  exit 0
fi

# Convert to array (portable: avoids readarray/mapfile which require bash 4+)
DIR_ARRAY=()
while IFS= read -r line; do
  [[ -n "$line" ]] && DIR_ARRAY+=("$line")
done <<< "$DIRS"

TOTAL=${#DIR_ARRAY[@]}

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║     HVAC Platform Backup Cleanup                     ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Backup root : ${BACKUP_ROOT}"
echo -e "Found       : ${TOTAL} daily backup directories"
echo -e "Keep        : ${KEEP} most recent"
if [[ "$DRY_RUN" == true ]]; then
  echo -e "Mode        : ${YELLOW}DRY RUN${NC} (no deletions will occur)"
fi
echo ""

if [[ "$TOTAL" -le "$KEEP" ]]; then
  echo -e "${GREEN}[ OK ]${NC} Only ${TOTAL} directories exist, keeping all (limit is ${KEEP})."
  echo ""
  exit 0
fi

# ── Delete old directories ──────────────────────────────────────────────────
# First KEEP directories are the most recent (sorted descending)
TO_DELETE=$((TOTAL - KEEP))
DELETED=0
FAILED=0

echo "Will keep (most recent):"
for ((i=0; i<KEEP && i<TOTAL; i++)); do
  sz=$(du -sh "${DIR_ARRAY[$i]}" 2>/dev/null | cut -f1 || echo "?")
  echo -e "  ${GREEN}[keep]${NC} ${DIR_ARRAY[$i]}  (${sz})"
done

echo ""
echo "Will remove (oldest):"
for ((i=KEEP; i<TOTAL; i++)); do
  sz=$(du -sh "${DIR_ARRAY[$i]}" 2>/dev/null | cut -f1 || echo "?")
  echo -e "  ${RED}[del ]${NC} ${DIR_ARRAY[$i]}  (${sz})"
done
echo ""

if [[ "$DRY_RUN" == true ]]; then
  echo -e "${YELLOW}[INFO]${NC} Dry run complete. ${TO_DELETE} directories would be removed."
  echo -e "  Re-run without --dry-run to actually delete them."
  echo ""
  exit 0
fi

for ((i=KEEP; i<TOTAL; i++)); do
  dir="${DIR_ARRAY[$i]}"
  if rm -rf "$dir"; then
    echo -e "${GREEN}[ OK ]${NC} Deleted: ${dir}"
    DELETED=$((DELETED + 1))
  else
    echo -e "${RED}[FAIL]${NC} Could not delete: ${dir}"
    FAILED=$((FAILED + 1))
  fi
done

echo ""
echo -e "${BOLD}Cleanup summary:${NC}"
echo -e "  Kept    : ${GREEN}${KEEP}${NC}"
echo -e "  Deleted : ${GREEN}${DELETED}${NC}"
if [[ $FAILED -gt 0 ]]; then
  echo -e "  Failed  : ${RED}${FAILED}${NC}"
fi
echo ""

if [[ $FAILED -gt 0 ]]; then
  exit 1
fi
exit 0
