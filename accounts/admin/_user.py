"""
User action
"""
from django.contrib import admin
from unfold.admin import ModelAdmin  # Unfold's enhanced ModelAdmin
from accounts.models import User


@admin.register(User)
class UserAdmin(ModelAdmin):
    """
    Admin panel configuration for the custom User model.
    Uses Unfold's ModelAdmin for improved UI.
    """

    # Fields displayed in list view
    list_display = ("id", "username", "email", "is_active",
                    "is_verified", "is_staff", "date_joined")
    list_filter = ("is_active", "is_verified", "is_staff",
                   "is_superuser", "date_joined")
    search_fields = ("username", "email")
    ordering = ("-date_joined",)
    readonly_fields = ("date_joined", "last_login", "updated_at")

    # Fieldsets (grouping in detail view)
    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        ("Status", {"fields": ("is_active",
         "is_verified", "is_staff", "is_superuser")}),
        ("Important dates", {
         "fields": ("date_joined", "last_login", "updated_at")}),
        ("Permissions", {"fields": ("groups", "user_permissions")}),
    )

    # Extra options for Unfold (like table settings)
    unfold_list_display = {
        "default_columns": ["id", "username", "email", "is_verified", "date_joined"],
        "collapse_filters": True,
    }
