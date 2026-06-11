# tenants/apps.py
from django.apps import AppConfig


class TenantsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name               = 'tenants'
    verbose_name       = 'مدیریت تنانت‌ها'

    def ready(self):
        import tenants.signals  # noqa — ثبت signal‌ها