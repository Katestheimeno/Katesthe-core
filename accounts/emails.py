"""
Custom email classes for Djoser authentication flows.
Path: accounts/emails.py
"""

from djoser import email
from django.contrib.auth.tokens import default_token_generator
from djoser import utils
from djoser.conf import settings


class CustomActivationEmail(email.ActivationEmail):
    """
    Custom activation email template.
    """
    template_name = "email/activation.html"

    def get_context_data(self):
        # Get the user from context
        user = self.context.get("user")
        if not user:
            return {}
        
        # Generate the context data manually to avoid Djoser's problematic settings
        context = {
            'user': user,
            'uid': utils.encode_uid(user.pk),
            'token': default_token_generator.make_token(user),
            'url': f"/api/v1/auth/users/activation/{utils.encode_uid(user.pk)}/{default_token_generator.make_token(user)}/",
            'site_name': 'Your App Name',
            'support_email': 'support@yourapp.com',
        }
        return context


class CustomPasswordResetEmail(email.PasswordResetEmail):
    """
    Custom password reset email template.
    """
    template_name = "email/password_reset.html"

    def get_context_data(self):
        context = super().get_context_data()
        
        # Add any custom context data you need
        context.update({
            'site_name': 'Your App Name',
            'support_email': 'support@yourapp.com',
        })
        return context


class CustomPasswordChangedConfirmationEmail(email.PasswordChangedConfirmationEmail):
    """
    Custom password changed confirmation email.
    """
    template_name = "email/password_changed_confirmation.html"

    def get_context_data(self):
        context = super().get_context_data()
        # Add any custom context data you need
        context.update({
            'site_name': 'Your App Name',
            'support_email': 'support@yourapp.com',
        })
        return context
