"""
Management command to generate an RSA key pair for JWT RS256 signing.
Path: accounts/management/commands/generate_jwt_keys.py

Usage:
    python manage.py generate_jwt_keys
"""

import base64

from django.core.management.base import BaseCommand

from config.jwt_keys import compute_kid, generate_rsa_private_key, private_key_to_pem


class Command(BaseCommand):
    help = "Generate an RSA-2048 private key for JWT RS256 signing and print the base64-encoded value for .env"

    def handle(self, *args, **options):
        key = generate_rsa_private_key()
        pem = private_key_to_pem(key)
        b64 = base64.b64encode(pem.encode()).decode()

        self.stdout.write(self.style.SUCCESS(f"Generated RSA key (kid={compute_kid(key)})"))
        self.stdout.write("Add this to your .env file:")
        self.stdout.write(f"JWT_RSA_PRIVATE_KEY={b64}")
