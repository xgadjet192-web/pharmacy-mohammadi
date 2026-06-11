# pharmacy/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone
from .models import (
    PharmacyUser, Category, Product,
    Ticket, Notification, SystemUpdate,
    UpdateConfirm, UserActivity, NotificationRead,
)
from .forms import PharmacyUserCreationForm, PharmacyUserChangeForm


# ══════════════════════════════════════════════════════════════════
#  PharmacyUser
# ══════════════════════════════════════════════════════════════════

@admin.register(PharmacyUser)
class PharmacyUserAdmin(UserAdmin):
    add_form = PharmacyUserCreationForm
    form     = PharmacyUserChangeForm
    model    = PharmacyUser

    list_display  = ('username', 'pharmacy_name', 'account_type', 'is_active', 'last_seen', 'is_currently_online')
    list_filter   = ('account_type', 'is_active')
    search_fields = ('username', 'pharmacy_name', 'email')

    add_fieldsets = (
        ('اطلاعات ورود', {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'account_type'),
        }),
        ('پروفایل', {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'email', 'phone', 'pharmacy_name', 'address', 'postal_code', 'profile_image', 'avatar_type'),
        }),
        ('فعال‌سازی', {
            'classes': ('wide',),
            'fields': ('is_active',),
        }),
    )

    fieldsets = (
        ('اطلاعات ورود',  {'fields': ('username', 'password')}),
        ('پروفایل',       {'fields': ('first_name', 'last_name', 'email', 'phone', 'pharmacy_name', 'address', 'postal_code', 'profile_image', 'avatar_type')}),
        ('دسترسی',        {'fields': ('is_active', 'account_type', 'is_staff', 'is_superuser')}),
        ('وضعیت آنلاین',  {'fields': ('last_seen', 'is_online')}),
    )
    readonly_fields = ('last_seen', 'is_online')

    @admin.display(boolean=True, description='آنلاین')
    def is_currently_online(self, obj):
        return obj.is_currently_online

    def save_model(self, request, obj, form, change):
        acc = form.cleaned_data.get('account_type', 'staff')
        if acc == 'admin':
            obj.is_staff = True
            obj.is_superuser = True
        elif acc in ('staff', 'pharmacist', 'chemist', 'accountant', 'doctor'):
            obj.is_staff = False
            obj.is_superuser = False
        super().save_model(request, obj, form, change)


# ══════════════════════════════════════════════════════════════════
#  Category
# ══════════════════════════════════════════════════════════════════

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ('name', 'product_count')
    search_fields = ('name',)

    @admin.display(description='تعداد محصولات')
    def product_count(self, obj):
        return obj.products.filter(is_deleted=False).count()


# ══════════════════════════════════════════════════════════════════
#  Product
# ══════════════════════════════════════════════════════════════════

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display  = ('code', 'name', 'category', 'price', 'discount_percent', 'final_price_display', 'is_active', 'accounting_status', 'created_at')
    list_filter   = ('is_active', 'is_deleted', 'category', 'accounting_status')
    search_fields = ('name', 'code')
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='قیمت نهایی')
    def final_price_display(self, obj):
        return f'{obj.final_price:,} تومان'


# ══════════════════════════════════════════════════════════════════
#  Ticket
# ══════════════════════════════════════════════════════════════════

class TicketReplyInline(admin.StackedInline):
    model        = Ticket
    fields       = ('admin_reply', 'status')
    extra        = 0
    can_delete   = False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display  = ('title', 'user', 'status', 'priority', 'created_at')
    list_filter   = ('status', 'priority')
    search_fields = ('title', 'user__username')
    readonly_fields = ('created_at', 'updated_at', 'user', 'message')
    fields        = ('user', 'title', 'message', 'priority', 'status', 'admin_reply', 'replied_at', 'created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        if obj.admin_reply and not obj.replied_at:
            obj.replied_at = timezone.now()
            if obj.status == 'open':
                obj.status = 'answered'
        super().save_model(request, obj, form, change)


# ══════════════════════════════════════════════════════════════════
#  Notification
# ══════════════════════════════════════════════════════════════════

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ('title', 'notif_type', 'target_user', 'is_active', 'created_at')
    list_filter   = ('notif_type', 'is_active')
    search_fields = ('title', 'message')


# ══════════════════════════════════════════════════════════════════
#  SystemUpdate
# ══════════════════════════════════════════════════════════════════

@admin.register(SystemUpdate)
class SystemUpdateAdmin(admin.ModelAdmin):
    list_display  = ('title', 'version', 'requires_confirm', 'is_active', 'created_at')
    list_filter   = ('is_active', 'requires_confirm')


# ══════════════════════════════════════════════════════════════════
#  UserActivity
# ══════════════════════════════════════════════════════════════════

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display  = ('user', 'action', 'path', 'ip_address', 'created_at')
    list_filter   = ('user',)
    search_fields = ('user__username', 'action')
    readonly_fields = ('user', 'action', 'path', 'ip_address', 'created_at')

    def has_add_permission(self, request):
        return False