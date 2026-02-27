#!/bin/bash
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

# Set up daily backup cron job if GITHUB_TOKEN is configured
if [ -n "$GITHUB_TOKEN" ] && [ -n "$GITHUB_BACKUP_REPO" ]; then
    echo "Setting up daily backup cron job..."
    
    # Pass environment variables to cron
    printenv | grep -E '^(GITHUB_TOKEN|GITHUB_BACKUP_REPO|DJANGO_SETTINGS_MODULE|DATABASE_URL|SECRET_KEY|PATH)=' > /etc/environment
    
    # Create cron job: runs daily at 2 AM
    echo "0 2 * * * cd /app && /bin/bash /app/docker_backup.sh >> /var/log/backup.log 2>&1" > /etc/cron.d/backup
    chmod 0644 /etc/cron.d/backup
    crontab /etc/cron.d/backup
    
    # Start cron in background
    service cron start || cron
    
    echo "Backup cron job configured (daily at 2 AM UTC)"
else
    echo "WARNING: GITHUB_TOKEN or GITHUB_BACKUP_REPO not set. Automated backups disabled."
fi

echo "Starting server..."
exec gunicorn --bind 0.0.0.0:8000 core.wsgi:application
