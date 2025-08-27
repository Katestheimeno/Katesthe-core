"""
Tests for custom email functionality.
Path: accounts/tests/test_emails.py
"""

import pytest
from django.test import TestCase
from django.core import mail
from django.contrib.auth import get_user_model
from accounts.emails import (
    CustomActivationEmail,
    CustomPasswordResetEmail,
    CustomPasswordChangedConfirmationEmail
)
from accounts.tests.factories import UserFactory

User = get_user_model()


class TestCustomActivationEmail:
    """Test custom activation email functionality."""
    
    @pytest.mark.django_db
    def test_activation_email_template(self):
        """Test that activation email uses correct template."""
        user = UserFactory()
        email = CustomActivationEmail()
        
        assert email.template_name == "email/activation.html"
    
    @pytest.mark.django_db
    def test_activation_email_context(self):
        """Test that activation email has correct context data."""
        user = UserFactory()
        email = CustomActivationEmail()
        
        # Set the context that Djoser expects
        email.context = {'user': user}
        
        # Get the context data
        context_data = email.get_context_data()
        
        # Check that custom context is added
        assert 'site_name' in context_data
        assert 'support_email' in context_data
        assert context_data['site_name'] == 'Your App Name'
        assert context_data['support_email'] == 'support@yourapp.com'
    
    @pytest.mark.django_db
    def test_activation_email_sending(self):
        """Test that activation email can be sent."""
        user = UserFactory()
        email = CustomActivationEmail()
        
        # Set the context that Djoser expects
        email.context = {'user': user}
        
        # Send the email
        email.send([user.email])
        
        # Check that email was sent
        assert len(mail.outbox) == 1
        sent_email = mail.outbox[0]
        
        assert sent_email.to == [user.email]
        assert 'activation' in sent_email.subject.lower()


class TestCustomPasswordResetEmail:
    """Test custom password reset email functionality."""
    
    @pytest.mark.django_db
    def test_password_reset_email_template(self):
        """Test that password reset email uses correct template."""
        user = UserFactory()
        email = CustomPasswordResetEmail()
        
        assert email.template_name == "email/password_reset.html"
    
    @pytest.mark.django_db
    def test_password_reset_email_context(self):
        """Test that password reset email has correct context data."""
        user = UserFactory()
        email = CustomPasswordResetEmail()
        
        # Set the context that Djoser expects
        email.context = {'user': user}
        
        # Get the context data
        context_data = email.get_context_data()
        
        # Check that custom context is added
        assert 'site_name' in context_data
        assert 'support_email' in context_data
        assert context_data['site_name'] == 'Your App Name'
        assert context_data['support_email'] == 'support@yourapp.com'
    
    @pytest.mark.django_db
    def test_password_reset_email_sending(self):
        """Test that password reset email can be sent."""
        user = UserFactory()
        email = CustomPasswordResetEmail()
        
        # Set the context that Djoser expects
        email.context = {'user': user}
        
        # Send the email
        email.send([user.email])
        
        # Check that email was sent
        assert len(mail.outbox) == 1
        sent_email = mail.outbox[0]
        
        assert sent_email.to == [user.email]
        assert 'password' in sent_email.subject.lower()


class TestCustomPasswordChangedConfirmationEmail:
    """Test custom password changed confirmation email functionality."""
    
    @pytest.mark.django_db
    def test_password_changed_email_template(self):
        """Test that password changed email uses correct template."""
        user = UserFactory()
        email = CustomPasswordChangedConfirmationEmail()
        
        assert email.template_name == "email/password_changed_confirmation.html"
    
    @pytest.mark.django_db
    def test_password_changed_email_context(self):
        """Test that password changed email has correct context data."""
        user = UserFactory()
        email = CustomPasswordChangedConfirmationEmail()
        
        # Get the context data
        context_data = email.get_context_data()
        
        # Check that custom context is added
        assert 'site_name' in context_data
        assert 'support_email' in context_data
        assert context_data['site_name'] == 'Your App Name'
        assert context_data['support_email'] == 'support@yourapp.com'
    
    @pytest.mark.django_db
    def test_password_changed_email_sending(self):
        """Test that password changed email can be sent."""
        user = UserFactory()
        email = CustomPasswordChangedConfirmationEmail()
        
        # Send the email
        email.send([user.email])
        
        # Check that email was sent
        assert len(mail.outbox) == 1
        sent_email = mail.outbox[0]
        
        assert sent_email.to == [user.email]
        assert 'password' in sent_email.subject.lower()


