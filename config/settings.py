# config/settings.py ← (در محیط واقعی حتماً عوض کنید!) ────────────────────
SECRET_KEY = 'nbrw-8k0_ojy=d36c=uu^=71w3f)3-sk!=yjjbf)e#*56svm6w'

# ── Debug mode (disable in production) ──────────────────────────────────────
# ── حالت دیباگ (در محیط واقعی غیرفعال کنید) ──────────────────────────────
DEBUG = True

# ── Allowed hosts ────────────────────────────────────────────────────────────
# ── هاست‌های مجاز ────────────────────────────────────────────────────────────
import os
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'pharmacy-ol9y.onrender.com', '.onrender.com']

# ── Installed Django apps ────────────────────────────────────────────────────
# ── اپلیکیشن‌های نصب‌شده ─────────────────────────────────────────────────────
INSTALLED_APPS = [
    'jazzmin',                          # Admin UI theme / تم پنل ادمین
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tenants.apps.TenantsConfig',
    'pharmacy',
]

# ── Middleware stack ──────────────────────────────────────────────────────────
# ── میان‌افزارها ──────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'pharmacy.middleware.TenantMiddleware',   # Multi-tenant middleware / میان‌افزار چند داروخانه
]

# ── URL configuration ─────────────────────────────────────────────────────────
# ── تنظیمات URL ──────────────────────────────────────────────────────────────
ROOT_URLCONF = 'config.urls'

# ── Template settings ─────────────────────────────────────────────────────────
# ── تنظیمات قالب‌ها ───────────────────────────────────────────────────────────
from pathlib import Path
import os
BASE_DIR = Path(__file__).resolve().parent.parent

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ── WSGI application ──────────────────────────────────────────────────────────
# ── اپلیکیشن WSGI ────────────────────────────────────────────────────────────
WSGI_APPLICATION = 'config.wsgi.application'

# ── Database configuration (default + dynamic tenants) ───────────────────────
# ── تنظیمات دیتابیس (پیش‌فرض + داروخانه‌های پویا) ──────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME':   BASE_DIR / 'db.sqlite3',
    }
}

# ── Password validators ───────────────────────────────────────────────────────
# ── اعتبارسنجی رمز عبور ──────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Localization ──────────────────────────────────────────────────────────────
# ── محلی‌سازی ────────────────────────────────────────────────────────────────
LANGUAGE_CODE = 'fa-ir'
TIME_ZONE     = 'Asia/Tehran'
USE_I18N      = True
USE_TZ        = True

# ── Static & Media files ──────────────────────────────────────────────────────
# ── فایل‌های استاتیک و رسانه ─────────────────────────────────────────────────
STATIC_URL       = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
    BASE_DIR / 'pharmacy' / 'static',
]
STATIC_ROOT = BASE_DIR / 'static_collected'
MEDIA_URL   = '/media/'
MEDIA_ROOT  = BASE_DIR / 'media'

# ── Default primary key field ─────────────────────────────────────────────────
# ── نوع پیش‌فرض کلید اصلی ────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL    = 'pharmacy.PharmacyUser'

# ── Login URLs ────────────────────────────────────────────────────────────────
# ── آدرس‌های ورود ────────────────────────────────────────────────────────────
LOGIN_URL          = '/pharmacy/staff/login/'
LOGIN_REDIRECT_URL = '/pharmacy/staff/panel/'

# ── Tenant database directory (auto-loaded from tenants/db) ──────────────────
# ── مسیر دیتابیس‌های داروخانه‌ها (بارگذاری خودکار) ──────────────────────────
TENANT_DB_DIR = os.path.join(BASE_DIR, 'tenants', 'db')

def get_dynamic_databases():
    """Load per-tenant SQLite databases automatically from tenants/db folder.
    دیتابیس‌های هر داروخانه را به‌صورت خودکار از پوشه tenants/db بارگذاری می‌کند."""
    dbs = {}
    if os.path.exists(TENANT_DB_DIR):
        for file in os.listdir(TENANT_DB_DIR):
            if file.startswith('pharmacyuser_') and file.endswith('.sqlite3'):
                username = file.replace('pharmacyuser_', '').replace('.sqlite3', '')
                dbs[username] = {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME':   os.path.join(TENANT_DB_DIR, file),
                }
    return dbs

DATABASES.update(get_dynamic_databases())

# ── External accounting API (optional integration) ────────────────────────────
# ── API حسابداری خارجی (اختیاری) ─────────────────────────────────────────────
ACCOUNTING_API_URL   = ''
ACCOUNTING_API_KEY   = ''
ACCOUNTING_API_TOKEN = ''

