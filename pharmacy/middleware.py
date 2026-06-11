# pharmacy/middleware.py
import threading
from django.utils import timezone

_thread_local = threading.local()


def get_current_tenant_db():
    return getattr(_thread_local, 'tenant_db', None)


class TenantMiddleware:
    """
    هر request که می‌آد، دیتابیس tenant رو تشخیص می‌ده
    و توی thread-local ذخیره می‌کنه.
    همچنین last_seen کاربر رو آپدیت می‌کنه.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_local.tenant_db = None

        if request.user.is_authenticated:
            username = request.user.username
            from django.conf import settings
            if username in settings.DATABASES:
                _thread_local.tenant_db = username

            # ── آپدیت last_seen هر ۳۰ ثانیه یه‌بار ─────────────
            from pharmacy.models import PharmacyUser
            try:
                last = request.user.last_seen
                now  = timezone.now()
                if not last or (now - last).total_seconds() > 30:
                    PharmacyUser.objects.filter(pk=request.user.pk).update(
                        last_seen=now,
                        is_online=True,
                    )
                # ── ثبت فعالیت ──────────────────────────────────
                from pharmacy.models import UserActivity
                UserActivity.objects.create(
                    user       = request.user,
                    action     = f"بازدید از {request.path}",
                    path       = request.path,
                    ip_address = self._get_ip(request),
                )
            except Exception:
                pass

        response = self.get_response(request)

        _thread_local.tenant_db = None
        return response

    @staticmethod
    def _get_ip(request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')