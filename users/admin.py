from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import ActivityLog, EmailOTP, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ('email',)
    list_display = (
        'email',
        'name',
        'role',
        'is_email_verified',
        'is_staff',
        'is_active',
    )
    list_filter = ('role', 'is_staff', 'is_active', 'is_email_verified')
    search_fields = ('email', 'name', 'phone_number')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Profile', {'fields': ('name', 'phone_number', 'role', 'organization')}),
        ('Verification', {'fields': ('is_email_verified', 'is_active')}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'name',
                'phone_number',
                'role',
                'organization',
                'password1',
                'password2',
                'is_staff',
                'is_superuser',
            ),
        }),
    )
    readonly_fields = ('date_joined', 'last_login')


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'entity_type', 'entity_id')
    list_filter = ('action', 'entity_type')
    search_fields = ('user__email', 'entity_id', 'description')
    readonly_fields = ('log_id', 'user', 'action', 'entity_type', 'entity_id', 'description', 'ip_address', 'created_at')


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ('user', 'purpose', 'attempts', 'expires_at', 'used_at', 'created_at')
    list_filter = ('purpose', 'used_at')
    readonly_fields = ('otp_hash', 'expires_at', 'attempts', 'resend_available_at', 'used_at', 'created_at')
