# ══════════════════════════════════════════════════════════════════
#  این کد رو به آخر pharmacy/models.py اضافه کن
# ══════════════════════════════════════════════════════════════════

class DrugCategory(models.Model):
    """دسته‌بندی داروها"""
    name        = models.CharField(max_length=100, unique=True, verbose_name=_("نام دسته"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    icon        = models.CharField(max_length=10, blank=True, default='💊', verbose_name=_("آیکون"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name        = _("دسته‌بندی دارو")
        verbose_name_plural = _("دسته‌بندی‌های دارو")
        ordering            = ['name']


class Drug(models.Model):
    """بانک اطلاعات داروها"""
    FORM_CHOICES = [
        ('tablet',    'قرص'),
        ('capsule',   'کپسول'),
        ('syrup',     'شربت'),
        ('injection', 'آمپول/تزریقی'),
        ('drop',      'قطره'),
        ('cream',     'کرم/پماد'),
        ('powder',    'پودر'),
        ('spray',     'اسپری'),
        ('patch',     'چسب دارویی'),
        ('suppository','شیاف'),
        ('inhaler',   'استنشاقی'),
        ('serum',     'سرم'),
        ('other',     'سایر'),
    ]

    name         = models.CharField(max_length=200, verbose_name=_("نام دارو (فارسی)"))
    name_en      = models.CharField(max_length=200, blank=True, verbose_name=_("نام دارو (انگلیسی)"))
    generic_name = models.CharField(max_length=200, blank=True, verbose_name=_("نام ژنریک"))
    category     = models.ForeignKey(
        DrugCategory, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='drugs',
        verbose_name=_("دسته‌بندی")
    )
    form         = models.CharField(max_length=20, choices=FORM_CHOICES, default='tablet', verbose_name=_("فرم دارویی"))
    dosage       = models.CharField(max_length=100, blank=True, verbose_name=_("دوز / مقدار"))
    description  = models.TextField(blank=True, verbose_name=_("توضیحات / کاربرد"))
    symptoms     = models.TextField(blank=True, verbose_name=_("علائم / موارد مصرف"))
    side_effects = models.TextField(blank=True, verbose_name=_("عوارض جانبی"))
    warnings     = models.TextField(blank=True, verbose_name=_("هشدارها"))
    is_otc       = models.BooleanField(default=False, verbose_name=_("بدون نسخه (OTC)"))
    is_active    = models.BooleanField(default=True, verbose_name=_("فعال"))
    created_at   = models.DateTimeField(default=timezone.now, verbose_name=_("تاریخ ثبت"))

    def __str__(self):
        return f"{self.name} ({self.get_form_display()})"

    class Meta:
        verbose_name        = _("دارو")
        verbose_name_plural = _("داروها")
        ordering            = ['name']