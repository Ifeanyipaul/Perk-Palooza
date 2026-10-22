from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    model = User

    list_display = (
        'username',
        'email',
        'role',
        'is_verified',
        'is_active',
        'is_staff',
    )

    list_filter = (
        'role',
        'is_verified',
        'is_active',
    )

    fieldsets = UserAdmin.fieldsets + (
        ('Perk Palooza Information', {
            'fields': (
                'role',
                'phone_number',
                'is_verified',
            )
        }),
    )