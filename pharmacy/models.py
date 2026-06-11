# pharmacy/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


# ══════════════════════════════════════════════════════════════════
#  PharmacyUser — کاربر داروخانه
# ══════════════════════════════════════════════════════════════════

class PharmacyUser(AbstractUser):

    ACCOUNT_TYPE_CHOICES = [
        ('admin',       'مدیر کل'),
        ('staff',       'پرسنل'),
        ('pharmacist',  'داروساز'),
        ('chemist',     'شیمی‌دان'),
        ('accountant',  'حسابدار'),
        ('doctor',      'دکتر'),
    ]

    AVATAR_CHOICES = [
        ('doctor',      'دکتر'),
        ('pharmacist',  'داروساز'),
        ('chemist',     'شیمی‌دان'),
        ('accountant',  'حسابدار'),
        ('staff',       'پرسنل'),
        ('custom',      'عکس شخصی'),
    ]

    phone         = models.CharField(max_length=15, blank=True, null=True, verbose_name=_("شماره تلفن"))
    address       = models.TextField(blank=True, null=True, verbose_name=_("آدرس"))
    postal_code   = models.CharField(max_length=10, blank=True, null=True, verbose_name=_("کد پستی"))
    profile_image = models.ImageField(upload_to='profile_pics/', blank=True, null=True, verbose_name=_("تصویر پروفایل"))
    is_active     = models.BooleanField(default=True, verbose_name=_("فعال"))
    account_type  = models.CharField(
        max_length=20, choices=ACCOUNT_TYPE_CHOICES,
        default='staff', verbose_name=_("نوع حساب")
    )
    avatar_type   = models.CharField(
        max_length=20, choices=AVATAR_CHOICES,
        default='staff', verbose_name=_("نوع آواتار")
    )
    pharmacy_name = models.CharField(max_length=200, blank=True, null=True, verbose_name=_("نام داروخانه"))
    last_seen     = models.DateTimeField(null=True, blank=True, verbose_name=_("آخرین بازدید"))
    is_online     = models.BooleanField(default=False, verbose_name=_("آنلاین"))

    USERNAME_FIELD  = 'username'
    REQUIRED_FIELDS = ['email']

    @property
    def is_currently_online(self):
        if not self.last_seen:
            return False
        return (timezone.now() - self.last_seen).total_seconds() < 120

    def __str__(self):
        return self.get_full_name() or self.username

    class Meta:
        verbose_name        = _("کاربر داروخانه")
        verbose_name_plural = _("کاربران داروخانه")


# ══════════════════════════════════════════════════════════════════
#  Category — دسته‌بندی محصولات داروخانه
# ══════════════════════════════════════════════════════════════════

