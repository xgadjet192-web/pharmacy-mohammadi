from django.urls import path
from . import views

urlpatterns = [

    # ── صفحه اصلی و لاگین ──────────────────────────────────────
    path("", views.home, name="home"),
    path("staff/login/", views.login_staff, name="login_staff"),
    path("staff/logout/", views.logout_staff, name="logout_staff"),

    # ── داشبورد ─────────────────────────────────────────────────
    path("staff/dashboard/", views.staff_dashboard, name="staff_dashboard"),
    path("staff/ping/", views.online_ping, name="online_ping"),

    # ── محصولات ─────────────────────────────────────────────────
    path("products/", views.product_list, name="product_list"),
    path("products/add/", views.product_add, name="product_add"),
    path("products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("products/<int:pk>/quick-edit/", views.product_quick_edit, name="product_quick_edit"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),
    path("products/<int:pk>/restore/", views.product_restore, name="product_restore"),
    path("products/<int:pk>/destroy/", views.product_destroy, name="product_destroy"),
    path("products/bulk-action/", views.product_bulk_action, name="product_bulk_action"),
    path("products/trash/", views.product_trash, name="product_trash"),

    # ── خروجی‌ها ────────────────────────────────────────────────
    path("products/export/excel/", views.export_excel, name="export_excel"),
    path("products/export/access/", views.export_access, name="export_access"),

    # ── ذخیره‌سازی ──────────────────────────────────────────────
    path("products/save-to-site/", views.save_to_site, name="save_to_site"),
    path("products/save-to-accounting/", views.save_to_accounting, name="save_to_accounting"),

    # ── دسته‌بندی‌ها ─────────────────────────────────────────────
    path("categories/", views.category_list, name="category_list"),
    path("categories/add/", views.category_add, name="category_add"),
    path("categories/<int:pk>/edit/", views.category_edit, name="category_edit"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),

    # ── تیکت‌ها ─────────────────────────────────────────────────
    path("tickets/", views.ticket_list, name="ticket_list"),
    path("tickets/create/", views.ticket_create, name="ticket_create"),
    path("tickets/<int:pk>/", views.ticket_detail, name="ticket_detail"),
    path("tickets/<int:pk>/close/", views.ticket_close, name="ticket_close"),

    # ── اعلانات ─────────────────────────────────────────────────
    path("notifications/", views.notification_list, name="notification_list"),
    path("notifications/<int:pk>/read/", views.notification_read, name="notification_read"),

    # ── به‌روزرسانی‌ها ────────────────────────────────────────────
    path("updates/", views.updates_list, name="updates_list"),
    path("updates/<int:pk>/confirm/", views.update_confirm, name="update_confirm"),

    # ── پروفایل و آواتار ─────────────────────────────────────────
    path("profile/", views.profile_view, name="profile_view"),
    path("profile/avatar/", views.avatar_select, name="avatar_select"),
    path("profile/password/", views.change_password, name="change_password"),

    # ── تنظیمات ─────────────────────────────────────────────────
    path("settings/financial/", views.settings_financial, name="settings_financial"),
    path("settings/accounting/", views.settings_accounting, name="settings_accounting"),
    path("settings/products/", views.settings_products, name="settings_products"),

    # ── راهنما ──────────────────────────────────────────────────
    path("help/rules/", views.help_rules, name="help_rules"),
    path("help/guide/", views.help_guide, name="help_guide"),
    path("help/articles/", views.help_articles, name="help_articles"),

    # ── پشتیبانی ────────────────────────────────────────────────
    path("support/contact/", views.support_contact, name="support_contact"),
    path("support/accounting/", views.support_accounting, name="support_accounting"),

    # ── ماشین حساب ──────────────────────────────────────────────
    path("calculator/", views.calculator_view, name="calculator_view"),

    # ── بانک دارو ───────────────────────────────────────────────
    path("drug-bank/", views.drug_bank, name="drug_bank"),
    path("drug-bank/<int:pk>/to-product/", views.drug_to_product, name="drug_to_product"),
    
    path("drug-bank/", views.drug_bank, name="drug_bank"),
    path("drug-bank/<int:pk>/to-product/", views.drug_to_product, name="drug_to_product"),
    
    path('ai-chat/', views.ai_chat, name='ai_chat'),
    path('setup-admin-x9z2/', views.temp_setup_admin, name='temp_setup_admin'),
]
