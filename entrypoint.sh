#!/bin/sh
set -eu

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

# Use the hosting platform's scheduler to invoke /app/docker_backup.sh daily.
# Secrets are intentionally never written to disk for an in-container cron job.
if [ "${BACKUP_ON_STARTUP:-false}" = "true" ]; then
    echo "Creating encrypted startup backup..."
    /bin/sh /app/docker_backup.sh
fi

echo "Starting server..."
exec gunicorn --bind 0.0.0.0:8000 core.wsgi:application
