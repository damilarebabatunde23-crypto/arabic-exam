import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Create or update a superuser/teacher account from the ADMIN_USERNAME, '
        'ADMIN_PASSWORD and ADMIN_EMAIL environment variables. Safe to run on '
        'every deploy: does nothing if those variables are not set.'
    )

    def handle(self, *args, **options):
        username = os.environ.get('ADMIN_USERNAME')
        password = os.environ.get('ADMIN_PASSWORD')
        email = os.environ.get('ADMIN_EMAIL', '')

        if not username or not password:
            self.stdout.write('ADMIN_USERNAME/ADMIN_PASSWORD not set, skipping.')
            return

        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        if email:
            user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        self.stdout.write(self.style.SUCCESS(
            f'{"Created" if created else "Updated"} admin account "{username}".'
        ))
