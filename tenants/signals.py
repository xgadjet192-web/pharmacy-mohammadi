# tenants/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
import os
import subprocess
import logging

logger = logging.getLogger(__name__)


def get_pharmacy_user_model():
    from pharmacy.models import PharmacyUser
    return PharmacyUser


@receiver(post_save, sender='pharmacy.PharmacyUser')
def create_pharmacy_database(sender, instance, created, **kwargs):
    """
    وقتی کاربر جدید ساخته می‌شه، یه دیتابیس SQLite جداگانه براش می‌سازه
    و migrate می‌کنه روی اون دیتابیس.
    """
    if not created:
        return

    username = instance.username
    db_dir   = os.path.join(settings.BASE_DIR, 'tenants', 'db')
    os.makedirs(db_dir, exist_ok=True)

    db_name = f"pharmacyuser_{username}.sqlite3"
    db_path = os.path.join(db_dir, db_name)

    # ── ساخت فایل دیتابیس ──────────────────────────────────────
    if not os.path.exists(db_path):
        open(db_path, 'w').close()
        logger.info(f"[Tenant] دیتابیس جدید ساخته شد: {db_path}")

    # ── اضافه کردن دیتابیس به settings در حافظه (runtime) ─────
    if username not in settings.DATABASES:
        settings.DATABASES[username] = {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME':   db_path,
        }

    # ── migrate روی دیتابیس جدید ───────────────────────────────
    try:
        manage_py = os.path.join(settings.BASE_DIR, 'manage.py')
        result = subprocess.run(
            ['python', manage_py, 'migrate', '--database', username, '--run-syncdb'],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            logger.info(f"[Tenant] migrate موفق برای: {username}")
        else:
            logger.error(f"[Tenant] migrate ناموفق برای {username}: {result.stderr}")
    except Exception as e:
        logger.error(f"[Tenant] خطا در migrate برای {username}: {e}")