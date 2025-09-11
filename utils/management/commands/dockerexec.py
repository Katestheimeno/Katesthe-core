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

  Force interactive mode:
    manage.py dockerexec shell --interactive

  Force non-interactive mode:
    manage.py dockerexec createsuperuser --no-interactive

Configuration:
  You can customize the list of recommended Docker commands by defining
  DOCKEREXEC_COMMANDS in your Django settings:

      DOCKEREXEC_COMMANDS = [
          'migrate', 'makemigrations', 'createsuperuser', 'shell',
          'dbshell', 'collectstatic', 'runserver', 'test', 'flush',
          'loaddata', 'dumpdata', 'showmigrations', 'sqlmigrate',
          'check', 'compilemessages', 'makemessages'
      ]

  You can also define commands that always need interactive mode:

      DOCKEREXEC_INTERACTIVE_COMMANDS = [
          'createsuperuser', 'shell', 'dbshell', 'runserver'
      ]
"""

    # Default Django commands that typically need Docker
    DEFAULT_DOCKER_COMMANDS = [
        'migrate', 'makemigrations', 'createsuperuser', 'shell', 
        'dbshell', 'collectstatic', 'runserver', 'test', 'flush',
        'loaddata', 'dumpdata', 'showmigrations', 'sqlmigrate',
        'check', 'compilemessages', 'makemessages'
    ]

    # Commands that typically need interactive mode
    DEFAULT_INTERACTIVE_COMMANDS = [
        'createsuperuser', 'shell', 'dbshell', 'runserver'
    ]

    # Extendable commands: take from settings if provided, else use defaults
    DOCKER_COMMANDS = getattr(cfg, "DOCKEREXEC_COMMANDS", DEFAULT_DOCKER_COMMANDS)
    INTERACTIVE_COMMANDS = getattr(cfg, "DOCKEREXEC_INTERACTIVE_COMMANDS", DEFAULT_INTERACTIVE_COMMANDS)

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
        parser.add_argument(
            '--interactive',
            action='store_true',
            help='Force interactive mode (allocate TTY)'
        )
        parser.add_argument(
            '--no-interactive',
            action='store_true',
            help='Force non-interactive mode (no TTY allocation)'
        )

    def _needs_interactive_mode(self, django_command, command_args, options):
        """
        Determine if the command needs interactive mode based on:
        1. Explicit --interactive or --no-interactive flags
        2. Command is in INTERACTIVE_COMMANDS list
        3. Presence of --noinput in command args
        """
        # Explicit override flags
        if options['interactive']:
            return True
        if options['no_interactive']:
            return False
        
        # Check if command args contain --noinput (Django's non-interactive flag)
        if '--noinput' in command_args or '--no-input' in command_args:
            return False
            
        # Check if command is in the interactive commands list
        if django_command in self.INTERACTIVE_COMMANDS:
            return True
            
        return False

    def _execute_interactive(self, docker_cmd):
        """Execute command in interactive mode with TTY allocation"""
        # Add -i and -t flags after 'exec' for interactive mode
        # Find the position of 'exec' and insert -i -t after it
        exec_index = docker_cmd.index('exec')
        docker_cmd_interactive = docker_cmd[:exec_index+1] + ['-i', '-t'] + docker_cmd[exec_index+1:]
        
        try:
            # Use subprocess.run for interactive commands to preserve TTY
            result = subprocess.run(docker_cmd_interactive)
            return result.returncode
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING("\nCommand interrupted by user")
            )
            return 1

    def _execute_non_interactive(self, docker_cmd):
        """Execute command in non-interactive mode with output streaming"""
        try:
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
            return process.wait()
            
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING("\nCommand interrupted by user")
            )
            return 1

    def handle(self, *args, **options):
        django_command = options['django_command']
        command_args = options['command_args']
        service = options['service']
        compose_file = options['compose_file']
        dry_run = options['dry_run']

        # Build the base command (without -it flags yet)
        docker_cmd = [
            'docker', 'compose',
            '-f', compose_file,
            'exec', service,
            'uv', 'run', 'python', 'manage.py',
            django_command
        ] + command_args

        # Determine if interactive mode is needed
        needs_interactive = self._needs_interactive_mode(django_command, command_args, options)

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN - Command that would be executed:")
            )
            if needs_interactive:
                # Show what the interactive command would look like
                exec_index = docker_cmd.index('exec')
                interactive_cmd = docker_cmd[:exec_index+1] + ['-i', '-t'] + docker_cmd[exec_index+1:]
                self.stdout.write(' '.join(interactive_cmd))
                self.stdout.write(self.style.NOTICE("(Interactive mode - TTY allocated)"))
            else:
                self.stdout.write(' '.join(docker_cmd))
                self.stdout.write(self.style.NOTICE("(Non-interactive mode - output streamed)"))
            return

        try:
            if needs_interactive:
                self.stdout.write(
                    self.style.SUCCESS(f"Executing: {django_command} in Docker container (interactive mode)...")
                )
                return_code = self._execute_interactive(docker_cmd)
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"Executing: {django_command} in Docker container...")
                )
                return_code = self._execute_non_interactive(docker_cmd)
            
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
            sys.exit(1)