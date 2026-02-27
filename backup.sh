#!/bin/bash
# ============================================================
# Automated Database Backup Script
# Runs the backup command, then commits and pushes to GitHub
# ============================================================

set -e

# Configuration
BACKUP_DIR="backups"
BRANCH="backup"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] Starting database backup..."

cd "$REPO_DIR"

# 1. Run the Django backup command
python manage.py backup_db --output-dir "$BACKUP_DIR"

# 2. Keep only the latest 7 timestamped backups (to avoid repo bloat)
cd "$BACKUP_DIR"
ls -t backup_*.json 2>/dev/null | tail -n +8 | xargs -r rm -f
cd "$REPO_DIR"

# 3. Switch to backup branch (create if needed)
CURRENT_BRANCH=$(git branch --show-current)
if ! git show-ref --verify --quiet "refs/heads/$BRANCH"; then
    git checkout --orphan "$BRANCH"
    git rm -rf . 2>/dev/null || true
    echo "# Database Backups" > README.md
    echo "" >> README.md
    echo "This branch contains automated daily database backups." >> README.md
    echo "To restore: \`python manage.py loaddata backups/latest.json\`" >> README.md
    git add README.md
    git commit -m "Initial backup branch"
else
    git stash --include-untracked 2>/dev/null || true
    git checkout "$BRANCH"
fi

# 4. Copy backup files to this branch
mkdir -p "$BACKUP_DIR"
git checkout "$CURRENT_BRANCH" -- "$BACKUP_DIR/"

# 5. Commit and push
git add "$BACKUP_DIR/"
git commit -m "Backup: $TIMESTAMP" 2>/dev/null || echo "No changes to commit"
git push origin "$BRANCH" 2>/dev/null || git push --set-upstream origin "$BRANCH"

# 6. Switch back to original branch
git checkout "$CURRENT_BRANCH"
git stash pop 2>/dev/null || true

echo "[$TIMESTAMP] Backup completed and pushed to branch '$BRANCH'"
