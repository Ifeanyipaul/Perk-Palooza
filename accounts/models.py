from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):

    class Role(models.TextChoices):
        GIVER = 'GIVER', 'Giver'
        BUSINESS = 'BUSINESS', 'Business Operator'
        ADMIN = 'ADMIN', 'Platform Admin'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.GIVER
    )

    email = models.EmailField(
        unique=True
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    is_verified = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.username} - {self.role}"