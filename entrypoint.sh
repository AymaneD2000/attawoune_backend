#!/bin/bash
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

# Set up daily backup cron job if GITHUB_TOKEN is configured
if [ -n "$GITHUB_TOKEN" ] && [ -n "$GITHUB_BACKUP_REPO" ]; then
    echo "Setting up daily backup cron job..."
    
    # Write ALL environment variables to a file that cron can source
    env > /app/.env.backup
    
    # Create the cron wrapper script that sources env first
    cat > /app/run_backup.sh << 'WRAPPER'
#!/bin/bash
set -a
source /app/.env.backup
set +a
cd /app
/bin/bash /app/docker_backup.sh >> /var/log/backup.log 2>&1
WRAPPER
    chmod +x /app/run_backup.sh
    
    # Create cron job: runs daily at 2 AM (MUST end with newline)
    echo "0 2 * * * /bin/bash /app/run_backup.sh" > /etc/cron.d/backup
    echo "" >> /etc/cron.d/backup
    chmod 0644 /etc/cron.d/backup
    crontab /etc/cron.d/backup
    
    # Start cron in background
    service cron start 2>/dev/null || cron 2>/dev/null || true
    
    # Run first backup immediately to verify it works
    echo "Running initial backup to verify setup..."
    /bin/bash /app/run_backup.sh && echo "Initial backup successful!" || echo "WARNING: Initial backup failed. Check /var/log/backup.log"
    
    echo "Backup cron job configured (daily at 2 AM UTC)"
else
    echo "WARNING: GITHUB_TOKEN or GITHUB_BACKUP_REPO not set. Automated backups disabled."
    echo "Set GITHUB_TOKEN and GITHUB_BACKUP_REPO environment variables to enable backups."
fi

echo "Starting server..."
exec gunicorn --bind 0.0.0.0:8000 core.wsgi:application
