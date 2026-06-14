import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from pharmacy.models import PharmacyUser

username = "amir"
password = "Amir12345"

user, created = PharmacyUser.objects.get_or_create(username=username)
user.set_password(password)
user.is_active = True
user.save()

print("Created" if created else "Updated", "user:", username, "/ password:", password)