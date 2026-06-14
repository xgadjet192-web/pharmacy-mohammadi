import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Create or reset an admin/staff user from environment variables"

    def handle(self, *args, **options):
        User = get_user_model()

        username = os.environ.get('ADMIN_USERNAME', 'admin')
        password = os.environ.get('ADMIN_PASSWORD')
        email    = os.environ.get('ADMIN_EMAIL', '')

        if not password:
            self.stdout.write(self.style.ERROR(
                'ADMIN_PASSWORD environment variable is not set.'
            ))
            return

        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': email}
        )

        user.set_password(password)
        user.is_staff     = True
        user.is_superuser = True
        user.is_active    = True
        if email:
            user.email = email
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(
                f'New user "{username}" created successfully.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Password for existing user "{username}" reset successfully.'
            ))