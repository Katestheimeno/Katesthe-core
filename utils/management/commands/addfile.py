"""
Management command: add suffix files to an app layer with nested scope support.
Path: utils/management/commands/addfile.py
"""

import re
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings as cfg
import argparse





class Command(BaseCommand):
    help = """Adds files to app layers with automatic import management
and nested scope support.

Usage:
  manage.py addfile <app_name> --layer LAYER --suffix SUFFIX [options]


Layer-specific default imports:
  Some layers (urls, controllers, models, admin, serializers) have default
  imports automatically added to the new file. You can customize these imports
  globally by defining the `ADDFILE_LAYER_IMPORTS` dictionary in your Django settings,
  for example:

      ADDFILE_LAYER_IMPORTS = {
          "controllers": [
              "from rest_framework import viewsets, status",
              "from rest_framework.response import Response",
              "from rest_framework.decorators import action",
              "from myproject.common.permissions import IsOwnerOrReadOnly"
          ]
      }

Examples:
  Create a controller for user creation:
    manage.py addfile accounts --layer controllers --suffix create --scope user

  Add a review serializer inside the shop feature:
    manage.py addfile shops --layer serializers --suffix review --scope shop

  Disable an existing handler:
    manage.py addfile bookings --layer handlers --suffix cancel --disable
"""

    DEFAULT_LAYER_IMPORTS = {
        "urls": [
            "from django.urls import path, include",
            "from django.conf import settings as cfg",
            "from django.conf.urls.static import static",
        ],
        "controllers": [
            "from rest_framework import viewsets, status, mixins",
            "from rest_framework.response import Response",
            "from rest_framework.decorators import action",
            "from rest_framework import permissions",
            "from django.shortcuts import get_object_or_404",
        ],
        "models": [
            "from django.db import models",
            "from django.utils import timezone",
            "from django.conf import settings as cfg",
            "from django.db.models import Q, F",
        ],
        "admin": [
            "from django.contrib import admin",
            "from django.utils.html import format_html",
        ],
        "serializers": [
            "from rest_framework import serializers",
            "from django.contrib.auth import get_user_model",
            "from rest_framework.validators import UniqueValidator",
        ],
        "services": [
            "# Place common service imports here (e.g., logging, datetime)",
            "import logging",
            "from django.db import transaction",
            "from django.core.exceptions import ObjectDoesNotExist",
        ],
        "permissions": [
            "from rest_framework import permissions",
        ],
        "selectors": [
            "from django.db.models import Q",
        ],
        "handlers": [
            "from django.dispatch import receiver",
            "from django.db.models.signals import post_save, pre_save, post_delete",
        ],
        "filters": [
            "from django_filters import rest_framework as filters",
            "from django.db.models import Q",
        ],
    }


    # Extendable imports: take from settings if provided, else use defaults
    LAYER_IMPORTS = getattr(cfg, "ADDFILE_LAYER_IMPORTS", DEFAULT_LAYER_IMPORTS)
    DEFAULT_VALID_LAYERS = [
        'admin', 'controllers', 'handlers', 'models', 'permissions',
        'selectors', 'serializers', 'services', 'urls', 'filters',
    ]

    VALID_LAYERS = getattr(
        cfg,
        "ADDFILE_VALID_LAYERS",
        DEFAULT_VALID_LAYERS
    )

    def create_parser(self, *args, **kwargs):
        # force RawTextHelpFormatter so newlines are respected
        kwargs['formatter_class'] = argparse.RawTextHelpFormatter
        return super().create_parser(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument(
            'app_name',
            type=str,
            help="Django app name where the file should be added"
        )
        parser.add_argument(
            "--layer",
            type=str,
            required=True,
            choices=self.VALID_LAYERS,
            metavar="LAYER",
            help=(
                "Target layer/module to add the file to.\n"
                "Examples: controllers, models, services.\n"
                f"Default layers: {', '.join(self.DEFAULT_VALID_LAYERS)}.\n"
                "Override with ADDFILE_VALID_LAYERS in config/django/base.py."
            ),
        )
        parser.add_argument(
            '--suffix',
            type=str,
            required=True,
            help=(
                "File identifier (suffix) used in naming.\n"
                "Examples: create, update, delete, detail, review.\n"
                "Final filename combines scope + suffix (e.g. 'user_create.py')."
            )
        )
        parser.add_argument(
            '--scope',
            type=str,
            default=None,
            help=(
                "Optional nested scope path for subdirectories.\n"
                "Examples: 'user', 'user/profile', 'auth/permissions/admin'."
            )
        )
        parser.add_argument(
            '--disable',
            action='store_true',
            help="Comment out the import in __init__.py to disable the file"
        )
        parser.add_argument(
            '--enable',
            action='store_true',
            help="Uncomment the import in __init__.py to re-enable the file"
        )
        parser.add_argument(
            '--description',
            type=str,
            default=None,
            help='Optional description for the file (appears in the file header)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Preview actions without actually creating files"
        )


    def handle(self, *args, **options):
        app_name = options.get('app_name')
        layer = options.get('layer')
        suffix = options.get('suffix')
        scope = options.get('scope')
        disable = options.get('disable')
        enable = options.get('enable')
        description = options.get('description')
        dry_run = options.get('dry_run')

        # Validate suffix name
        if not self._is_valid_suffix_name(suffix):
            raise CommandError(f"'{suffix}' is not a valid suffix name")

        # Validate scope path if provided
        if scope and not self._is_valid_scope_path(scope):
            raise CommandError(f"'{scope}' is not a valid scope path")

        # Get app directory
        app_dir = cfg.BASE_DIR / app_name
        if not app_dir.exists():
            raise CommandError(f"App directory '{app_dir}' does not exist")

        # Get layer directory
        layer_dir = app_dir / layer
        if not layer_dir.exists():
            raise CommandError(f"Layer directory '{layer_dir}' does not exist")

        # Parse scope path into components
        scope_parts = scope.split('/') if scope else []
        
        # Determine target paths
        if scope_parts:
            # Build nested scope path
            scope_path = layer_dir
            for part in scope_parts:
                scope_path = scope_path / part
            
            file_path = scope_path / f"_{suffix}.py"
            target_init_path = scope_path / "__init__.py"
        else:
            scope_path = None
            file_path = layer_dir / f"_{suffix}.py"
            target_init_path = layer_dir / "__init__.py"

        if dry_run:
            self._dry_run_preview(
                file_path, scope_path, layer_dir, suffix, 
                scope_parts, disable, enable
            )
            return

        # Handle disable/enable operations
        if disable or enable:
            self._handle_toggle_import(
                layer_dir, suffix, scope_parts, disable
            )
            return

        # Create nested scope directories if needed
        if scope_parts:
            current_path = layer_dir
            for part in scope_parts:
                current_path = current_path / part
                if not current_path.exists():
                    current_path.mkdir(parents=True, exist_ok=True)
                    self.stdout.write(self.style.SUCCESS(
                        f"Created directory: {current_path}"))
                
                # Create __init__.py for each level
                init_path = current_path / "__init__.py"
                if not init_path.exists():
                    init_path.touch()
                    self.stdout.write(self.style.SUCCESS(
                        f"Created: {init_path}"))

        # Create the suffix file
        if not file_path.exists():
            self._create_suffix_file(file_path, suffix, scope, description)
            self.stdout.write(self.style.SUCCESS(f"Created file: {file_path}"))
        else:
            self.stdout.write(self.style.WARNING(
                f"File already exists: {file_path}"))

        # Update imports through the nested structure
        self._update_nested_imports(layer_dir, suffix, scope_parts)

    def _is_valid_suffix_name(self, suffix):
        """Validate suffix name is a valid Python identifier"""
        return suffix.isidentifier() and not suffix.startswith('__')

    def _is_valid_scope_path(self, scope_path):
        """Validate scope path contains only valid Python identifiers"""
        parts = scope_path.split('/')
        return all(
            part.isidentifier() and not part.startswith('__') 
            for part in parts
        )

    def _create_suffix_file(self, file_path, suffix, scope, description=None):
        """Create the suffix file with a standard header, optional description, and default imports"""
        header = f'"""\n{file_path.name}: {description or "TODO: Implement this file"}\n'
        header += f"Path: {file_path}\n\"\"\"\n\n"

        # Add default imports if any
        layer = file_path.parent.name  # get layer name
        imports = self.LAYER_IMPORTS.get(layer, [])
        if imports:
            header += "\n".join(imports) + "\n\n"

        header += "# Your code starts here\n"
        file_path.write_text(header)

    def _update_nested_imports(self, layer_dir, suffix, scope_parts):
        """Update __init__.py files through nested scope structure"""
        if not scope_parts:
            # Direct import to layer __init__.py
            layer_init = layer_dir / "__init__.py"
            self._add_import_to_init(layer_init, f"from ._{suffix} import *")
            return

        # Handle nested imports
        current_path = layer_dir
        
        # First, add the suffix import to the deepest __init__.py
        for part in scope_parts:
            current_path = current_path / part
        
        deepest_init = current_path / "__init__.py"
        self._add_import_to_init(deepest_init, f"from ._{suffix} import *")

        # Then, propagate imports up the chain
        current_path = layer_dir
        import_chain = []
        
        for i, part in enumerate(scope_parts):
            current_path = current_path / part
            current_init = current_path.parent / "__init__.py"
            
            if i == 0:
                # First level: layer/__init__.py imports from scope
                import_statement = f"from .{part} import *"
            else:
                # Subsequent levels: already handled by directory creation
                continue
                
            if current_init.exists() or current_init == layer_dir / "__init__.py":
                self._add_import_to_init(current_init, import_statement)

        # Handle intermediate levels
        for i in range(len(scope_parts) - 1):
            intermediate_path = layer_dir
            for j in range(i + 1):
                intermediate_path = intermediate_path / scope_parts[j]
            
            intermediate_init = intermediate_path / "__init__.py"
            next_part = scope_parts[i + 1]
            import_statement = f"from .{next_part} import *"
            
            self._add_import_to_init(intermediate_init, import_statement)

    def _add_import_to_init(self, init_path, import_statement):
        """Add import statement to __init__.py if it doesn't exist"""
        if not init_path.exists():
            init_path.touch()

        content = init_path.read_text() if init_path.stat().st_size > 0 else ""

        # Check if import already exists (including commented version)
        escaped_statement = re.escape(import_statement)
        if re.search(rf"^{escaped_statement}$", content, re.MULTILINE):
            self.stdout.write(self.style.WARNING(
                f"Import already exists in {init_path}"))
            return
        elif re.search(rf"^#\s*{escaped_statement}$", content, re.MULTILINE):
            self.stdout.write(self.style.WARNING(
                f"Import exists but is commented in {init_path}"))
            return

        # Add import
        if content and not content.endswith('\n'):
            content += '\n'
        content += import_statement + '\n'

        init_path.write_text(content)
        self.stdout.write(self.style.SUCCESS(
            f"Added import to {init_path}: {import_statement}"))

    def _handle_toggle_import(self, layer_dir, suffix, scope_parts, disable):
        """Enable or disable imports by commenting/uncommenting"""
        if not scope_parts:
            # Direct layer import
            target_init = layer_dir / "__init__.py"
            import_pattern = f"from ._{suffix} import *"
        else:
            # Nested scope import - target the deepest level
            target_path = layer_dir
            for part in scope_parts:
                target_path = target_path / part
            target_init = target_path / "__init__.py"
            import_pattern = f"from ._{suffix} import *"

        if not target_init.exists():
            raise CommandError(f"__init__.py file not found: {target_init}")

        content = target_init.read_text()
        escaped_pattern = re.escape(import_pattern)

        if disable:
            # Comment out the import
            if re.search(rf"^{escaped_pattern}$", content, re.MULTILINE):
                new_content = re.sub(
                    rf"^({escaped_pattern})$",
                    rf"# \1",
                    content,
                    flags=re.MULTILINE
                )
                target_init.write_text(new_content)
                self.stdout.write(self.style.SUCCESS(
                    f"Disabled import in {target_init}: {import_pattern}"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"Import not found or already disabled: {import_pattern}"
                ))
        else:  # enable
            # Uncomment the import
            if re.search(rf"^#\s*{escaped_pattern}$", content, re.MULTILINE):
                new_content = re.sub(
                    rf"^#\s*({escaped_pattern})$",
                    rf"\1",
                    content,
                    flags=re.MULTILINE
                )
                target_init.write_text(new_content)
                self.stdout.write(self.style.SUCCESS(
                    f"Enabled import in {target_init}: {import_pattern}"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"Import not found or already enabled: {import_pattern}"
                ))

    def _dry_run_preview(self, file_path, scope_path, layer_dir, suffix, scope_parts, disable, enable):
        """Show what would be created/modified in dry-run mode"""
        self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))

        if disable:
            self.stdout.write(f"Would disable import for suffix '{suffix}'")
            return
        elif enable:
            self.stdout.write(f"Would enable import for suffix '{suffix}'")
            return

        self.stdout.write(f"Would create file: {file_path}")

        if scope_parts:
            current_path = layer_dir
            for part in scope_parts:
                current_path = current_path / part
                if not current_path.exists():
                    self.stdout.write(f"Would create directory: {current_path}")
                
                init_path = current_path / "__init__.py"
                if not init_path.exists():
                    self.stdout.write(f"Would create: {init_path}")

            # Show import chain
            self.stdout.write("\nWould create import chain:")
            
            # Deepest level
            deepest_init = scope_path / "__init__.py"
            self.stdout.write(f"  {deepest_init}: from ._{suffix} import *")
            
            # Intermediate levels
            current_path = layer_dir
            for i, part in enumerate(scope_parts):
                if i == 0:
                    parent_init = layer_dir / "__init__.py"
                    self.stdout.write(f"  {parent_init}: from .{part} import *")
                else:
                    parent_path = layer_dir
                    for j in range(i):
                        parent_path = parent_path / scope_parts[j]
                    parent_init = parent_path / "__init__.py"
                    self.stdout.write(f"  {parent_init}: from .{part} import *")
        else:
            layer_init = layer_dir / "__init__.py"
            self.stdout.write(f"Would add to {layer_init}: from ._{suffix} import *")
