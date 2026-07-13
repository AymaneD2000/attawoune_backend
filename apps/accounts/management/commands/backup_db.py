"""Create an encrypted, external application backup."""

import os
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Create an AES-256 encrypted data/media archive outside the repository'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            default=os.environ.get('BACKUP_DIR', str(Path.home() / 'university_backups')),
            help='External directory for encrypted archives (or set BACKUP_DIR)',
        )
        parser.add_argument(
            '--include-media',
            action='store_true',
            help='Include MEDIA_ROOT in the encrypted archive',
        )
        parser.add_argument(
            '--keep',
            type=int,
            default=7,
            help='Number of encrypted archives to retain',
        )

    def handle(self, *args, **options):
        encryption_key = os.environ.get('BACKUP_ENCRYPTION_KEY')
        if not encryption_key:
            raise CommandError('BACKUP_ENCRYPTION_KEY is required.')
        if shutil.which('openssl') is None:
            raise CommandError('openssl is required to encrypt backups.')

        output_dir = Path(options['output_dir']).expanduser().resolve()
        output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(output_dir, 0o700)

        repository_root = Path(settings.BASE_DIR).resolve()
        try:
            output_dir.relative_to(repository_root)
        except ValueError:
            pass
        else:
            raise CommandError('BACKUP_DIR must be outside the application repository.')

        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        encrypted_path = output_dir / f'university_backup_{timestamp}.tar.gz.enc'

        with tempfile.TemporaryDirectory(prefix='university-backup-') as temp_name:
            temp_dir = Path(temp_name)
            data_path = temp_dir / 'data.json'
            archive_path = temp_dir / 'backup.tar.gz'

            with data_path.open('w', encoding='utf-8') as output:
                call_command(
                    'dumpdata',
                    '--natural-foreign',
                    '--natural-primary',
                    exclude=[
                        'contenttypes',
                        'auth.permission',
                        'sessions',
                        'admin.logentry',
                    ],
                    stdout=output,
                )
            os.chmod(data_path, 0o600)

            with tarfile.open(archive_path, 'w:gz') as archive:
                archive.add(data_path, arcname='data.json')
                media_root = Path(settings.MEDIA_ROOT)
                if options['include_media'] and media_root.exists():
                    archive.add(media_root, arcname='media')

            environment = os.environ.copy()
            environment['BACKUP_ENCRYPTION_KEY'] = encryption_key
            result = subprocess.run(
                [
                    'openssl', 'enc', '-aes-256-cbc', '-pbkdf2', '-salt',
                    '-in', str(archive_path), '-out', str(encrypted_path),
                    '-pass', 'env:BACKUP_ENCRYPTION_KEY',
                ],
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                encrypted_path.unlink(missing_ok=True)
                raise CommandError(f'Backup encryption failed: {result.stderr.strip()}')

        os.chmod(encrypted_path, 0o600)
        archives = sorted(
            output_dir.glob('university_backup_*.tar.gz.enc'),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for old_archive in archives[max(options['keep'], 1):]:
            old_archive.unlink()

        self.stdout.write(self.style.SUCCESS(f'Encrypted backup created: {encrypted_path}'))
