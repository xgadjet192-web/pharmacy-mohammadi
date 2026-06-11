# config/urls.py
from django.contrib import admin
from django.urls import path, include
from pharmacy import views as pharmacy_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", pharmacy_views.login_staff, name="login_staff"),
    path("pharmacy/", include("pharmacy.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)