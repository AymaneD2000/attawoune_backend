#!/bin/bash
# ============================================================
# Docker Backup Script - Pushes db.sqlite3 to GitHub
# Runs inside the Docker container via cron every 24h
# Requires: GITHUB_TOKEN, GITHUB_BACKUP_REPO
# ============================================================

set -e

TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
LOG_FILE="/var/log/backup.log"
CLONE_DIR="/tmp/backup_repo"

echo "[$TIMESTAMP] Starting full backup..." >> "$LOG_FILE"

# Check required variables
if [ -z "$GITHUB_TOKEN" ] || [ -z "$GITHUB_BACKUP_REPO" ]; then
    echo "[$TIMESTAMP] ERROR: GITHUB_TOKEN or GITHUB_BACKUP_REPO not set." >> "$LOG_FILE"
    exit 1
fi

# Clean up previous clone
rm -rf "$CLONE_DIR"

# Clone the repo using the token
git clone --depth 1 "https://${GITHUB_TOKEN}@github.com/${GITHUB_BACKUP_REPO}.git" "$CLONE_DIR" >> "$LOG_FILE" 2>&1

# Copy the database file
cp /app/db.sqlite3 "$CLONE_DIR/db.sqlite3"

# Copy media files if they exist
if [ -d "/app/media" ]; then
    cp -r /app/media "$CLONE_DIR/"
fi

# Also create a JSON backup for safety
cd /app
python manage.py backup_db --output-dir "$CLONE_DIR/backups" >> "$LOG_FILE" 2>&1

# Commit and push
cd "$CLONE_DIR"
git config user.email "backup@attawoune.com"
git config user.name "Attawoune Backup Bot"
git add -A
git commit -m "Backup: $TIMESTAMP" >> "$LOG_FILE" 2>&1 || echo "[$TIMESTAMP] No changes to commit" >> "$LOG_FILE"
git push origin main >> "$LOG_FILE" 2>&1

# Cleanup
rm -rf "$CLONE_DIR"

echo "[$TIMESTAMP] Backup pushed to GitHub ($GITHUB_BACKUP_REPO)" >> "$LOG_FILE"
