# staff/urls.py
from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('dashboard/', views.staff_dashboard_view, name='staff_dashboard'),
]

# این بخش فقط برای ارائه فایل‌های استاتیک در حالت توسعه (DEBUG=True) لازمه
# اگر از esbuild برای ساخت bundle.js استفاده می‌کنی، ممکنه لازم نباشه
# ولی برای اطمینان، اینجا نگهش می‌داریم
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
