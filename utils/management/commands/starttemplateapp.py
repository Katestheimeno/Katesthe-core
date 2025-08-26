"""
Management command: scaffold a new app from the template in `static/exp_app`.
Path: utils/management/commands/starttemplateapp.py
"""

import os
import shutil
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings as cfg


class Command(BaseCommand):
    help = "Creates a new app from templates with placeholder replacement"

    def add_arguments(self, parser):
        parser.add_argument(
            'app_name',
            type=str,
            help='Name of the new app'
        )
        parser.add_argument(
            '--dir',
            type=str,
            default=None,
            help='Directory to create the app in (default: current directory or BASE_DIR)'
        )
        parser.add_argument(
            '--template',
            type=str,
            default='exp_app',
            help='Template directory name to use (default: exp_app)'
        )
        parser.add_argument(
            '--template-path',
            type=str,
            default=None,
            help='Full path to template directory (overrides --template)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing app directory if it exists'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating files'
        )
        parser.add_argument(
            '--add-to-settings',
            action='store_true',
            help='Automatically add the app to PROJECT_APPS in settings'
        )

    def handle(self, *args, **options):
        app_name = options['app_name']

        # Validate app name
        if not app_name.isidentifier():
            raise CommandError(
                f"'{app_name}' is not a valid Python identifier for an app name"
            )

        # Generate name variants
        class_name = "".join(word.capitalize() for word in app_name.split("_"))

        # Determine target directory
        if options['dir']:
            base_dir = Path(options['dir'])
        else:
            base_dir = getattr(
                cfg, 'BASE_DIR', Path.cwd().parent.parent.parent.parent)

        target_dir = base_dir / app_name

        # Determine template directory
        if options['template_path']:
            template_dir = Path(options['template_path'])
        else:
            template_dir = (
                Path(__file__).resolve().parent.parent.parent.parent /
                'static' / options['template']
            )

        # Validate template directory
        if not template_dir.exists():
            raise CommandError(f"Template directory '{
                               template_dir}' does not exist!")

        # Check if target exists
        if target_dir.exists():
            if not options['force']:
                raise CommandError(
                    f"The target directory '{target_dir}' already exists! "
                    "Use --force to overwrite."
                )
            elif not options['dry_run']:
                shutil.rmtree(target_dir)
                self.stdout.write(self.style.WARNING(
                    f"Removed existing directory '{target_dir}'"
                ))

        if options['dry_run']:
            self.stdout.write(self.style.WARNING(
                "DRY RUN - No files will be created"))
            self.stdout.write(f"Template: {template_dir}")
            self.stdout.write(f"Target: {target_dir}")
            self.stdout.write(
                f"Replacements: {{{{APP_NAME}}}} -> {app_name}, {{{{APP_CLASS_NAME}}}} -> {class_name}")
            return

        # Copy template folder
        shutil.copytree(template_dir, target_dir)

        # Replace placeholders in all files
        for file_path in target_dir.rglob("*.*"):
            try:
                text = file_path.read_text()
                text = text.replace("{{APP_NAME}}", app_name)
                text = text.replace("{{APP_CLASS_NAME}}", class_name)
                file_path.write_text(text)
            except UnicodeDecodeError:
                continue

        # Add to settings if requested
        if options['add_to_settings']:
            try:
                from django.core.management import call_command
                call_command('manageprojectapp', app_name, verbosity=0)
                self.stdout.write(self.style.SUCCESS(
                    f"Added '{app_name}' to PROJECT_APPS in settings"
                ))
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"Could not add '{ app_name}' to settings automatically: {e}"
                ))

        self.stdout.write(self.style.SUCCESS(
            f"App '{app_name}' created from template at {target_dir}"
        ))