class TestEmailTemplates:
    """Test email template rendering."""
    
    @pytest.mark.django_db
    def test_activation_template_rendering(self):
        """Test that activation template renders correctly."""
        from django.template.loader import render_to_string
        from django.test import RequestFactory
        
        user = UserFactory()
        request = RequestFactory().get('/')
        
        context = {
            'user': user,
            'protocol': 'https',
            'domain': 'example.com',
            'url': 'activation/url/here',
            'site_name': 'Your App Name',
            'support_email': 'support@yourapp.com'
        }
        
        # Render the template
        html_content = render_to_string('email/activation.html', context, request=request)
        text_content = render_to_string('email/activation.txt', context, request=request)
        
        # Check that template renders without errors
        assert html_content is not None
        assert text_content is not None
        
        # Check that activation content is included
        assert 'activation' in html_content.lower()
        assert 'activation' in text_content.lower()
    
    @pytest.mark.django_db
    def test_password_reset_template_rendering(self):
        """Test that password reset template renders correctly."""
        from django.template.loader import render_to_string
        from django.test import RequestFactory
        
        user = UserFactory()
        request = RequestFactory().get('/')
        
        context = {
            'user': user,
            'protocol': 'https',
            'domain': 'example.com',
            'uid': 'test_uid',
            'token': 'test_token',
            'site_name': 'Your App Name',
            'support_email': 'support@yourapp.com'
        }
        
        # Render the template
        html_content = render_to_string('email/password_reset.html', context, request=request)
        text_content = render_to_string('email/password_reset.txt', context, request=request)
        
        # Check that template renders without errors
        assert html_content is not None
        assert text_content is not None
        
        # Check that password reset content is included
        assert 'password' in html_content.lower()
        assert 'password' in text_content.lower()
    
    @pytest.mark.django_db
    def test_password_changed_template_rendering(self):
        """Test that password changed template renders correctly."""
        from django.template.loader import render_to_string
        from django.test import RequestFactory
        
        user = UserFactory()
        request = RequestFactory().get('/')
        
        context = {
            'user': user,
            'site_name': 'Your App Name',
            'support_email': 'support@yourapp.com'
        }
        
        # Render the template
        html_content = render_to_string('email/password_changed_confirmation.html', context, request=request)
        text_content = render_to_string('email/password_changed_confirmation.txt', context, request=request)
        
        # Check that template renders without errors
        assert html_content is not None
        assert text_content is not None
        
        # Check that confirmation message is included
        assert 'password' in html_content.lower()
        assert 'password' in text_content.lower()


class TestEmailIntegration:
    """Integration tests for email functionality."""
    
    @pytest.mark.django_db
    def test_email_sending_integration(self):
        """Test that emails can be sent in a realistic scenario."""
        # Create a user for this test
        user = UserFactory()
        mail.outbox.clear()
        
        # Create activation email
        activation_email = CustomActivationEmail()
        
        # Set the context that Djoser expects
        activation_email.context = {'user': user}
        
        # Send the email
        activation_email.send([user.email])
        
        # Verify email was sent
        assert len(mail.outbox) == 1
        sent_email = mail.outbox[0]
        
        assert sent_email.to == [user.email]
        assert 'activation' in sent_email.subject.lower()
        
        # Check email content
        assert 'activation' in sent_email.body.lower()
    
    @pytest.mark.django_db
    def test_multiple_emails_sending(self):
        """Test that multiple emails can be sent."""
        user1 = UserFactory()
        user2 = UserFactory()
        
        # Clear mail outbox
        mail.outbox.clear()
        
        # Send activation email to first user
        activation_email = CustomActivationEmail()
        activation_email.context = {'user': user1}
        activation_email.send([user1.email])
        
        # Send password reset email to second user
        reset_email = CustomPasswordResetEmail()
        reset_email.context = {'user': user2}
        reset_email.send([user2.email])
        
        # Verify both emails were sent
        assert len(mail.outbox) == 2
        
        # Check first email
        assert mail.outbox[0].to == [user1.email]
        assert 'activation' in mail.outbox[0].subject.lower()
        
        # Check second email
        assert mail.outbox[1].to == [user2.email]
        assert 'password' in mail.outbox[1].subject.lower()
