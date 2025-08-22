import re
from pathlib import Path
from django.conf import settings as cfg
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Manages apps in PROJECT_APPS and THIRD_PARTY_PACKAGES in apps_middlewares.py"

    def add_arguments(self, parser):
        parser.add_argument(
            "app_name",
            type=str,
            help="Name of the app to add/remove"
        )
        parser.add_argument(
            "--type",
            choices=["project", "third-party"],
            default="project",
            help="Type of app: 'project' for PROJECT_APPS or 'third-party' for THIRD_PARTY_PACKAGES (default: project)"
        )
        parser.add_argument(
            "--comment",
            type=str,
            default=None,
            help="Optional comment to add next to the app"
        )
        parser.add_argument(
            "--remove",
            action="store_true",
            help="Remove the app instead of adding it"
        )
        parser.add_argument(
            "--soft-remove",
            action="store_true",
            help="Soft remove by commenting out the app (only works with --remove)"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force add even if app folder doesn't exist (useful for third-party packages)"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without actually modifying the file"
        )

    def handle(self, *args, **options):
        app_name = options["app_name"]
        app_type = options["type"]
        comment = options.get("comment")
        remove = options["remove"]
        soft_remove = options["soft_remove"]
        force = options["force"]
        dry_run = options["dry_run"]

        apps_file = cfg.BASE_DIR / "config/settings/apps_middlewares.py"
        app_path = cfg.BASE_DIR / app_name

        if not apps_file.exists():
            raise CommandError(f"{apps_file} not found!")

        # Determine target list name
        target_list = "PROJECT_APPS" if app_type == "project" else "THIRD_PARTY_PACKAGES"
        
        # Check app folder existence for project apps (unless forced or removing)
        if app_type == "project" and not remove and not force:
            if not app_path.exists() or not app_path.is_dir():
                self.stdout.write(self.style.WARNING(
                    f"App folder '{app_name}' does not exist. Use --force to add anyway."
                ))
                return

        content = apps_file.read_text()

        if remove:
            self._handle_remove(content, apps_file, app_name, target_list, soft_remove, dry_run)
        else:
            self._handle_add(content, apps_file, app_name, target_list, comment, dry_run)

    def _handle_add(self, content, apps_file, app_name, target_list, comment, dry_run):
        """Handle adding an app to the target list"""
        # Match the target list
        pattern = rf"({target_list}\s*=\s*\[)(.*?)(\])"
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            raise CommandError(f"Could not find {target_list} in apps_middlewares.py")

        start, apps_list, end = match.groups()

        # Check if app already exists (including commented versions)
        app_patterns = [
            f"'{app_name}'",
            f'"{app_name}"',
            f"# '{app_name}'",
            f'# "{app_name}"'
        ]
        
        for pattern in app_patterns:
            if pattern in apps_list:
                self.stdout.write(self.style.WARNING(
                    f"App '{app_name}' already exists in {target_list}"
                ))
                return

        # Prepare the new line with optional comment
        comment_str = f"  # {comment}" if comment else ""
        
        # Find the best insertion point (before the closing bracket, maintaining formatting)
        if apps_list.strip():
            # Add after existing apps
            new_apps_list = apps_list.rstrip() + f"\n    '{app_name}',{comment_str}\n"
        else:
            # Empty list
            new_apps_list = f"\n    '{app_name}',{comment_str}\n"

        new_content = content.replace(match.group(0), f"{start}{new_apps_list}{end}")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes made"))
            self.stdout.write(f"Would add '{app_name}' to {target_list}")
        else:
            apps_file.write_text(new_content)
            self.stdout.write(self.style.SUCCESS(
                f"App '{app_name}' added to {target_list}"
            ))

    def _handle_remove(self, content, apps_file, app_name, target_list, soft_remove, dry_run):
        """Handle removing an app from the target list"""
        # Match the target list
        pattern = rf"({target_list}\s*=\s*\[)(.*?)(\])"
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            raise CommandError(f"Could not find {target_list} in apps_middlewares.py")

        start, apps_list, end = match.groups()

        # Find the app line to remove/comment
        app_patterns = [
            rf"(\s*)('{app_name}',.*?)(\n|$)",
            rf"(\s*)(\"{ app_name}\",.*?)(\n|$)"
        ]

        found = False
        new_apps_list = apps_list

        for pattern in app_patterns:
            app_match = re.search(pattern, apps_list)
            if app_match:
                found = True
                indent, app_line, newline = app_match.groups()
                
                if soft_remove:
                    # Comment out the line
                    if not app_line.strip().startswith('#'):
                        commented_line = f"# {app_line}"
                        new_apps_list = apps_list.replace(
                            f"{indent}{app_line}{newline}", 
                            f"{indent}{commented_line}{newline}"
                        )
                        action = "commented out"
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"App '{app_name}' is already commented out in {target_list}"
                        ))
                        return
                else:
                    # Hard remove - delete the entire line
                    new_apps_list = apps_list.replace(f"{indent}{app_line}{newline}", "")
                    action = "removed"
                break

        if not found:
            # Check if it exists but is commented
            commented_patterns = [
                rf"(\s*)(#\s*'{app_name}',.*?)(\n|$)",
                rf"(\s*)(#\s*\"{app_name}\",.*?)(\n|$)"
            ]
            
            for pattern in commented_patterns:
                app_match = re.search(pattern, apps_list)
                if app_match:
                    if not soft_remove:
                        # Remove commented line
                        indent, app_line, newline = app_match.groups()
                        new_apps_list = apps_list.replace(f"{indent}{app_line}{newline}", "")
                        found = True
                        action = "removed"
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"App '{app_name}' is already commented out in {target_list}"
                        ))
                        return
                    break

        if not found:
            self.stdout.write(self.style.WARNING(
                f"App '{app_name}' not found in {target_list}"
            ))
            return

        new_content = content.replace(match.group(0), f"{start}{new_apps_list}{end}")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes made"))
            self.stdout.write(f"Would {action} '{app_name}' from {target_list}")
        else:
            apps_file.write_text(new_content)
            self.stdout.write(self.style.SUCCESS(
                f"App '{app_name}' {action} from {target_list}"
            ))
