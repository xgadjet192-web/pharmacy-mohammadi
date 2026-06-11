# config/db_router.py
from django.conf import settings


class PharmacyRouter:
    """
    اگر request در حافظه باشه و username داشته باشه،
    مدل‌های Product و Category رو روی دیتابیس اون کاربر می‌فرسته.
    """

    TENANT_MODELS = {'product', 'category'}

    def _get_tenant_db(self):
        """دیتابیس فعلی tenant رو از thread-local یا settings می‌گیره"""
        try:
            from pharmacy.middleware import get_current_tenant_db
            return get_current_tenant_db()
        except Exception:
            return None

    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'pharmacy' and \
                model._meta.model_name in self.TENANT_MODELS:
            db = self._get_tenant_db()
            if db and db in settings.DATABASES:
                return db
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'pharmacy' and \
                model._meta.model_name in self.TENANT_MODELS:
            db = self._get_tenant_db()
            if db and db in settings.DATABASES:
                return db
        return None

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # migrate مدل‌های اصلی فقط روی default
        if db == 'default':
            return True
        # روی دیتابیس‌های tenant فقط product و category
        if model_name in self.TENANT_MODELS and app_label == 'pharmacy':
            return True
        return False