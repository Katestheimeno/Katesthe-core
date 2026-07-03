"""
Admin mixins for common functionality.
"""

from django.utils.html import format_html


class CopyableFieldMixin:
    """
    Mixin that provides copyable field functionality for Django admin.

    Usage:
        from unfold.admin import ModelAdmin
        class MyModelAdmin(CopyableFieldMixin, ModelAdmin):
            def my_copyable_field(self, obj):
                return self.copyable_field(obj.my_field, 'My Field')
    """

    def copyable_field(self, value, field_name=None, css_class='copy-field',
                        default_display='-', copy_success_message=None):
        """
        Create a copyable field with click-to-copy functionality.

        Args:
            value: The value to be copied
            field_name: Display name for the field (optional)
            css_class: CSS class for styling (default: 'copy-field')
            default_display: What to show when value is empty (default: '-')
            copy_success_message: Custom success message (optional)

        Returns:
            HTML string with copyable functionality
        """
        if not value:
            return default_display

        if copy_success_message is None:
            copy_success_message = f'{field_name or "Value"} copied to clipboard!'

        return format_html(
            '<span class="{}" data-code="{}" title="Click to copy {}">{}</span>',
            css_class,
            value,
            field_name or 'value',
            value
        )

    def copyable_email(self, obj, field_name='email', field_label=None):
        """
        Create a copyable email field.

        Args:
            obj: The model instance
            field_name: Name of the email field (default: 'email')
            field_label: Display label for the field (optional)

        Returns:
            HTML string with copyable email functionality
        """
        value = getattr(obj, field_name, None)
        label = field_label or field_name.title()

        return self.copyable_field(
            value=value,
            field_name=label,
            css_class='copy-field',
            copy_success_message='Email copied to clipboard!'
        )

    def copyable_text(self, obj, field_name, field_label=None):
        """
        Create a copyable text field.

        Args:
            obj: The model instance
            field_name: Name of the field to copy
            field_label: Display label for the field (optional)

        Returns:
            HTML string with copyable text functionality
        """
        value = getattr(obj, field_name, None)
        label = field_label or field_name.title()

        return self.copyable_field(
            value=value,
            field_name=label,
            css_class='copy-field',
            copy_success_message=f'{label} copied to clipboard!'
        )

    def copyable_code(self, obj, field_name, field_label=None):
        """
        Create a copyable code field (like promo codes, tokens, etc.).

        Args:
            obj: The model instance
            field_name: Name of the field to copy
            field_label: Display label for the field (optional)

        Returns:
            HTML string with copyable code functionality
        """
        value = getattr(obj, field_name, None)
        label = field_label or field_name.title()

        return self.copyable_field(
            value=value,
            field_name=label,
            css_class='code-copy',
            copy_success_message=f'{label} copied to clipboard!'
        )

    class Media:
        css = {
            'all': ('utils/admin/css/copy-field.css',)
        }
        js = ('utils/admin/js/copy-field.js',)
