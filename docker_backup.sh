#!/bin/sh
set -eu

export BACKUP_DIR=${BACKUP_DIR:-/var/backups/university_management_system}
export BACKUP_RETENTION=${BACKUP_RETENTION:-7}

exec /bin/sh /app/backup.sh
