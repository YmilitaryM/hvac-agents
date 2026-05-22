# HVAC Platform Database Backup & Restore

Scripts for backing up and restoring PostgreSQL/TimescaleDB databases used by the HVAC platform. All databases run as Docker containers managed via `docker compose`.

## Quick Start

```bash
# Backup all databases
./scripts/backup/backup.sh

# Backup a single database
./scripts/backup/backup.sh --db energy_db

# Restore a database (interactive confirmation)
./scripts/backup/restore.sh -f ./backups/2026-05-22/energy_db_2026-05-22_120000.dump -d energy_db

# Restore without confirmation prompt (automation)
./scripts/backup/restore.sh -f ./backups/2026-05-22/energy_db_2026-05-22_120000.dump -d energy_db -y

# Clean up old backups, keeping the latest 7 days
./scripts/backup/cleanup.sh --keep 7
```

## Database Inventory

| Database    | Container Service  | Type        | Notes                     |
|-------------|-------------------|-------------|---------------------------|
| asset_db    | postgres_asset     | PostgreSQL  | Asset registry            |
| env_db      | timescaledb        | TimescaleDB | Environment/weather data  |
| sim_db      | postgres_sim       | PostgreSQL  | Simulation state          |
| agent_db    | postgres_agent     | PostgreSQL  | Agent runtime             |
| acq_db      | timescaledb_acq    | TimescaleDB | Sensor data acquisition   |
| edge_db     | postgres_edge      | PostgreSQL  | Edge device management    |
| energy_db   | energy_db          | TimescaleDB | Energy analytics          |
| health_db   | health_db          | PostgreSQL  | Health monitoring         |

All databases use user `hvac` with password `hvac_dev` (development defaults).

## Container Resolution

The scripts resolve Docker containers by trying (in order):

1. Exact name match (e.g. `postgres_asset`)
2. Fuzzy match (container name containing the service name)
3. Docker Compose project-prefix pattern (`<project>_<service>_N`)

If your containers use custom names, set environment variables:

```bash
export CONTAINER_asset_db=my_custom_asset_container
export CONTAINER_energy_db=prod_energy
./scripts/backup/backup.sh
```

## Scripts

### backup.sh

Backs up PostgreSQL/TimescaleDB databases to compressed custom-format files.

**Options:**
- `--all` -- backup all databases (default)
- `--db <name>` -- backup a single database
- `--output-dir <path>` -- write dumps here (default: `./backups/YYYY-MM-DD/`)

**Output:** Each dump is a `.dump` file in `pg_dump` custom format (compressed). Named: `<db>_<timestamp>.dump`

**Exit code:** 0 on success, 1 if any backup failed.

```bash
# Backup all databases to a custom location
./scripts/backup/backup.sh --all --output-dir /mnt/nas/hvac-backups/

# Backup just the health database
./scripts/backup/backup.sh --db health_db
```

### restore.sh

Restores a database from a backup dump file. **Destructive** -- drops the target database and recreates it before restoring.

**Options:**
- `-f, --file <path>` -- dump file to restore from (required)
- `-d, --db <name>` -- target database name (required)
- `-y, --yes` -- skip confirmation prompt
- `-h, --help` -- show help

**Steps performed:**
1. Validates dump file exists
2. Locates and starts the database container if needed
3. Prompts for confirmation (unless `-y`)
4. Terminates active connections to the target database
5. Drops the database
6. Creates a fresh empty database
7. Restores from dump using `pg_restore -c -O -x`

```bash
# Interactive restore
./scripts/backup/restore.sh -f ./backups/2026-05-22/agent_db_2026-05-22_020000.dump -d agent_db

# Automated restore (CI/CD, scripts)
./scripts/backup/restore.sh -f /tmp/restore.dump -d energy_db -y
```

### cleanup.sh

Removes old daily backup directories, keeping only the most recent N.

**Options:**
- `--keep <N>` -- number of recent backup dirs to keep (required)
- `--dir <path>` -- root directory with dated subdirs (default: `./backups`)
- `--dry-run` -- preview without deleting
- `-h, --help` -- show help

```bash
# Keep the last 14 days, remove the rest
./scripts/backup/cleanup.sh --keep 14 --dir /var/backups/hvac

# Preview what would be deleted
./scripts/backup/cleanup.sh --dry-run --keep 7
```

## Automation

Install the example crontab from `backup-cron.txt`:

```bash
crontab -e
# Paste the lines from scripts/backup/backup-cron.txt (adjusted for your paths)
```

Example schedule:
- **Daily at 2 AM:** full backup of all databases
- **Weekly on Sunday:** remove backups older than 4 weeks

## Dump Format & Compression

All dumps use `pg_dump -Fc` (custom format), which:
- Is compressed by default
- Supports parallel restore with `pg_restore -j N`
- Allows selective restore of individual tables/schemas
- Is portable across PostgreSQL major versions

## TimescaleDB Notes

TimescaleDB hypertables are backed up correctly by `pg_dump`. During restore, TimescaleDB-specific objects (hypertables, compression policies, continuous aggregates) are recreated. This requires the target database to also be running TimescaleDB (i.e. restore `env_db` only to its dedicated TimescaleDB container).

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "no container found" | Start the service: `docker compose up -d postgres_asset` |
| "pg_dump: not found" | Container may be missing PostgreSQL tools; verify the image |
| Permission denied on restore | Uses `-O -x` flags to skip ownership/ACL during restore |
| Large databases timeout | Increase Docker exec timeout or run pg_dump manually |
