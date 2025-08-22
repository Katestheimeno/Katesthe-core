import re
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings as cfg


class Command(BaseCommand):
    help = "Adds files to app sections with automatic import management"

    VALID_SECTIONS = [
        'admin', 'controllers', 'handlers', 'models', 'permissions',
        'selectors', 'serializers', 'services', 'urls'
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            'app_name',
            type=str,
            help='Name of the app to add file to'
        )
        parser.add_argument(
            '--section',
            type=str,
            required=True,
            choices=self.VALID_SECTIONS,
            help='Section/module to add file to (e.g., controllers, models, services)'
        )
        parser.add_argument(
            '--action',
            type=str,
            required=True,
            help='Action/file name (e.g., create, update, delete)'
        )
        parser.add_argument(
            '--domain',
            type=str,
            default=None,
            help='Optional domain/subdirectory to organize files'
        )
        parser.add_argument(
            '--disable',
            action='store_true',
            help='Comment out the import in __init__.py to disable the action'
        )
        parser.add_argument(
            '--enable',
            action='store_true',
            help='Uncomment the import in __init__.py to enable the action'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating files'
        )

    def handle(self, *args, **options):
        app_name = options['app_name']
        section = options['section']
        action = options['action']
        domain = options['domain']
        disable = options['disable']
        enable = options['enable']
        dry_run = options['dry_run']

        # Validate action name
        if not self._is_valid_action_name(action):
            raise CommandError(f"'{action}' is not a valid action name")

        # Get app directory
        app_dir = cfg.BASE_DIR / app_name
        if not app_dir.exists():
            raise CommandError(f"App directory '{app_dir}' does not exist")

        # Get section directory
        section_dir = app_dir / section
        if not section_dir.exists():
            raise CommandError(f"Section directory '{
                               section_dir}' does not exist")

        # Determine target paths
        if domain:
            domain_dir = section_dir / domain
            file_path = domain_dir / f"_{action}.py"
            domain_init_path = domain_dir / "__init__.py"
        else:
            domain_dir = None
            file_path = section_dir / f"_{action}.py"
            domain_init_path = None

        section_init_path = section_dir / "__init__.py"

        if dry_run:
            self._dry_run_preview(file_path, domain_dir, domain_init_path,
                                  section_init_path, action, domain, disable, enable)
            return

        # Handle disable/enable operations
        if disable or enable:
            self._handle_toggle_import(
                section_init_path, domain_init_path, action, domain, disable)
            return

        # Create domain directory if needed
        if domain and not domain_dir.exists():
            domain_dir.mkdir(parents=True, exist_ok=True)
            self.stdout.write(self.style.SUCCESS(
                f"Created domain directory: {domain_dir}"))

        # Create the action file
        if not file_path.exists():
            self._create_action_file(file_path, action, domain)
            self.stdout.write(self.style.SUCCESS(f"Created file: {file_path}"))
        else:
            self.stdout.write(self.style.WARNING(
                f"File already exists: {file_path}"))

        # Create domain __init__.py if needed
        if domain and not domain_init_path.exists():
            domain_init_path.touch()
            self.stdout.write(self.style.SUCCESS(
                f"Created: {domain_init_path}"))

        # Update imports
        self._update_imports(
            section_init_path, domain_init_path, action, domain)

    def _is_valid_action_name(self, action):
        """Validate action name is a valid Python identifier"""
        return action.isidentifier() and not action.startswith('__')

    def _create_action_file(self, file_path, action, domain):
        """Create the action file with basic content"""
        content = f'"""\n{action.title()} action'
        if domain:
            content += f' for {domain} domain'
        content += '\n"""\n\n# TODO: Implement your logic here\n'

        file_path.write_text(content)

    def _update_imports(self, section_init_path, domain_init_path, action, domain):
        """Update __init__.py files with appropriate imports"""

        if domain:
            # Update domain __init__.py
            self._add_import_to_init(
                domain_init_path, f"from ._{action} import *")

            # Update section __init__.py with domain import
            self._add_import_to_init(
                section_init_path, f"from .{domain} import *")
        else:
            # Direct import to section __init__.py
            self._add_import_to_init(
                section_init_path, f"from ._{action} import *")

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

    def _handle_toggle_import(self, section_init_path, domain_init_path, action, domain, disable):
        """Enable or disable imports by commenting/uncommenting"""

        if domain:
            target_init = domain_init_path
            import_pattern = f"from ._{action} import *"
        else:
            target_init = section_init_path
            import_pattern = f"from ._{action} import *"

        if not target_init or not target_init.exists():
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
                    f"Import not found or already disabled in {
                        target_init}: {import_pattern}"
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
                    f"Import not found or already enabled in {
                        target_init}: {import_pattern}"
                ))

    def _dry_run_preview(self, file_path, domain_dir, domain_init_path, section_init_path, action, domain, disable, enable):
        """Show what would be created/modified in dry-run mode"""
        self.stdout.write(self.style.WARNING(
            "DRY RUN - No changes will be made"))

        if disable:
            self.stdout.write(f"Would disable import for action '{
                              action}' in appropriate __init__.py")
            return
        elif enable:
            self.stdout.write(f"Would enable import for action '{
                              action}' in appropriate __init__.py")
            return

        self.stdout.write(f"Would create file: {file_path}")

        if domain and not domain_dir.exists():
            self.stdout.write(f"Would create domain directory: {domain_dir}")

        if domain and not domain_init_path.exists():
            self.stdout.write(f"Would create: {domain_init_path}")

        if domain:
            self.stdout.write(f"Would add to {domain_init_path}: from ._{
                              action} import *")
            self.stdout.write(f"Would add to {section_init_path}: from .{
                              domain} import *")
        else:
            self.stdout.write(f"Would add to {section_init_path}: from ._{
                              action} import *")