class Category(models.Model):
    name       = models.CharField(max_length=100, verbose_name=_("نام دسته‌بندی"))
    created_at = models.DateTimeField(default=timezone.now, verbose_name=_("تاریخ ایجاد"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name        = _("دسته‌بندی")
        verbose_name_plural = _("دسته‌بندی‌ها")
        ordering            = ['name']


# ══════════════════════════════════════════════════════════════════
#  Product — محصول
# ══════════════════════════════════════════════════════════════════

class Product(models.Model):
    name        = models.CharField(max_length=200, verbose_name=_("نام محصول"))
    code        = models.CharField(max_length=50, unique=True, verbose_name=_("کد محصول"))
    category    = models.ForeignKey(
        Category, on_delete=models.SET_NULL,
        related_name='products', verbose_name=_("دسته‌بندی"),
        null=True, blank=True
    )
    description      = models.TextField(blank=True, null=True, verbose_name=_("توضیحات"))
    image            = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name=_("تصویر"))
    price            = models.DecimalField(max_digits=12, decimal_places=0, verbose_name=_("قیمت (تومان)"))
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=_("تخفیف (%)"))
    is_active        = models.BooleanField(default=True, verbose_name=_("فعال"))
    is_deleted       = models.BooleanField(default=False, verbose_name=_("حذف شده"))

    ACCOUNTING_STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('synced',  'همگام‌سازی شده'),
        ('failed',  'خطا'),
    ]
    accounting_status = models.CharField(
        max_length=20, choices=ACCOUNTING_STATUS_CHOICES,
        default='pending', verbose_name=_("وضعیت حسابداری")
    )

    created_at = models.DateTimeField(default=timezone.now, verbose_name=_("تاریخ بارگذاری"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("آخرین ویرایش"))

    @property
    def discount_amount(self):
        return int(self.price * self.discount_percent / 100)

    @property
    def final_price(self):
        return int(self.price) - self.discount_amount

    def __str__(self):
        return f"{self.code} — {self.name}"

    class Meta:
        verbose_name        = _("محصول")
        verbose_name_plural = _("محصولات")
        ordering            = ['-created_at']


# ══════════════════════════════════════════════════════════════════
#  DrugCategory — دسته‌بندی بانک دارویی
# ══════════════════════════════════════════════════════════════════

class DrugCategory(models.Model):
    """دسته‌بندی‌های اصلی بانک دارویی"""

    ICON_CHOICES = [
        ('pill',        '💊 قرص / کپسول'),
        ('syringe',     '💉 آمپول / تزریقی'),
        ('bottle',      '🧴 شربت / قطره'),
        ('tube',        '🟡 پماد / کرم / ژل'),
        ('supplement',  '🌿 مکمل / ویتامین'),
        ('bandage',     '🩹 پانسمان / زخم'),
        ('hygiene',     '🧼 بهداشتی'),
        ('cosmetic',    '💄 آرایشی'),
        ('sexual',      '❤️ سلامت جنسی'),
        ('orthopedic',  '🦴 ارتوپدی / فیزیوتراپی'),
        ('eye',         '👁 چشم / گوش / بینی'),
        ('baby',        '👶 کودک / نوزاد'),
        ('herbal',      '🌱 گیاهی / طبیعی'),
        ('device',      '🩺 تجهیزات پزشکی'),
        ('other',       '📦 سایر'),
    ]

    name        = models.CharField(max_length=100, verbose_name=_("نام دسته"))
    name_en     = models.CharField(max_length=100, blank=True, verbose_name=_("نام انگلیسی"))
    icon        = models.CharField(max_length=20, choices=ICON_CHOICES, default='other', verbose_name=_("آیکون"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    order       = models.PositiveIntegerField(default=0, verbose_name=_("ترتیب نمایش"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name        = _("دسته دارویی")
        verbose_name_plural = _("دسته‌بندی‌های دارویی")
        ordering            = ['order', 'name']


# ══════════════════════════════════════════════════════════════════
#  Drug — بانک جامع دارویی
# ══════════════════════════════════════════════════════════════════

class Drug(models.Model):
    """
    بانک جامع دارویی — شامل همه داروها، مکمل‌ها، پمادها،
    شربت‌ها، آمپول‌ها، لوازم بهداشتی، آرایشی، ارتوپدی و غیره
    """

    FORM_CHOICES = [
        ('tablet',      'قرص'),
        ('capsule',     'کپسول'),
        ('syrup',       'شربت'),
        ('drop',        'قطره'),
        ('injection',   'آمپول / تزریقی'),
        ('serum',       'سرم'),
        ('ointment',    'پماد'),
        ('cream',       'کرم'),
        ('gel',         'ژل'),
        ('spray',       'اسپری'),
        ('inhaler',     'اینهالر'),
        ('patch',       'پچ / چسب'),
        ('suppository', 'شیاف'),
        ('powder',      'پودر'),
        ('solution',    'محلول'),
        ('lotion',      'لوسیون'),
        ('shampoo',     'شامپو'),
        ('soap',        'صابون'),
        ('device',      'دستگاه / تجهیزات'),
        ('bandage',     'باند / گاز / پانسمان'),
        ('other',       'سایر'),
    ]

    OTCPX_CHOICES = [
        ('otc', 'بدون نسخه (OTC)'),
        ('rx',  'نیاز به نسخه (Rx)'),
        ('na',  'غیر دارویی'),
    ]

    # ── اطلاعات اصلی ───────────────────────────────────────────
    name_fa      = models.CharField(max_length=300, verbose_name=_("نام فارسی"))
    name_en      = models.CharField(max_length=300, blank=True, verbose_name=_("نام انگلیسی / ژنریک"))
    brand_name   = models.CharField(max_length=300, blank=True, verbose_name=_("نام تجاری / برند"))
    category     = models.ForeignKey(
        DrugCategory, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='drugs', verbose_name=_("دسته‌بندی")
    )
    drug_form    = models.CharField(
        max_length=20, choices=FORM_CHOICES,
        default='tablet', verbose_name=_("فرم دارو")
    )
    otc_rx       = models.CharField(
        max_length=5, choices=OTCPX_CHOICES,
        default='otc', verbose_name=_("نسخه‌ای / بدون نسخه")
    )

    # ── اطلاعات دارویی ─────────────────────────────────────────
    active_ingredient = models.CharField(max_length=500, blank=True, verbose_name=_("ماده مؤثره"))
    strength          = models.CharField(max_length=100, blank=True, verbose_name=_("دوز / قدرت (مثلاً ۵۰۰mg)"))
    manufacturer      = models.CharField(max_length=200, blank=True, verbose_name=_("تولیدکننده"))
    country_of_origin = models.CharField(max_length=100, blank=True, default='ایران', verbose_name=_("کشور سازنده"))

    # ── علائم، کاربرد، دسته دارویی ────────────────────────────
    indications   = models.TextField(
        blank=True,
        verbose_name=_("موارد مصرف / علائمی که برای آن تجویز می‌شود"),
        help_text="مثال: سردرد، تب، درد، التهاب، عفونت باکتریایی"
    )
    drug_class    = models.CharField(
        max_length=200, blank=True,
        verbose_name=_("خانواده دارویی"),
        help_text="مثال: آنتی‌بیوتیک، NSAID، بتابلاکر، بنزودیازپین"
    )
    contraindications = models.TextField(blank=True, verbose_name=_("موارد منع مصرف"))
    side_effects      = models.TextField(blank=True, verbose_name=_("عوارض جانبی"))
    interactions      = models.TextField(blank=True, verbose_name=_("تداخلات دارویی"))
    storage           = models.CharField(max_length=200, blank=True, verbose_name=_("شرایط نگهداری"))
    notes             = models.TextField(blank=True, verbose_name=_("توضیحات تکمیلی"))

    # ── کلمات کلیدی جستجو ─────────────────────────────────────
    search_keywords = models.TextField(
        blank=True,
        verbose_name=_("کلمات کلیدی جستجو"),
        help_text="کلماتی که کاربر ممکن است با آن جستجو کند — جدا با ویرگول"
    )

    # ── وضعیت ──────────────────────────────────────────────────
    is_active    = models.BooleanField(default=True, verbose_name=_("فعال"))
    is_verified  = models.BooleanField(default=False, verbose_name=_("تأیید شده توسط متخصص"))
    created_at   = models.DateTimeField(default=timezone.now, verbose_name=_("تاریخ ثبت"))
    updated_at   = models.DateTimeField(auto_now=True, verbose_name=_("آخرین ویرایش"))
    added_by     = models.ForeignKey(
        PharmacyUser, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='added_drugs', verbose_name=_("افزوده توسط")
    )

    def __str__(self):
        parts = [self.name_fa]
        if self.brand_name:
            parts.append(f"({self.brand_name})")
        if self.strength:
            parts.append(self.strength)
        return ' '.join(parts)

    def get_all_searchable_text(self):
        """متن کامل برای جستجو"""
        return ' '.join(filter(None, [
            self.name_fa, self.name_en, self.brand_name,
            self.active_ingredient, self.indications,
            self.drug_class, self.search_keywords,
        ])).lower()

    class Meta:
        verbose_name        = _("دارو")
        verbose_name_plural = _("داروها")
        ordering            = ['name_fa']
        indexes = [
            models.Index(fields=['name_fa']),
            models.Index(fields=['name_en']),
            models.Index(fields=['drug_class']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
        ]


# ══════════════════════════════════════════════════════════════════
#  Ticket — تیکت پشتیبانی
# ══════════════════════════════════════════════════════════════════

class Ticket(models.Model):
    STATUS_CHOICES = [
        ('open',     'در انتظار پاسخ'),
        ('answered', 'پاسخ داده شده'),
        ('closed',   'بسته شده'),
    ]
    PRIORITY_CHOICES = [
        ('low',    'کم'),
        ('medium', 'متوسط'),
        ('high',   'زیاد'),
        ('urgent', 'فوری'),
    ]

    user        = models.ForeignKey(PharmacyUser, on_delete=models.CASCADE, related_name='tickets', verbose_name=_("کاربر"))
    title       = models.CharField(max_length=255, verbose_name=_("عنوان تیکت"))
    message     = models.TextField(verbose_name=_("متن پیام"))
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', verbose_name=_("وضعیت"))
    priority    = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', verbose_name=_("اولویت"))
    admin_reply = models.TextField(blank=True, null=True, verbose_name=_("پاسخ ادمین"))
    replied_at  = models.DateTimeField(null=True, blank=True, verbose_name=_("تاریخ پاسخ"))
    is_read     = models.BooleanField(default=False, verbose_name=_("خوانده شده"))
    created_at  = models.DateTimeField(default=timezone.now, verbose_name=_("تاریخ ثبت"))
    updated_at  = models.DateTimeField(auto_now=True, verbose_name=_("آخرین تغییر"))

    def __str__(self):
        return f"[{self.get_status_display()}] {self.title} — {self.user.username}"

    class Meta:
        verbose_name        = _("تیکت")
        verbose_name_plural = _("تیکت‌ها")
        ordering            = ['-created_at']


# ══════════════════════════════════════════════════════════════════
#  Notification — اعلانات
# ══════════════════════════════════════════════════════════════════

class Notification(models.Model):
    TYPE_CHOICES = [
        ('info',    'اطلاع‌رسانی'),
        ('warning', 'هشدار'),
        ('success', 'موفقیت'),
        ('update',  'به‌روزرسانی'),
        ('urgent',  'فوری'),
    ]

    title       = models.CharField(max_length=255, verbose_name=_("عنوان"))
    message     = models.TextField(verbose_name=_("متن اعلان"))
    notif_type  = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info', verbose_name=_("نوع"))
    is_active   = models.BooleanField(default=True, verbose_name=_("فعال"))
    target_user = models.ForeignKey(
        PharmacyUser, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='targeted_notifications',
        verbose_name=_("کاربر هدف (خالی = همه)")
    )
    created_at  = models.DateTimeField(default=timezone.now, verbose_name=_("تاریخ انتشار"))
    expires_at  = models.DateTimeField(null=True, blank=True, verbose_name=_("تاریخ انقضا"))

    def __str__(self):
        return f"[{self.get_notif_type_display()}] {self.title}"

    class Meta:
        verbose_name        = _("اعلان")
        verbose_name_plural = _("اعلانات")
        ordering            = ['-created_at']


# ══════════════════════════════════════════════════════════════════
#  NotificationRead
# ══════════════════════════════════════════════════════════════════

class NotificationRead(models.Model):
    user         = models.ForeignKey(PharmacyUser, on_delete=models.CASCADE, related_name='read_notifications')
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='reads')
    read_at      = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together     = ('user', 'notification')
        verbose_name        = _("اعلان خوانده‌شده")
        verbose_name_plural = _("اعلانات خوانده‌شده")


# ══════════════════════════════════════════════════════════════════
#  UserActivity
# ══════════════════════════════════════════════════════════════════

class UserActivity(models.Model):
    user       = models.ForeignKey(PharmacyUser, on_delete=models.CASCADE, related_name='activities', verbose_name=_("کاربر"))
    action     = models.CharField(max_length=255, verbose_name=_("عملیات"))
    path       = models.CharField(max_length=500, blank=True, verbose_name=_("مسیر"))
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_("آدرس IP"))
    created_at = models.DateTimeField(default=timezone.now, verbose_name=_("زمان"))

    def __str__(self):
        return f"{self.user.username} — {self.action}"

    class Meta:
        verbose_name        = _("فعالیت کاربر")
        verbose_name_plural = _("فعالیت‌های کاربران")
        ordering            = ['-created_at']


# ══════════════════════════════════════════════════════════════════
#  SystemUpdate
# ══════════════════════════════════════════════════════════════════

class SystemUpdate(models.Model):
    title            = models.CharField(max_length=255, verbose_name=_("عنوان"))
    description      = models.TextField(verbose_name=_("توضیحات"))
    version          = models.CharField(max_length=20, blank=True, verbose_name=_("نسخه"))
    is_active        = models.BooleanField(default=True, verbose_name=_("نمایش"))
    requires_confirm = models.BooleanField(default=False, verbose_name=_("نیاز به تأیید"))
    created_at       = models.DateTimeField(default=timezone.now, verbose_name=_("تاریخ"))

    def __str__(self):
        return f"v{self.version} — {self.title}"

    class Meta:
        verbose_name        = _("به‌روزرسانی سیستم")
        verbose_name_plural = _("به‌روزرسانی‌های سیستم")
        ordering            = ['-created_at']


# ══════════════════════════════════════════════════════════════════
#  UpdateConfirm
# ══════════════════════════════════════════════════════════════════

class UpdateConfirm(models.Model):
    user         = models.ForeignKey(PharmacyUser, on_delete=models.CASCADE, related_name='update_confirms')
    update       = models.ForeignKey(SystemUpdate, on_delete=models.CASCADE, related_name='confirms')
    confirmed    = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together     = ('user', 'update')
        verbose_name        = _("تأیید به‌روزرسانی")
        verbose_name_plural = _("تأییدیه‌های به‌روزرسانی")