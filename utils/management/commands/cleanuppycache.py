"""
cleanuppycache.py: Management command to remove all __pycache__ directories from all Django apps in the project
Path: /home/katestheimeno/dev/DRF-starter/utils/management/commands/cleanuppycache.py
"""

from django.core.management.base import BaseCommand
from django.conf import settings as cfg
from pathlib import Path
import shutil

class Command(BaseCommand):
    help = "Remove all __pycache__ directories from all Django apps in the project"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Show which __pycache__ directories would be removed without deleting"
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help="Print each __pycache__ directory as it is removed"
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        verbose = options.get('verbose', False)
        base_dir = cfg.BASE_DIR

        pycache_dirs = list(base_dir.rglob("__pycache__"))
        total_removed = 0
        total_size = 0

        if not pycache_dirs:
            self.stdout.write(self.style.SUCCESS("No __pycache__ directories found"))
            return

        for pycache_dir in pycache_dirs:
            size_bytes = sum(f.stat().st_size for f in pycache_dir.rglob('*') if f.is_file())
            if dry_run:
                if verbose:
                    self.stdout.write(f"Would remove: {pycache_dir} ({size_bytes / 1024:.2f} KB)")
            else:
                shutil.rmtree(pycache_dir)
                total_removed += 1
                total_size += size_bytes
                if verbose:
                    self.stdout.write(self.style.SUCCESS(f"Removed: {pycache_dir} ({size_bytes / 1024:.2f} KB)"))

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"Dry run complete. {len(pycache_dirs)} __pycache__ directories would be removed."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Removed {total_removed} __pycache__ directories, freeing {total_size / 1024:.2f} KB."
            ))
