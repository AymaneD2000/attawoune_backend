"""
Management command to restore database from a backup JSON file.
Usage: python manage.py restore_db [--file backups/latest.json]
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Restore database from a JSON backup file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='backups/latest.json',
            help='Path to backup file (default: backups/latest.json)'
        )

    def handle(self, *args, **options):
        filepath = options['file']
        self.stdout.write(f'Restoring database from: {filepath}')
        self.stdout.write(self.style.WARNING('This will overwrite existing data!'))

        try:
            call_command('loaddata', filepath, verbosity=1)
            self.stdout.write(self.style.SUCCESS(f'Database restored successfully from {filepath}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Restore failed: {str(e)}'))
