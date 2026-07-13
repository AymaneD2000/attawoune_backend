#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BACKUP_DIR=${BACKUP_DIR:-"$HOME/university_backups"}
BACKUP_RETENTION=${BACKUP_RETENTION:-7}

if [ -z "${BACKUP_ENCRYPTION_KEY:-}" ]; then
    echo "BACKUP_ENCRYPTION_KEY is required." >&2
    exit 1
fi

cd "$SCRIPT_DIR"
python manage.py backup_db \
    --output-dir "$BACKUP_DIR" \
    --include-media \
    --keep "$BACKUP_RETENTION"
