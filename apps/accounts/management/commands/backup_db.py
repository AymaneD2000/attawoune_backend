"""
Management command to create a database backup as JSON dump.
Usage: python manage.py backup_db
"""
import os
import json
from datetime import datetime
from django.core.management.base import BaseCommand
from django.core.management import call_command
from io import StringIO


class Command(BaseCommand):
    help = 'Create a JSON backup of the entire database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default='backups',
            help='Directory to store backup files (default: backups/)'
        )

    def handle(self, *args, **options):
        output_dir = options['output_dir']
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f'backup_{timestamp}.json'
        filepath = os.path.join(output_dir, filename)

        # Also always save as 'latest.json' for easy restore
        latest_path = os.path.join(output_dir, 'latest.json')

        self.stdout.write(f'Creating database backup...')

        # Dump all data
        output = StringIO()
        call_command(
            'dumpdata',
            '--natural-foreign',
            '--natural-primary',
            '--indent', '2',
            exclude=[
                'contenttypes',
                'auth.permission',
                'sessions',
                'admin.logentry',
            ],
            stdout=output
        )

        data = output.getvalue()

        # Write timestamped backup
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(data)

        # Write latest backup (overwrite)
        with open(latest_path, 'w', encoding='utf-8') as f:
            f.write(data)

        # Parse to count records
        records = json.loads(data)
        self.stdout.write(self.style.SUCCESS(
            f'Backup created: {filepath} ({len(records)} records, {len(data)} bytes)'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Latest backup updated: {latest_path}'
        ))