# ── Session settings ──────────────────────────────────────────────────────────
# ── تنظیمات نشست ─────────────────────────────────────────────────────────────
SESSION_COOKIE_AGE              = 28800   # 8 hours / ۸ ساعت
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# ── Online status timeout (seconds) ──────────────────────────────────────────
# ── مهلت آنلاین بودن (ثانیه) ─────────────────────────────────────────────────
ONLINE_TIMEOUT_SECONDS = 120   # 2 minutes / ۲ دقیقه

# ── Groq AI API Key ───────────────────────────────────────────────────────────
# ── کلید API هوش مصنوعی گروق ─────────────────────────────────────────────────
GROQ_API_KEY = 'YOUR_GROQ_API_KEY_HERE'

# ══════════════════════════════════════════════════════════════════════════════
# JAZZMIN SETTINGS — تنظیمات پنل ادمین زیبا
# ══════════════════════════════════════════════════════════════════════════════
JAZZMIN_SETTINGS = {
    # ── Site identity / هویت سایت ────────────────────────────────────────────
    "site_title":        "داروخانه",
    "site_header":       "داروخانه",
    "site_brand":        "pharmacy",
    "site_logo":         None,
    "welcome_sign":      "خوش آمدید به پنل مدیریت ",
    "copyright":         "Pharmacy System",

    # ── Search / جستجو ────────────────────────────────────────────────────────
    "search_model": ["pharmacy.PharmacyUser", "pharmacy.Product"],

    # ── Top menu links / لینک‌های منوی بالا ──────────────────────────────────
    "topmenu_links": [
        {"name": "🏠 سایت اصلی",  "url": "/pharmacy/",           "new_window": False},
        {"name": "💊 بانک دارو",   "url": "/pharmacy/drug-bank/", "new_window": False},
        {"name": "🎫 تیکت‌ها",     "url": "/admin/pharmacy/ticket/", "new_window": False},
    ],

    # ── User menu / منوی کاربر ────────────────────────────────────────────────
    "usermenu_links": [
        {"name": "پروفایل من", "url": "/pharmacy/profile/", "new_window": False},
    ],

    # ── Sidebar / نوار کناری ──────────────────────────────────────────────────
    "show_sidebar":          True,
    "navigation_expanded":   True,
    "hide_apps":             [],
    "hide_models":           [],

    # ── Icons / آیکون‌ها ──────────────────────────────────────────────────────
    "icons": {
        "auth":                          "fas fa-shield-alt",
        "auth.Group":                    "fas fa-users",
        "pharmacy.PharmacyUser":         "fas fa-user-md",
        "pharmacy.Product":              "fas fa-pills",
        "pharmacy.Category":             "fas fa-tags",
        "pharmacy.Ticket":               "fas fa-headset",
        "pharmacy.Notification":         "fas fa-bell",
        "pharmacy.SystemUpdate":         "fas fa-sync-alt",
        "pharmacy.UserActivity":         "fas fa-chart-line",
        "pharmacy.NotificationRead":     "fas fa-check-double",
        "pharmacy.UpdateConfirm":        "fas fa-clipboard-check",
    },
    "default_icon_parents":  "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",

    # ── UI extras / تنظیمات اضافی UI ─────────────────────────────────────────
    "related_modal_active": True,
    "show_ui_builder":      False,
    "changeform_format":    "horizontal_tabs",
    "language_chooser":     False,
}

# ── Jazzmin UI Tweaks — ظاهر دارک پرپل ───────────────────────────────────────
JAZZMIN_UI_TWEAKS = {
    "navbar_small_text":          False,
    "footer_small_text":          False,
    "body_small_text":            False,
    "brand_small_text":           False,
    "brand_colour":               "navbar-purple",
    "accent":                     "accent-purple",
    "navbar":                     "navbar-dark",
    "no_navbar_border":           True,
    "navbar_fixed":               True,
    "layout_boxed":               False,
    "footer_fixed":               False,
    "sidebar_fixed":              True,
    "sidebar":                    "sidebar-dark-purple",
    "sidebar_nav_small_text":     False,
    "sidebar_disable_expand":     False,
    "sidebar_nav_child_indent":   True,
    "sidebar_nav_compact_style":  False,
    "sidebar_nav_legacy_style":   False,
    "sidebar_nav_flat_style":     False,
    "theme":                      "darkly",
    "dark_mode_theme":            "darkly",
    "button_classes": {
        "primary":   "btn-primary",
        "secondary": "btn-secondary",
        "info":      "btn-info",
        "warning":   "btn-warning",
        "danger":    "btn-danger",
        "success":   "btn-success",
    },
}