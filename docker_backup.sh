#!/bin/bash
# ============================================================
# Docker Backup Script - Pushes db.sqlite3 to GitHub
# Runs inside the Docker container via cron every 24h
# Requires: GITHUB_TOKEN, GITHUB_BACKUP_REPO
# ============================================================

TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
LOG_FILE="/var/log/backup.log"
CLONE_DIR="/tmp/backup_repo_$$"

echo "[$TIMESTAMP] Starting full backup..."

# Check required variables
if [ -z "$GITHUB_TOKEN" ] || [ -z "$GITHUB_BACKUP_REPO" ]; then
    echo "[$TIMESTAMP] ERROR: GITHUB_TOKEN or GITHUB_BACKUP_REPO not set."
    exit 1
fi

# Clean up previous clone
rm -rf "$CLONE_DIR"

# Configure git
export GIT_TERMINAL_PROMPT=0

# Clone the backup repo using the token
echo "[$TIMESTAMP] Cloning $GITHUB_BACKUP_REPO..."
if ! git clone --depth 1 "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_BACKUP_REPO}.git" "$CLONE_DIR" 2>&1; then
    echo "[$TIMESTAMP] ERROR: Failed to clone repo. Check GITHUB_TOKEN and GITHUB_BACKUP_REPO."
    exit 1
fi

# Copy the database file
if [ -f "/app/db.sqlite3" ]; then
    cp /app/db.sqlite3 "$CLONE_DIR/db.sqlite3"
    echo "[$TIMESTAMP] Copied db.sqlite3"
else
    echo "[$TIMESTAMP] WARNING: db.sqlite3 not found!"
fi

# Copy media files if they exist
if [ -d "/app/media" ]; then
    cp -r /app/media "$CLONE_DIR/"
    echo "[$TIMESTAMP] Copied media/"
fi

# Also create a JSON backup for safety
cd /app
mkdir -p "$CLONE_DIR/backups"
python manage.py backup_db --output-dir "$CLONE_DIR/backups" 2>&1 || echo "[$TIMESTAMP] WARNING: JSON backup failed"

# Commit and push
cd "$CLONE_DIR"
git config user.email "backup@attawoune.com"
git config user.name "Attawoune Backup Bot"

# Remove old timestamped backups (keep last 7)
if [ -d "backups" ]; then
    ls -t backups/backup_*.json 2>/dev/null | tail -n +8 | xargs rm -f 2>/dev/null || true
fi

git add -A

if git diff --cached --quiet; then
    echo "[$TIMESTAMP] No changes to commit."
else
    git commit -m "Backup: $TIMESTAMP"
    git push origin main 2>&1
    echo "[$TIMESTAMP] Backup pushed to GitHub ($GITHUB_BACKUP_REPO)"
fi

# Cleanup
rm -rf "$CLONE_DIR"
echo "[$TIMESTAMP] Backup complete."
