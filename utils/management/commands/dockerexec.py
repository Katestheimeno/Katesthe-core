"""
Management command: Execute Django management commands inside Docker container.
Path: utils/management/commands/dockerexec.py
"""

import subprocess
import sys
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings as cfg
import argparse


class Command(BaseCommand):
    help = """Execute Django management commands inside Docker container.

This command provides a convenient way to run Django management commands
inside the Docker environment from your local development machine, ensuring
consistent database connections and environment variables.

Usage:
  manage.py dockerexec <django_command> [command_args...] [options]

Examples:
  Run database migrations:
    manage.py dockerexec migrate

  Make migrations for specific app:
    manage.py dockerexec makemigrations accounts

  Create a superuser:
    manage.py dockerexec createsuperuser

  Run tests:
    manage.py dockerexec test

  Run shell with specific app:
    manage.py dockerexec shell --settings=config.django.test

  Dry run to see what would be executed:
    manage.py dockerexec migrate --dry-run

  Use different Docker service:
    manage.py dockerexec migrate --service=web-dev

Configuration:
  You can customize the list of recommended Docker commands by defining
  DOCKEREXEC_COMMANDS in your Django settings:

      DOCKEREXEC_COMMANDS = [
          'migrate', 'makemigrations', 'createsuperuser', 'shell',
          'dbshell', 'collectstatic', 'runserver', 'test', 'flush',
          'loaddata', 'dumpdata', 'showmigrations', 'sqlmigrate',
          'check', 'compilemessages', 'makemessages'
      ]
"""

    # Default Django commands that typically need Docker
    DEFAULT_DOCKER_COMMANDS = [
        'migrate', 'makemigrations', 'createsuperuser', 'shell', 
        'dbshell', 'collectstatic', 'runserver', 'test', 'flush',
        'loaddata', 'dumpdata', 'showmigrations', 'sqlmigrate',
        'check', 'compilemessages', 'makemessages'
    ]

    # Extendable commands: take from settings if provided, else use defaults
    DOCKER_COMMANDS = getattr(cfg, "DOCKEREXEC_COMMANDS", DEFAULT_DOCKER_COMMANDS)

    def create_parser(self, *args, **kwargs):
        # force RawTextHelpFormatter so newlines are respected
        kwargs['formatter_class'] = argparse.RawTextHelpFormatter
        return super().create_parser(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument(
            'django_command',
            type=str,
            help='Django management command to execute in Docker'
        )
        parser.add_argument(
            'command_args',
            nargs='*',
            help='Arguments to pass to the Django command'
        )
        parser.add_argument(
            '--service',
            type=str,
            default='web',
            help='Docker service name (default: web)'
        )
        parser.add_argument(
            '--compose-file',
            type=str,
            default='docker-compose.yml',
            help='Docker compose file to use (default: docker-compose.yml)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show the command that would be executed without running it'
        )

    def handle(self, *args, **options):
        django_command = options['django_command']
        command_args = options['command_args']
        service = options['service']
        compose_file = options['compose_file']
        dry_run = options['dry_run']

        # Build the full command
        docker_cmd = [
            'docker', 'compose',
            '-f', compose_file,
            'exec', service,
            'uv', 'run', 'python', 'manage.py',
            django_command
        ] + command_args

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN - Command that would be executed:")
            )
            self.stdout.write(' '.join(docker_cmd))
            return

        try:
            self.stdout.write(
                self.style.SUCCESS(f"Executing: {django_command} in Docker container...")
            )
            
            # Execute the command and stream output in real-time
            process = subprocess.Popen(
                docker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Stream output line by line
            for line in process.stdout:
                self.stdout.write(line.rstrip())
            
            # Wait for completion and get return code
            return_code = process.wait()
            
            if return_code != 0:
                raise CommandError(f"Command failed with exit code {return_code}")
                
            self.stdout.write(
                self.style.SUCCESS(f"Successfully completed: {django_command}")
            )
            
        except subprocess.CalledProcessError as e:
            raise CommandError(f"Docker command failed: {e}")
        except FileNotFoundError:
            raise CommandError(
                "Docker or docker-compose not found. Make sure Docker is installed and running."
            )
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING("\nCommand interrupted by user")
            )
            sys.exit(1)
