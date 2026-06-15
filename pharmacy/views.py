# ══════════════════════════════════════════════════════════════════
# pharmacy/views.py
# Pharmacy Management System — Main Views File
# سیستم مدیریت داروخانه — فایل اصلی ویوها
# ══════════════════════════════════════════════════════════════════

# ┌─────────────────────────────────────────────────────────────────┐
# │  SECTION 0 — IMPORTS & CONSTANTS                                │
# │  بخش ۰ — وارد کردن کتابخانه‌ها و ثابت‌ها                       │
# └─────────────────────────────────────────────────────────────────┘
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Avg, Q
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string
import json, openpyxl, sqlite3, tempfile, os, pytz, jdatetime
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from django.http import JsonResponse, HttpResponse

from .models import (
    Product, Category, Ticket, Notification,
    NotificationRead, UserActivity, SystemUpdate,
    UpdateConfirm, PharmacyUser,
)

# Tehran timezone constant — ثابت منطقه زمانی تهران
TEHRAN = pytz.timezone('Asia/Tehran')


# ══════════════════════════════════════════════════════════════════
# SECTION 1 — JALALI (SHAMSI) DATE UTILITIES
# بخش ۱ — توابع کمکی تاریخ شمسی
# ══════════════════════════════════════════════════════════════════

def jalali_weekday(dt_tehran):
    """Return Persian weekday name — نام روز هفته به فارسی"""
    wd = {0:'دوشنبه',1:'سه‌شنبه',2:'چهارشنبه',3:'پنج‌شنبه',4:'جمعه',5:'شنبه',6:'یکشنبه'}
    return wd[dt_tehran.weekday()]

def tehran_jalali_full(dt):
    """Full Jalali datetime with weekday — تاریخ شمسی کامل با روز هفته"""
    dt_t  = dt.astimezone(TEHRAN)
    jdt   = jdatetime.datetime.fromgregorian(datetime=dt_t)
    return f"{jdt.year}/{jdt.month:02d}/{jdt.day:02d} {jalali_weekday(dt_t)} ساعت {jdt.hour:02d}:{jdt.minute:02d}"

def tehran_jalali_display(dt):
    """Short Jalali datetime for display — تاریخ شمسی کوتاه برای نمایش"""
    dt_t = dt.astimezone(TEHRAN)
    jdt  = jdatetime.datetime.fromgregorian(datetime=dt_t)
    return f"{jdt.year}/{jdt.month:02d}/{jdt.day:02d}  {jdt.hour:02d}:{jdt.minute:02d}"

def tehran_jalali_filename(dt):
    """Jalali datetime formatted for filenames — تاریخ شمسی برای نام فایل"""
    dt_t = dt.astimezone(TEHRAN)
    jdt  = jdatetime.datetime.fromgregorian(datetime=dt_t)
    return f"{jdt.year}{jdt.month:02d}{jdt.day:02d}_{jdt.hour:02d}{jdt.minute:02d}"


# ══════════════════════════════════════════════════════════════════
# SECTION 2 — BASE CONTEXT HELPER
# بخش ۲ — تابع کمکی context پایه
# ══════════════════════════════════════════════════════════════════

def base_context(request):
    """
    Build shared context for all views (notifications, tickets, pharmacy name).
    ساخت context مشترک برای همه ویوها (اعلانات، تیکت‌ها، نام داروخانه).
    """
    ctx = {}
    if request.user.is_authenticated:
        ctx['unread_notif_count'] = Notification.objects.filter(
            is_active=True
        ).exclude(
            reads__user=request.user
        ).filter(
            Q(target_user=None) | Q(target_user=request.user)
        ).count()
        ctx['open_ticket_count'] = Ticket.objects.filter(
            user=request.user, status='open'
        ).count()
        ctx['pharmacy_name'] = request.user.pharmacy_name or request.user.username
    return ctx


# ══════════════════════════════════════════════════════════════════
# SECTION 3 — HOME, LOGIN, LOGOUT
# بخش ۳ — صفحه اصلی، ورود، خروج
# ══════════════════════════════════════════════════════════════════

def home(request):
    """Redirect authenticated users to dashboard, others to login.
    کاربران احراز هویت‌شده را به داشبورد، بقیه را به صفحه ورود هدایت می‌کند."""
    if request.user.is_authenticated:
        return redirect('staff_dashboard')
    return redirect('login_staff')


def login_staff(request):
    """Staff login page — صفحه ورود پرسنل"""
    if request.user.is_authenticated:
        return redirect('staff_dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            UserActivity.objects.create(
                user=user, action='ورود به سیستم', path='/staff/login/'
            )
            return redirect('staff_dashboard')
        messages.error(request, 'نام کاربری یا رمز عبور اشتباه است.')
    return render(request, 'pharmacy/login_staff.html')


@login_required
def logout_staff(request):
    """Staff logout — خروج پرسنل از سیستم"""
    UserActivity.objects.create(
        user=request.user, action='خروج از سیستم', path='/staff/logout/'
    )
    PharmacyUser.objects.filter(pk=request.user.pk).update(is_online=False)
    logout(request)
    return redirect('login_staff')


# ══════════════════════════════════════════════════════════════════
# SECTION 4 — MAIN DASHBOARD
# بخش ۴ — داشبورد اصلی
# ══════════════════════════════════════════════════════════════════

@login_required
def staff_dashboard(request):
    """
    Main dashboard: products, online staff, tickets, announcements, updates.
    داشبورد اصلی: محصولات، پرسنل آنلاین، تیکت‌ها، اعلانات، به‌روزرسانی‌ها.
    """
    now = timezone.now()

    total_products  = Product.objects.filter(is_deleted=False).count()
    active_products = Product.objects.filter(is_deleted=False, is_active=True).count()

    latest_products = Product.objects.filter(is_deleted=False).order_by('-created_at')[:10]
    latest_products_with_dates = [
        {
            'obj':        p,
            'created_fa': tehran_jalali_full(p.created_at),
            'updated_fa': tehran_jalali_full(p.updated_at),
        }
        for p in latest_products
    ]

    # Online staff: users active in last 120 seconds — پرسنل آنلاین: فعال در ۱۲۰ ثانیه اخیر
    cutoff        = now - timezone.timedelta(seconds=120)
    online_staff  = PharmacyUser.objects.filter(last_seen__gte=cutoff, is_active=True)
    online_count  = online_staff.count()

    pending_tickets  = Ticket.objects.filter(status='open').count()
    answered_tickets = Ticket.objects.filter(status='answered').count()
    recent_tickets   = Ticket.objects.select_related('user').order_by('-created_at')[:5]

    announcements = Notification.objects.filter(
        is_active=True
    ).filter(
        Q(target_user=None) | Q(target_user=request.user)
    ).order_by('-created_at')[:5]

    updates = SystemUpdate.objects.filter(is_active=True).order_by('-created_at')[:3]

    recent_activities = UserActivity.objects.filter(
        user=request.user
    ).order_by('-created_at')[:8]

    ctx = {
        **base_context(request),
        'total_products':     total_products,
        'active_products':    active_products,
        'online_count':       online_count,
        'online_staff':       online_staff[:5],
        'pending_tickets':    pending_tickets,
        'answered_tickets':   answered_tickets,
        'recent_tickets':     recent_tickets,
        'announcements':      announcements,
        'updates':            updates,
        'recent_activities':  recent_activities,
        'latest_products':    latest_products_with_dates,
        'now_fa':             tehran_jalali_full(now),
    }
    return render(request, 'pharmacy/dashboard.html', ctx)


@login_required
def online_ping(request):
    """Heartbeat endpoint to mark user as online — نقطه پایانی ضربان قلب برای آنلاین نشان دادن کاربر"""
    PharmacyUser.objects.filter(pk=request.user.pk).update(
        last_seen=timezone.now(), is_online=True
    )
    return JsonResponse({'status': 'ok'})


# ══════════════════════════════════════════════════════════════════
# SECTION 5 — PRODUCTS (LIST, ADD, EDIT, DELETE, TRASH, BULK)
# بخش ۵ — محصولات (لیست، افزودن، ویرایش، حذف، سطل آشغال، عملیات گروهی)
# ══════════════════════════════════════════════════════════════════

@login_required
def product_list(request):
    """
    Product listing with search, status filter, category filter, and AJAX support.
    لیست محصولات با جستجو، فیلتر وضعیت، فیلتر دسته‌بندی و پشتیبانی AJAX.
    """
    q           = request.GET.get('q', '')
    status      = request.GET.get('status', '')
    category_id = request.GET.get('category', '')

    qs = Product.objects.filter(is_deleted=False)
    if q:
        qs = qs.filter(Q(name__icontains=q)|Q(code__icontains=q)|Q(category__name__icontains=q))
    if status == 'active':
        qs = qs.filter(is_active=True)
    elif status == 'inactive':
        qs = qs.filter(is_active=False)
    if category_id:
        qs = qs.filter(category_id=category_id)

    qs         = qs.order_by('-created_at')
    total      = qs.count()
    active     = qs.filter(is_active=True).count()
    inactive   = qs.filter(is_active=False).count()
    avg_price  = qs.aggregate(avg=Avg('price'))['avg'] or 0
    categories = Category.objects.all()

    products_with_dates = []
    for p in qs:
        products_with_dates.append({
            'obj':        p,
            'created_fa': tehran_jalali_full(p.created_at),
            'updated_fa': tehran_jalali_full(p.updated_at),
        })

    ctx = {
        **base_context(request),
        'products':          products_with_dates,
        'categories':        categories,
        'search_query':      q,
        'selected_status':   status,
        'selected_category': category_id,
        'kpi': {
            'total':     total,
            'active':    active,
            'inactive':  inactive,
            'avg_price': int(avg_price),
        }
    }

    # AJAX partial render — رندر جزئی برای AJAX
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('pharmacy/partials/product_table.html', ctx, request=request)
        return JsonResponse({'table_html': html, 'kpi': ctx['kpi']})

    return render(request, 'pharmacy/product_list.html', ctx)


@login_required
def product_add(request):
    """Add a new product — افزودن محصول جدید"""
    categories = Category.objects.all()
    if request.method == 'POST':
        name             = request.POST.get('name', '').strip()
        code             = request.POST.get('code', '').strip()
        category_id      = request.POST.get('category') or None
        price            = request.POST.get('price', 0)
        discount_percent = request.POST.get('discount_percent', 0)
        description      = request.POST.get('description', '')
        is_active        = request.POST.get('is_active') == 'on'
        image            = request.FILES.get('image')

        if not name or not code or not price:
            messages.error(request, 'نام، کد و قیمت الزامی هستند.')
            return render(request, 'pharmacy/product_add.html', {'categories': categories, **base_context(request)})

        if Product.objects.filter(code=code, is_deleted=False).exists():
            messages.error(request, 'این کد محصول قبلاً ثبت شده است.')
            return render(request, 'pharmacy/product_add.html', {'categories': categories, **base_context(request)})

        p = Product.objects.create(
            name=name, code=code, category_id=category_id,
            price=price, discount_percent=discount_percent,
            description=description, is_active=is_active, image=image,
        )
        UserActivity.objects.create(
            user=request.user,
            action=f"افزودن محصول: {p.name} (کد: {p.code})",
            path=request.path,
        )
        messages.success(request, f'محصول «{p.name}» با موفقیت اضافه شد.')
        return redirect('product_list')

    return render(request, 'pharmacy/product_add.html', {'categories': categories, **base_context(request)})


@login_required
def product_edit(request, pk):
    """Edit an existing product — ویرایش محصول موجود"""
    product    = get_object_or_404(Product, pk=pk, is_deleted=False)
    categories = Category.objects.all()

    if request.method == 'POST':
        product.name             = request.POST.get('name', product.name).strip()
        product.code             = request.POST.get('code', product.code).strip()
        product.category_id      = request.POST.get('category') or None
        product.price            = request.POST.get('price', product.price)
        product.discount_percent = request.POST.get('discount_percent', product.discount_percent)
        product.description      = request.POST.get('description', '')
        product.is_active        = request.POST.get('is_active') == 'on'
        if request.FILES.get('image'):
            product.image = request.FILES['image']
        product.save()
        UserActivity.objects.create(
            user=request.user,
            action=f"ویرایش محصول: {product.name}",
            path=request.path,
        )
        messages.success(request, f'محصول «{product.name}» ویرایش شد.')
        return redirect('product_list')

    return render(request, 'pharmacy/product_edit.html',
                  {'product': product, 'categories': categories, **base_context(request)})


@login_required
@require_POST
def product_quick_edit(request, pk):
    """Quick inline edit for price and discount via AJAX — ویرایش سریع قیمت و تخفیف از طریق AJAX"""
    product      = get_object_or_404(Product, pk=pk, is_deleted=False)
    data         = json.loads(request.body)
    new_price    = data.get('price')
    new_discount = data.get('discount_percent')

    if new_price is not None:
        new_price = int(new_price)
        if new_price < 0:
            return JsonResponse({'error': 'قیمت نمی‌تواند منفی باشد.'}, status=400)
        product.price = new_price

    if new_discount is not None:
        new_discount = float(new_discount)
        if not (0 <= new_discount <= 100):
            return JsonResponse({'error': 'تخفیف باید بین ۰ تا ۱۰۰ درصد باشد.'}, status=400)
        product.discount_percent = new_discount

    product.save()
    UserActivity.objects.create(
        user=request.user,
        action=f"ویرایش سریع قیمت: {product.name} → {int(product.price)} تومان",
        path=request.path,
    )
    return JsonResponse({
        'success':          True,
        'price':            int(product.price),
        'discount_percent': float(product.discount_percent),
        'final_price':      product.final_price,
    })


@login_required
@require_POST
def product_delete(request, pk):
    """Soft-delete: move product to trash — حذف نرم: انتقال محصول به سطل آشغال"""
    product            = get_object_or_404(Product, pk=pk, is_deleted=False)
    name               = product.name
    product.is_deleted = True
    product.save()
    UserActivity.objects.create(
        user=request.user,
        action=f"حذف محصول: {name}",
        path=request.path,
    )
    return JsonResponse({'success': True, 'message': f'محصول «{name}» به سطل آشغال منتقل شد.'})


@login_required
def product_trash(request):
    """View soft-deleted products — مشاهده محصولات حذف‌شده (سطل آشغال)"""
    qs  = Product.objects.filter(is_deleted=True).order_by('-updated_at')
    ctx = {**base_context(request), 'products': qs}
    return render(request, 'pharmacy/product_trash.html', ctx)


@login_required
@require_POST
def product_restore(request, pk):
    """Restore a product from trash — بازگرداندن محصول از سطل آشغال"""
    product            = get_object_or_404(Product, pk=pk, is_deleted=True)
    product.is_deleted = False
    product.save()
    return JsonResponse({'success': True, 'message': f'محصول «{product.name}» بازگردانده شد.'})


@login_required
@require_POST
def product_destroy(request, pk):
    """Permanently delete a product — حذف دائمی محصول"""
    product = get_object_or_404(Product, pk=pk, is_deleted=True)
    name    = product.name
    product.delete()
    return JsonResponse({'success': True, 'message': f'محصول «{name}» برای همیشه حذف شد.'})


@login_required
@require_POST
def product_bulk_action(request):
    """
    Bulk actions: delete, activate, deactivate, change category, change price.
    عملیات گروهی: حذف، فعال‌سازی، غیرفعال‌سازی، تغییر دسته‌بندی، تغییر قیمت.
    """
    data   = json.loads(request.body)
    action = data.get('action')
    ids    = data.get('ids', [])

    if not ids:
        return JsonResponse({'error': 'هیچ محصولی انتخاب نشده.'}, status=400)

    products = Product.objects.filter(pk__in=ids, is_deleted=False)

    if action == 'delete':
        products.update(is_deleted=True)
        return JsonResponse({'success': True, 'message': f'{len(ids)} محصول به سطل آشغال منتقل شد.'})
    elif action == 'activate':
        products.update(is_active=True)
        return JsonResponse({'success': True, 'message': f'{len(ids)} محصول فعال شد.'})
    elif action == 'deactivate':
        products.update(is_active=False)
        return JsonResponse({'success': True, 'message': f'{len(ids)} محصول غیرفعال شد.'})
    elif action == 'change_category':
        cid = data.get('category_id')
        if not cid:
            return JsonResponse({'error': 'دسته‌بندی انتخاب نشده.'}, status=400)
        products.update(category_id=cid)
        return JsonResponse({'success': True, 'message': f'دسته‌بندی {len(ids)} محصول تغییر کرد.'})
    elif action == 'change_price':
        value     = data.get('value')
        mode      = data.get('mode', 'fixed')
        direction = data.get('direction', 'set')
        discount  = data.get('discount', None)
        if value is None:
            return JsonResponse({'error': 'مقدار وارد نشده.'}, status=400)
        value = float(value)
        for p in products:
            if mode == 'percent':
                if direction == 'increase':
                    p.price = int(p.price * (1 + value / 100))
                elif direction == 'decrease':
                    p.price = max(0, int(p.price * (1 - value / 100)))
                else:
                    p.price = int(p.price * value / 100)
            else:
                if direction == 'increase':
                    p.price = int(p.price) + int(value)
                elif direction == 'decrease':
                    p.price = max(0, int(p.price) - int(value))
                else:
                    p.price = int(value)
            if discount is not None and discount != '':
                p.discount_percent = float(discount)
            p.save()
        return JsonResponse({'success': True, 'message': f'قیمت {len(ids)} محصول تغییر کرد.'})

    return JsonResponse({'error': 'عملیات نامعتبر.'}, status=400)


# ══════════════════════════════════════════════════════════════════
# SECTION 6 — CATEGORIES
# بخش ۶ — دسته‌بندی‌ها
# ══════════════════════════════════════════════════════════════════

@login_required
def category_list(request):
    """List all categories — لیست همه دسته‌بندی‌ها"""
    cats = Category.objects.all().order_by('name')
    ctx  = {**base_context(request), 'categories': cats}
    return render(request, 'pharmacy/category_list.html', ctx)


@login_required
def category_add(request):
    """Add a new category — افزودن دسته‌بندی جدید"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'نام دسته‌بندی الزامی است.')
        elif Category.objects.filter(name=name).exists():
            messages.error(request, 'این دسته‌بندی قبلاً ثبت شده.')
        else:
            cat = Category.objects.create(name=name)
            messages.success(request, f'دسته‌بندی «{cat.name}» ساخته شد.')
            return redirect('category_list')
    return render(request, 'pharmacy/category_form.html', {'action': 'add', **base_context(request)})


@login_required
def category_edit(request, pk):
    """Edit an existing category — ویرایش دسته‌بندی موجود"""
    cat = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'نام دسته‌بندی الزامی است.')
        else:
            cat.name = name
            cat.save()
            messages.success(request, f'دسته‌بندی «{cat.name}» ویرایش شد.')
            return redirect('category_list')
    return render(request, 'pharmacy/category_form.html', {'action': 'edit', 'category': cat, **base_context(request)})


@login_required
@require_POST
def category_delete(request, pk):
    """Delete a category (only if no active products) — حذف دسته‌بندی (فقط اگر محصول فعال نداشته باشد)"""
    cat = get_object_or_404(Category, pk=pk)
    if cat.products.filter(is_deleted=False).exists():
        return JsonResponse({'error': 'این دسته‌بندی محصول فعال دارد. ابتدا محصولات را منتقل کنید.'}, status=400)
    name = cat.name
    cat.delete()
    return JsonResponse({'success': True, 'message': f'دسته‌بندی «{name}» حذف شد.'})


# ══════════════════════════════════════════════════════════════════
# SECTION 7 — SUPPORT TICKETS
# بخش ۷ — تیکت‌های پشتیبانی
# ══════════════════════════════════════════════════════════════════

@login_required
def ticket_list(request):
    """List user's support tickets — لیست تیکت‌های پشتیبانی کاربر"""
    tickets = Ticket.objects.filter(user=request.user).order_by('-created_at')
    tickets_with_dates = [
        {'obj': t, 'created_fa': tehran_jalali_full(t.created_at)}
        for t in tickets
    ]
    ctx = {
        **base_context(request),
        'tickets': tickets_with_dates,
        'open_count':     tickets.filter(status='open').count(),
        'answered_count': tickets.filter(status='answered').count(),
        'closed_count':   tickets.filter(status='closed').count(),
    }
    return render(request, 'pharmacy/ticket_list.html', ctx)


@login_required
def ticket_create(request):
    """Create a new support ticket — ایجاد تیکت پشتیبانی جدید"""
    if request.method == 'POST':
        title    = request.POST.get('title', '').strip()
        message  = request.POST.get('message', '').strip()
        priority = request.POST.get('priority', 'medium')
        if not title or not message:
            messages.error(request, 'عنوان و متن پیام الزامی هستند.')
        else:
            t = Ticket.objects.create(
                user=request.user, title=title,
                message=message, priority=priority
            )
            UserActivity.objects.create(
                user=request.user,
                action=f"ثبت تیکت: {t.title}",
                path=request.path,
            )
            messages.success(request, 'تیکت شما با موفقیت ثبت شد.')
            return redirect('ticket_list')
    return render(request, 'pharmacy/ticket_create.html', {**base_context(request)})


@login_required
def ticket_detail(request, pk):
    """View ticket details and mark as read — مشاهده جزئیات تیکت و علامت‌گذاری به‌عنوان خوانده‌شده"""
    ticket = get_object_or_404(Ticket, pk=pk, user=request.user)
    ticket.is_read = True
    ticket.save(update_fields=['is_read'])
    ctx = {
        **base_context(request),
        'ticket':     ticket,
        'created_fa': tehran_jalali_full(ticket.created_at),
        'replied_fa': tehran_jalali_full(ticket.replied_at) if ticket.replied_at else None,
    }
    return render(request, 'pharmacy/ticket_detail.html', ctx)


@login_required
@require_POST
def ticket_close(request, pk):
    """Close a ticket — بستن تیکت"""
    ticket = get_object_or_404(Ticket, pk=pk, user=request.user)
    ticket.status = 'closed'
    ticket.save(update_fields=['status'])
    return JsonResponse({'success': True})


# ══════════════════════════════════════════════════════════════════
# SECTION 8 — NOTIFICATIONS
# بخش ۸ — اعلانات
# ══════════════════════════════════════════════════════════════════

@login_required
def notification_list(request):
    """List active notifications for the current user — لیست اعلانات فعال برای کاربر جاری"""
    notifs = Notification.objects.filter(
        is_active=True
    ).filter(
        Q(target_user=None) | Q(target_user=request.user)
    ).order_by('-created_at')

    read_ids = set(
        NotificationRead.objects.filter(user=request.user).values_list('notification_id', flat=True)
    )

    notifs_data = [
        {
            'obj':        n,
            'is_read':    n.pk in read_ids,
            'created_fa': tehran_jalali_full(n.created_at),
        }
        for n in notifs
    ]

    ctx = {**base_context(request), 'notifications': notifs_data}
    return render(request, 'pharmacy/notification_list.html', ctx)


@login_required
@require_POST
def notification_read(request, pk):
    """Mark a notification as read — علامت‌گذاری اعلان به‌عنوان خوانده‌شده"""
    notif = get_object_or_404(Notification, pk=pk, is_active=True)
    NotificationRead.objects.get_or_create(user=request.user, notification=notif)
    return JsonResponse({'success': True})


# ══════════════════════════════════════════════════════════════════
# SECTION 9 — SYSTEM UPDATES
# بخش ۹ — به‌روزرسانی‌های سیستم
# ══════════════════════════════════════════════════════════════════

@login_required
def updates_list(request):
    """List system updates and confirmation status — لیست به‌روزرسانی‌های سیستم و وضعیت تأیید"""
    updates = SystemUpdate.objects.filter(is_active=True).order_by('-created_at')
    confirmed_ids = set(
        UpdateConfirm.objects.filter(user=request.user, confirmed=True).values_list('update_id', flat=True)
    )
    updates_data = [
        {
            'obj':        u,
            'confirmed':  u.pk in confirmed_ids,
            'created_fa': tehran_jalali_full(u.created_at),
        }
        for u in updates
    ]
    ctx = {**base_context(request), 'updates': updates_data}
    return render(request, 'pharmacy/updates_list.html', ctx)


@login_required
@require_POST
def update_confirm(request, pk):
    """Confirm receipt of a system update — تأیید دریافت به‌روزرسانی سیستم"""
    update = get_object_or_404(SystemUpdate, pk=pk, is_active=True)
    obj, created = UpdateConfirm.objects.get_or_create(user=request.user, update=update)
    obj.confirmed    = True
    obj.confirmed_at = timezone.now()
    obj.save()
    return JsonResponse({'success': True})


# ══════════════════════════════════════════════════════════════════
# SECTION 10 — PROFILE, AVATAR, PASSWORD
# بخش ۱۰ — پروفایل، آواتار، تغییر رمز عبور
# ══════════════════════════════════════════════════════════════════

@login_required
def profile_view(request):
    """View and update user profile — مشاهده و ویرایش پروفایل کاربر"""
    if request.method == 'POST':
        user = request.user
        user.first_name    = request.POST.get('first_name', user.first_name)
        user.last_name     = request.POST.get('last_name',  user.last_name)
        user.email         = request.POST.get('email',      user.email)
        user.phone         = request.POST.get('phone',      user.phone)
        user.address       = request.POST.get('address',    user.address)
        user.postal_code   = request.POST.get('postal_code',user.postal_code)
        user.pharmacy_name = request.POST.get('pharmacy_name', user.pharmacy_name)
        if request.FILES.get('profile_image'):
            user.profile_image = request.FILES['profile_image']
            user.avatar_type   = 'custom'
        user.save()
        messages.success(request, 'اطلاعات با موفقیت ذخیره شد.')
        return redirect('profile_view')
    return render(request, 'pharmacy/profile.html', {**base_context(request), 'user': request.user})


@login_required
def avatar_select(request):
    """Select a predefined avatar — انتخاب آواتار از پیش‌تعریف‌شده"""
    AVATARS = [
        ('doctor',     'دکتر',      '👨‍⚕️'),
        ('pharmacist', 'داروساز',   '💊'),
        ('chemist',    'شیمی‌دان',  '🔬'),
        ('accountant', 'حسابدار',   '📊'),
        ('staff',      'پرسنل',     '👤'),
    ]
    if request.method == 'POST':
        avatar = request.POST.get('avatar_type', 'staff')
        PharmacyUser.objects.filter(pk=request.user.pk).update(avatar_type=avatar)
        messages.success(request, 'آواتار شما تغییر کرد.')
        return redirect('profile_view')
    return render(request, 'pharmacy/avatar_select.html',
                  {**base_context(request), 'avatars': AVATARS, 'current': request.user.avatar_type})


@login_required
def change_password(request):
    """Change user password — تغییر رمز عبور کاربر"""
    if request.method == 'POST':
        old_pw  = request.POST.get('old_password', '')
        new_pw  = request.POST.get('new_password', '')
        new_pw2 = request.POST.get('new_password2', '')
        if not request.user.check_password(old_pw):
            messages.error(request, 'رمز فعلی اشتباه است.')
        elif new_pw != new_pw2:
            messages.error(request, 'رمز جدید و تکرار آن یکسان نیستند.')
        elif len(new_pw) < 8:
            messages.error(request, 'رمز جدید باید حداقل ۸ کاراکتر باشد.')
        else:
            request.user.set_password(new_pw)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'رمز عبور با موفقیت تغییر کرد.')
            return redirect('profile_view')
    return render(request, 'pharmacy/change_password.html', {**base_context(request)})


# ══════════════════════════════════════════════════════════════════
# SECTION 11 — SETTINGS
# بخش ۱۱ — تنظیمات
# ══════════════════════════════════════════════════════════════════

@login_required
def settings_financial(request):
    """Financial settings page — صفحه تنظیمات مالی"""
    return render(request, 'pharmacy/settings_financial.html', {**base_context(request)})

@login_required
def settings_accounting(request):
    """Accounting settings page — صفحه تنظیمات حسابداری"""
    return render(request, 'pharmacy/settings_accounting.html', {**base_context(request)})

@login_required
def settings_products(request):
    """Product settings page — صفحه تنظیمات محصولات"""
    return render(request, 'pharmacy/settings_products.html', {**base_context(request)})


# ══════════════════════════════════════════════════════════════════
# SECTION 12 — HELP & SUPPORT PAGES
# بخش ۱۲ — صفحات راهنما و پشتیبانی
# ══════════════════════════════════════════════════════════════════

@login_required
def help_rules(request):
    """Rules and regulations page — صفحه قوانین و مقررات"""
    return render(request, 'pharmacy/help_rules.html', {**base_context(request)})

@login_required
def help_guide(request):
    """User guide page — صفحه راهنمای استفاده"""
    return render(request, 'pharmacy/help_guide.html', {**base_context(request)})

@login_required
def help_articles(request):
    """Help articles page — صفحه مقالات راهنما"""
    return render(request, 'pharmacy/help_articles.html', {**base_context(request)})

@login_required
def support_contact(request):
    """Contact support page — صفحه تماس با پشتیبانی"""
    return render(request, 'pharmacy/support_contact.html', {**base_context(request)})

@login_required
def support_accounting(request):
    """Accounting support page — صفحه پشتیبانی حسابداری"""
    return render(request, 'pharmacy/support_accounting.html', {**base_context(request)})


# ══════════════════════════════════════════════════════════════════
# SECTION 13 — CALCULATOR
# بخش ۱۳ — ماشین حساب
# ══════════════════════════════════════════════════════════════════

@login_required
def calculator_view(request):
    """Pharmacy calculator tool — ابزار ماشین حساب داروخانه"""
    return render(request, 'pharmacy/calculator.html', {**base_context(request)})


# ══════════════════════════════════════════════════════════════════
# SECTION 14 — EXCEL EXPORT (PRODUCTS)
# بخش ۱۴ — خروجی Excel محصولات
# ══════════════════════════════════════════════════════════════════

@login_required
def export_excel(request):
    """
    Export all active products to a styled Excel file.
    خروجی Excel از همه محصولات فعال با قالب‌بندی حرفه‌ای.
    """
    products   = list(Product.objects.filter(is_deleted=False).select_related('category').order_by('-created_at'))
    now        = timezone.now()
    jalali_str = tehran_jalali_full(now)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'محصولات داروخانه'
    ws.sheet_view.rightToLeft    = True
    ws.sheet_properties.tabColor = '0D9488'

    # Color palette — پالت رنگی
    TEAL_DARK  = '0D9488'
    TEAL_MID   = '14B8A6'
    TEAL_LIGHT = 'CCFBF1'
    TEAL_STRIPE= '99F6E4'
    WHITE      = 'FFFFFF'
    OFF_WHITE  = 'F0FDFA'
    GREEN_BG   = 'DCFCE7'; GREEN_FG = '166534'
    YELLOW_BG  = 'FEFCE8'; YELLOW_FG= '854D0E'
    RED_BG     = 'FEF2F2'; RED_FG   = 'DC2626'
    PRICE_BG   = 'FEFCE8'; PRICE_FG = '92400E'
    DISC_BG    = 'FFF7ED'; DISC_FG  = 'C2410C'
    FINAL_BG   = 'F0FDF4'; FINAL_FG = '166534'
    DATE_BG    = 'F8FAFC'; DATE_FG  = '64748B'
    CODE_FG    = '0D9488'
    NUM_BG     = 'F0FDFA'; NUM_FG   = '94A3B8'
    SUM_BG     = '0F766E'

    # Style helper functions — توابع کمکی استایل
    def mkfill(h): return PatternFill('solid', fgColor=h)
    def mkfont(bold=False, size=10, color='1E293B', italic=False):
        return Font(bold=bold, size=size, color=color, italic=italic, name='Calibri')
    def mkalign(h='center', wrap=False):
        return Alignment(horizontal=h, vertical='center', wrap_text=wrap, readingOrder=2)

    thin     = Side(style='thin',   color='A7F3D0')
    med_teal = Side(style='medium', color=TEAL_DARK)
    brd_thin = Border(left=thin,     right=thin,     top=thin,     bottom=thin)
    brd_hdr  = Border(left=med_teal, right=med_teal, top=med_teal, bottom=med_teal)

    # Row 1: Title header — ردیف ۱: عنوان اصلی
    ws.merge_cells('A1:K1')
    c = ws['A1']
    c.value     = '🏥   سیستم مدیریت داروخانه — سازمان دارو شیراز   |   گزارش کامل محصولات'
    c.font      = Font(bold=True, size=20, color=WHITE, name='Calibri')
    c.fill      = mkfill(TEAL_DARK)
    c.alignment = mkalign('center')
    ws.row_dimensions[1].height = 54

    # Row 2: Date and count info — ردیف ۲: تاریخ و تعداد
    ws.merge_cells('A2:K2')
    c = ws['A2']
    c.value     = f'  تاریخ تهیه:   {jalali_str}   (به وقت تهران)          |          تعداد کل محصولات:   {len(products)}   عدد  '
    c.font      = mkfont(size=11, color='134E4A', italic=True)
    c.fill      = mkfill(TEAL_LIGHT)
    c.alignment = mkalign('center')
    ws.row_dimensions[2].height = 28

    # Row 3: Decorative stripe — ردیف ۳: نوار تزئینی
    ws.merge_cells('A3:K3')
    ws['A3'].fill = mkfill(TEAL_STRIPE)
    ws.row_dimensions[3].height = 6

    # Row 4: Column headers — ردیف ۴: سرستون‌ها
    col_defs = [
        ('#', 5), ('کد محصول', 18), ('نام محصول', 44), ('دسته‌بندی', 22),
        ('قیمت (تومان)', 22), ('تخفیف %', 13), ('مبلغ تخفیف (تومان)', 22),
        ('قیمت نهایی (تومان)', 22), ('وضعیت', 14),
        ('تاریخ بارگذاری', 26), ('آخرین ویرایش', 26),
    ]
    for ci, (hdr, w) in enumerate(col_defs, 1):
        c = ws.cell(row=4, column=ci, value=hdr)
        c.font      = Font(bold=True, size=11, color=WHITE, name='Calibri')
        c.fill      = mkfill(TEAL_MID)
        c.alignment = mkalign('center', wrap=True)
        c.border    = brd_hdr
        ws.column_dimensions[get_column_letter(ci)].width = w
    ws.row_dimensions[4].height = 36

    # Data rows — ردیف‌های داده
    for idx, p in enumerate(products, 1):
        r      = idx + 4
        row_bg = TEAL_LIGHT if idx % 2 == 0 else OFF_WHITE
        vals   = [
            idx, p.code, p.name,
            p.category.name if p.category else '—',
            int(p.price), float(p.discount_percent),
            int(p.discount_amount), int(p.final_price),
            'فعال' if p.is_active else 'غیرفعال',
            tehran_jalali_display(p.created_at),
            tehran_jalali_display(p.updated_at),
        ]
        for ci, val in enumerate(vals, 1):
            c = ws.cell(row=r, column=ci, value=val)
            c.border = brd_thin
            if ci == 1:
                c.font = mkfont(size=9, color=NUM_FG); c.fill = mkfill(NUM_BG); c.alignment = mkalign()
            elif ci == 2:
                c.font = Font(bold=True, size=10, color=CODE_FG, name='Courier New'); c.fill = mkfill(row_bg); c.alignment = mkalign()
            elif ci == 3:
                c.font = mkfont(bold=True, size=10, color='134E4A'); c.fill = mkfill(row_bg); c.alignment = mkalign('right')
            elif ci == 4:
                c.font = mkfont(size=10, color='475569'); c.fill = mkfill(row_bg); c.alignment = mkalign()
            elif ci == 5:
                c.font = mkfont(bold=True, size=10, color=PRICE_FG); c.fill = mkfill(PRICE_BG); c.alignment = mkalign(); c.number_format = '#,##0'
            elif ci == 6:
                c.value = f'{val:.1f}%'; c.font = mkfont(bold=True, size=10, color=YELLOW_FG); c.fill = mkfill(YELLOW_BG); c.alignment = mkalign()
            elif ci == 7:
                c.font = mkfont(size=10, color=DISC_FG); c.fill = mkfill(DISC_BG); c.alignment = mkalign(); c.number_format = '#,##0'
            elif ci == 8:
                c.font = Font(bold=True, size=11, color=FINAL_FG, name='Calibri'); c.fill = mkfill(FINAL_BG); c.alignment = mkalign(); c.number_format = '#,##0'
            elif ci == 9:
                if p.is_active:
                    c.value = '✔  فعال'; c.font = Font(bold=True, size=10, color=GREEN_FG, name='Calibri'); c.fill = mkfill(GREEN_BG)
                else:
                    c.value = '✘  غیرفعال'; c.font = Font(bold=True, size=10, color=RED_FG, name='Calibri'); c.fill = mkfill(RED_BG)
                c.alignment = mkalign()
            elif ci in (10, 11):
                c.font = mkfont(size=9, color=DATE_FG, italic=True); c.fill = mkfill(DATE_BG); c.alignment = mkalign()
            else:
                c.font = mkfont(size=10); c.fill = mkfill(row_bg); c.alignment = mkalign()
        ws.row_dimensions[r].height = 26

    # Separator stripe — نوار جداکننده
    sep = len(products) + 5
    ws.merge_cells(f'A{sep}:K{sep}')
    ws[f'A{sep}'].fill = mkfill(TEAL_STRIPE)
    ws.row_dimensions[sep].height = 5

    # Summary row — ردیف خلاصه
    sum_row   = sep + 1
    total_fin = sum(int(p.final_price) for p in products)
    avg_p     = int(sum(int(p.price) for p in products) / len(products)) if products else 0
    act_cnt   = sum(1 for p in products if p.is_active)
    for col_l, txt, bg in [
        ('A', f'مجموع: {len(products)} محصول', SUM_BG),
        ('C', f'✔ فعال: {act_cnt}',            GREEN_FG),
        ('E', f'✘ غیرفعال: {len(products)-act_cnt}', RED_FG),
        ('G', f'میانگین قیمت: {avg_p:,} ت',   YELLOW_FG),
        ('I', f'جمع نهایی: {total_fin:,} ت',   SUM_BG),
    ]:
        c = ws[f'{col_l}{sum_row}']
        c.value = txt; c.font = Font(bold=True, size=10, color=WHITE, name='Calibri')
        c.fill  = mkfill(bg); c.alignment = mkalign()
    ws.row_dimensions[sum_row].height = 32

    # Footer — پاورقی
    foot = sum_row + 1
    ws.merge_cells(f'A{foot}:K{foot}')
    c = ws[f'A{foot}']
    c.value     = f'این گزارش در تاریخ  {jalali_str}  توسط سیستم مدیریت داروخانه — سازمان دارو شیراز تهیه شده است.'
    c.font      = mkfont(size=9, color='94A3B8', italic=True)
    c.fill      = mkfill('F0FDFA')
    c.alignment = mkalign()
    ws.row_dimensions[foot].height = 22

    ws.freeze_panes = 'A5'

    filename = f'products_{tehran_jalali_filename(now)}.xlsx'
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


# ══════════════════════════════════════════════════════════════════
# SECTION 15 — ACCESS / SQLITE EXPORT (PRODUCTS)
# بخش ۱۵ — خروجی Access/SQLite محصولات
# ══════════════════════════════════════════════════════════════════

@login_required
def export_access(request):
    """
    Export products to a SQLite database file (disguised as .accdb).
    خروجی محصولات به فایل پایگاه داده SQLite (با پسوند .accdb).
    """
    now           = timezone.now()
    jalali_full   = tehran_jalali_full(now)
    file_stamp    = tehran_jalali_filename(now)
    products_qs   = Product.objects.filter(is_deleted=False).select_related('category').order_by('-created_at')
    categories_qs = Category.objects.all()

    tmp = tempfile.NamedTemporaryFile(suffix='.accdb', delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.execute("PRAGMA encoding='UTF-8'")
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()

    # Report metadata table — جدول اطلاعات گزارش
    cur.execute('CREATE TABLE report_info (key TEXT PRIMARY KEY, value TEXT)')
    cur.executemany('INSERT OR REPLACE INTO report_info VALUES (?,?)', [
        ('export_date',       jalali_full),
        ('total_products',    str(products_qs.count())),
        ('active_products',   str(products_qs.filter(is_active=True).count())),
        ('inactive_products', str(products_qs.filter(is_active=False).count())),
        ('exported_by',       request.user.get_full_name() or request.user.username),
        ('system',            'سیستم مدیریت داروخانه — سازمان دارو شیراز'),
    ])

    # Categories table — جدول دسته‌بندی‌ها
    cur.execute('CREATE TABLE categories (id INTEGER PRIMARY KEY, name TEXT NOT NULL, product_cnt INTEGER DEFAULT 0)')
    for cat in categories_qs:
        cnt = Product.objects.filter(category=cat, is_deleted=False).count()
        cur.execute('INSERT INTO categories VALUES (?,?,?)', (cat.id, cat.name, cnt))

    # Products table — جدول محصولات
    cur.execute('''CREATE TABLE products (
        id INTEGER PRIMARY KEY, code TEXT NOT NULL, name TEXT NOT NULL,
        category_id INTEGER, category_name TEXT DEFAULT '',
        price INTEGER NOT NULL DEFAULT 0,
        discount_percent REAL NOT NULL DEFAULT 0,
        discount_amount INTEGER NOT NULL DEFAULT 0,
        final_price INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'فعال',
        description TEXT DEFAULT '',
        created_at TEXT, updated_at TEXT, export_date TEXT,
        FOREIGN KEY (category_id) REFERENCES categories(id)
    )''')
    for p in products_qs:
        cur.execute('INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (
            p.pk, p.code, p.name,
            p.category_id,
            p.category.name if p.category else '',
            int(p.price), float(p.discount_percent),
            int(p.discount_amount), int(p.final_price),
            'فعال' if p.is_active else 'غیرفعال',
            p.description or '',
            tehran_jalali_display(p.created_at),
            tehran_jalali_display(p.updated_at),
            jalali_full,
        ))

    # Indexes for performance — ایندکس‌ها برای بهبود کارایی
    for iname, ifield in [('idx_code','code'),('idx_cat','category_id'),('idx_status','status'),('idx_price','price')]:
        cur.execute(f'CREATE INDEX {iname} ON products({ifield})')

    # Convenience views — ویوهای کمکی
    for vname, vsql in [
        ('v_active',    "SELECT * FROM products WHERE status='فعال' ORDER BY name"),
        ('v_inactive',  "SELECT * FROM products WHERE status='غیرفعال' ORDER BY name"),
        ('v_discounted',"SELECT * FROM products WHERE discount_percent>0 ORDER BY discount_percent DESC"),
        ('v_summary',   "SELECT COUNT(*) total, SUM(CASE WHEN status='فعال' THEN 1 ELSE 0 END) active_cnt, ROUND(AVG(CAST(price AS REAL)),0) avg_price, SUM(final_price) total_final FROM products"),
        ('v_top20',     "SELECT id,code,name,category_name,price,final_price,status FROM products ORDER BY price DESC LIMIT 20"),
    ]:
        cur.execute(f'CREATE VIEW {vname} AS {vsql}')

    conn.commit()
    conn.close()

    with open(tmp.name, 'rb') as f:
        data = f.read()
    os.unlink(tmp.name)

    filename = f'pharmacy_products_{file_stamp}.accdb'
    response = HttpResponse(data, content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ══════════════════════════════════════════════════════════════════
# SECTION 16 — SAVE TO SITE / ACCOUNTING INTEGRATION
# بخش ۱۶ — ذخیره در سایت / ارتباط با سیستم حسابداری
# ══════════════════════════════════════════════════════════════════

@login_required
@require_POST
def save_to_site(request):
    """Save/sync products to the public website — ذخیره/همگام‌سازی محصولات با سایت عمومی"""
    try:
        count = Product.objects.filter(is_deleted=False).count()
        return JsonResponse({'success': True, 'message': f'{count} محصول با موفقیت در سایت ذخیره شد.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def save_to_accounting(request):
    """Push products to external accounting system API — ارسال محصولات به API سیستم حسابداری خارجی"""
    api_url = getattr(settings, 'ACCOUNTING_API_URL', None)
    if not api_url:
        return JsonResponse({'success': False, 'error': 'آدرس API حسابداری تعریف نشده است.'}, status=400)

    products = Product.objects.filter(is_deleted=False).select_related('category')
    payload  = {'products': [
        {
            'code':             p.code,
            'name':             p.name,
            'category':         p.category.name if p.category else '',
            'price':            int(p.price),
            'discount_percent': float(p.discount_percent),
            'discount_amount':  int(p.discount_amount),
            'final_price':      int(p.final_price),
            'is_active':        p.is_active,
        }
        for p in products
    ]}

    headers = {'Content-Type': 'application/json'}
    if getattr(settings, 'ACCOUNTING_API_KEY', ''):
        headers['X-API-Key'] = settings.ACCOUNTING_API_KEY
    if getattr(settings, 'ACCOUNTING_API_TOKEN', ''):
        headers['Authorization'] = f"Bearer {settings.ACCOUNTING_API_TOKEN}"

    try:
        import requests as http_req
        resp = http_req.post(f"{api_url}/products/sync", json=payload, headers=headers, timeout=30)
        if resp.status_code in (200, 201):
            Product.objects.filter(is_deleted=False).update(accounting_status='synced')
            return JsonResponse({'success': True, 'message': f"{len(payload['products'])} محصول در سیستم حسابداری ذخیره شد."})
        return JsonResponse({'success': False, 'error': f'خطا از سرور: کد {resp.status_code}'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=503)


# ══════════════════════════════════════════════════════════════════
# SECTION 17 — DRUG BANK (LIST, DETAIL, ADD TO PRODUCTS)
# بخش ۱۷ — بانک دارو (لیست، جزئیات، افزودن به محصولات)
#
# ── ROOT CAUSE OF ????? BUG ────────────────────────────────────
# The seed scripts stored otc_rx as 'OTC'/'RX' (uppercase),
# but the Drug model OTCPX_CHOICES uses 'otc'/'rx' (lowercase).
# Also drug_form was stored as Persian text like 'قرص/اسپری'
# but model FORM_CHOICES uses English keys like 'tablet','spray'.
# This view fixes both by normalizing values on read.
#
# ── ریشه باگ ????? ─────────────────────────────────────────────
# اسکریپت‌های seed مقدار otc_rx را به صورت 'OTC'/'RX' (حروف بزرگ)
# ذخیره کردند، اما model از 'otc'/'rx' (حروف کوچک) استفاده می‌کند.
# همچنین drug_form به صورت فارسی مثل 'قرص/اسپری' ذخیره شده
# ولی FORM_CHOICES کلیدهای انگلیسی مثل 'tablet','spray' دارد.
# این view با normalize کردن مقادیر هنگام خواندن مشکل را حل می‌کند.
# ══════════════════════════════════════════════════════════════════


# ── Helper: normalize otc_rx to lowercase ──────────────────────
# تابع کمکی: تبدیل otc_rx به حروف کوچک
# Seed stored 'OTC'/'RX' but model choices are 'otc'/'rx'.
# اسکریپت seed مقدار 'OTC'/'RX' ذخیره کرد ولی model از 'otc'/'rx' استفاده می‌کند.
def _normalize_otc(val):
    """
    Normalize otc_rx field value to lowercase for consistent comparison.
    مقدار فیلد otc_rx را به حروف کوچک تبدیل می‌کند تا مقایسه یکنواخت باشد.
    Returns 'otc', 'rx', or 'na'.
    """
    if not val:
        return 'na'
    return val.lower().strip()


# ── Helper: build drug form icon and CSS class ─────────────────
# تابع کمکی: ساخت آیکون و کلاس CSS برای فرم دارو
# Maps both English model keys AND Persian seed values to emoji icons.
# هر دو کلید انگلیسی model و مقادیر فارسی seed را به آیکون emoji ترجمه می‌کند.
DRUG_FORM_ICON_MAP = {
    # English model keys — کلیدهای انگلیسی model
    'tablet':      ('💊', 'rgba(91,140,255,.15)'),
    'capsule':     ('💊', 'rgba(91,140,255,.15)'),
    'syrup':       ('🍶', 'rgba(56,189,248,.15)'),
    'drop':        ('💧', 'rgba(6,182,212,.15)'),
    'injection':   ('💉', 'rgba(255,93,108,.15)'),
    'serum':       ('💉', 'rgba(255,93,108,.15)'),
    'ointment':    ('🧴', 'rgba(16,185,129,.15)'),
    'cream':       ('🧴', 'rgba(16,185,129,.15)'),
    'gel':         ('🧪', 'rgba(16,185,129,.15)'),
    'spray':       ('💨', 'rgba(124,92,255,.15)'),
    'inhaler':     ('😮‍💨', 'rgba(124,92,255,.15)'),
    'patch':       ('🩹', 'rgba(236,72,153,.15)'),
    'suppository': ('🔹', 'rgba(245,158,11,.15)'),
    'powder':      ('🫧', 'rgba(255,255,255,.08)'),
    'solution':    ('💧', 'rgba(56,189,248,.15)'),
    'lotion':      ('🧴', 'rgba(16,185,129,.15)'),
    'shampoo':     ('🧴', 'rgba(16,185,129,.15)'),
    'soap':        ('🧼', 'rgba(255,255,255,.08)'),
    'device':      ('🩺', 'rgba(255,255,255,.08)'),
    'bandage':     ('🩹', 'rgba(236,72,153,.15)'),
    'other':       ('💊', 'rgba(255,255,255,.08)'),
    # Persian seed values — مقادیر فارسی seed
    'قرص':         ('💊', 'rgba(91,140,255,.15)'),
    'کپسول':       ('💊', 'rgba(91,140,255,.15)'),
    'شربت':        ('🍶', 'rgba(56,189,248,.15)'),
    'قطره':        ('💧', 'rgba(6,182,212,.15)'),
    'آمپول':       ('💉', 'rgba(255,93,108,.15)'),
    'سرم':         ('💉', 'rgba(255,93,108,.15)'),
    'پماد':        ('🧴', 'rgba(16,185,129,.15)'),
    'کرم':         ('🧴', 'rgba(16,185,129,.15)'),
    'ژل':          ('🧪', 'rgba(16,185,129,.15)'),
    'اسپری':       ('💨', 'rgba(124,92,255,.15)'),
    'اینهالر':     ('😮‍💨', 'rgba(124,92,255,.15)'),
    'پچ':          ('🩹', 'rgba(236,72,153,.15)'),
    'شیاف':        ('🔹', 'rgba(245,158,11,.15)'),
    'پودر':        ('🫧', 'rgba(255,255,255,.08)'),
    'محلول':       ('💧', 'rgba(56,189,248,.15)'),
    'لوسیون':      ('🧴', 'rgba(16,185,129,.15)'),
    'شامپو':       ('🧴', 'rgba(16,185,129,.15)'),
    'صابون':       ('🧼', 'rgba(255,255,255,.08)'),
    'دستگاه':      ('🩺', 'rgba(255,255,255,.08)'),
    'باند':        ('🩹', 'rgba(236,72,153,.15)'),
}


def _get_drug_icon(drug_form_value):
    """
    Return (emoji, background_css) for a drug form value.
    Handles both English model keys and Persian seed values.
    Returns emoji and CSS background color for drug form display.

    آیکون و رنگ پس‌زمینه CSS را برای فرم دارو برمی‌گرداند.
    هم کلیدهای انگلیسی model و هم مقادیر فارسی seed را پردازش می‌کند.
    """
    if not drug_form_value:
        return ('💊', 'rgba(255,255,255,.08)')

    # Direct match — تطابق مستقیم
    if drug_form_value in DRUG_FORM_ICON_MAP:
        return DRUG_FORM_ICON_MAP[drug_form_value]

    # Partial match for combined values like 'قرص/اسپری' — تطابق جزئی برای مقادیر ترکیبی
    val_lower = drug_form_value.lower()
    for key, result in DRUG_FORM_ICON_MAP.items():
        if key in val_lower or key in drug_form_value:
            return result

    return ('💊', 'rgba(255,255,255,.08)')


@login_required
def drug_bank(request):
    """
    Drug bank listing with search, category, drug form, and OTC/Rx filters.
    Full context variables matching drug_bank.html template exactly.

    لیست بانک دارو با فیلتر جستجو، دسته‌بندی، شکل دارویی و OTC/Rx.
    تمام متغیرهای context دقیقاً مطابق با template drug_bank.html ارسال می‌شود.

    FIXED BUGS vs old code — باگ‌های اصلاح‌شده نسبت به کد قدیمی:
    ① Context variable names now match template:
       search_query, selected_category, selected_form, selected_otc
       نام متغیرهای context حالا با template مطابقت دارد.
    ② otc_rx filter uses lowercase 'otc'/'rx' matching model choices
       فیلتر otc_rx از 'otc'/'rx' حروف کوچک استفاده می‌کند که با choices مطابقت دارد.
    ③ form_choices and otc_choices passed for template dropdowns
       form_choices و otc_choices برای dropdown‌های template ارسال می‌شود.
    ④ otc_count and rx_count use lowercase for accurate counting
       otc_count و rx_count از حروف کوچک برای شمارش دقیق استفاده می‌کند.
    ⑤ Excel export integrated via export=excel query param
       خروجی Excel از طریق پارامتر export=excel یکپارچه شد.
    ⑥ drug_to_product URL now uses correct endpoint name
       URL مربوط به drug_to_product حالا از نام endpoint صحیح استفاده می‌کند.
    """
    from .models import Drug, DrugCategory

    # ── Read filter parameters from GET request ─────────────────
    # خواندن پارامترهای فیلتر از درخواست GET
    search_query      = request.GET.get('q', '').strip()
    selected_category = request.GET.get('category', '').strip()
    selected_form     = request.GET.get('form', '').strip()
    selected_otc      = request.GET.get('otc', '').strip()
    export_format     = request.GET.get('export', '').strip()

    # ── Base queryset: only active drugs ────────────────────────
    # کوئری‌ست پایه: فقط داروهای فعال
    qs = Drug.objects.filter(is_active=True).select_related('category')

    # ── Apply text search across key fields ─────────────────────
    # اعمال جستجوی متنی روی فیلدهای اصلی
    if search_query:
        qs = qs.filter(
            Q(name_fa__icontains=search_query)      |  # Persian name — نام فارسی
            Q(name_en__icontains=search_query)      |  # English name — نام انگلیسی
            Q(brand_name__icontains=search_query)   |  # Brand name — نام تجاری
            Q(indications__icontains=search_query)  |  # Indications — موارد مصرف
            Q(active_ingredient__icontains=search_query)  # Active ingredient — ماده موثره
        )

    # ── Apply category filter ────────────────────────────────────
    # اعمال فیلتر دسته‌بندی
    if selected_category:
        qs = qs.filter(category_id=selected_category)

    # ── Apply drug form filter ───────────────────────────────────
    # اعمال فیلتر فرم دارو
    # Uses icontains to match both English keys and Persian seed values
    # از icontains استفاده می‌کند تا هم کلیدهای انگلیسی و هم مقادیر فارسی seed را پوشش دهد
    if selected_form:
        qs = qs.filter(drug_form__icontains=selected_form)

    # ── Apply OTC/Rx filter ──────────────────────────────────────
    # اعمال فیلتر OTC/Rx
    # IMPORTANT: filter with iexact to handle both 'otc' and 'OTC' in database
    # مهم: از iexact استفاده می‌کند تا هم 'otc' و هم 'OTC' در دیتابیس را پوشش دهد
    if selected_otc:
        qs = qs.filter(otc_rx__iexact=selected_otc)

    # ── Sort alphabetically by Persian name ─────────────────────
    # مرتب‌سازی بر اساس نام فارسی به صورت حروف الفبا
    qs = qs.order_by('name_fa')

    # ── Handle Excel export request ─────────────────────────────
    # پردازش درخواست خروجی Excel
    if export_format == 'excel':
        return drug_export_excel(request)

    # ── Aggregated counts for KPI cards ─────────────────────────
    # تعداد کلی برای کارت‌های KPI
    # Count ALL active drugs (not filtered) for the total KPI card
    # تعداد کل داروهای فعال (بدون فیلتر) برای کارت KPI اول
    total_all = Drug.objects.filter(is_active=True).count()

    # Count OTC and Rx using iexact to catch both uppercase and lowercase stored values
    # شمارش OTC و Rx با iexact تا هم مقادیر بزرگ و هم کوچک را بگیرد
    otc_count = Drug.objects.filter(
        is_active=True, otc_rx__iexact='otc'
    ).count()
    rx_count  = Drug.objects.filter(
        is_active=True, otc_rx__iexact='rx'
    ).count()

    # ── Category list for filter dropdown ───────────────────────
    # لیست دسته‌بندی‌ها برای dropdown فیلتر
    categories = DrugCategory.objects.all().order_by('name')

    # ── Drug form choices from model ─────────────────────────────
    # انتخاب‌های فرم دارو از model
    # These are the official (key, display_label) tuples defined in Drug.FORM_CHOICES
    # اینها tupleهای رسمی (کلید، برچسب نمایشی) تعریف‌شده در Drug.FORM_CHOICES هستند
    form_choices = Drug.FORM_CHOICES

    # ── OTC/Rx choices from model ────────────────────────────────
    # انتخاب‌های OTC/Rx از model
    # These are the official (key, display_label) tuples defined in Drug.OTCPX_CHOICES
    # اینها tupleهای رسمی تعریف‌شده در Drug.OTCPX_CHOICES هستند
    otc_choices = Drug.OTCPX_CHOICES

    # ── Build context dict matching template variable names exactly ──
    # ساخت دیکشنری context با نام‌های متغیر دقیقاً مطابق template
    ctx = {
        **base_context(request),

        # Drug queryset — کوئری‌ست داروها
        'drugs':             qs,

        # Filter dropdown data — داده‌های dropdown فیلتر
        'categories':        categories,
        'form_choices':      form_choices,
        'otc_choices':       otc_choices,

        # KPI counts — تعداد KPI
        'total':             total_all,
        'otc_count':         otc_count,
        'rx_count':          rx_count,

        # Active filter values (for re-populating form fields) — مقادیر فیلتر فعال
        'search_query':      search_query,
        'selected_category': selected_category,
        'selected_form':     selected_form,
        'selected_otc':      selected_otc,
    }

    return render(request, 'pharmacy/drug_bank.html', ctx)


@login_required
def drug_detail(request, pk):
    """
    Drug detail page — individual drug information.
    صفحه جزئیات دارو — اطلاعات کامل یک دارو.
    """
    from .models import Drug

    drug = get_object_or_404(Drug, pk=pk, is_active=True)

    # Normalize otc_rx for template display — نرمال‌سازی otc_rx برای نمایش در template
    drug_otc_normalized = _normalize_otc(drug.otc_rx)

    # Get icon for this drug's form — دریافت آیکون برای فرم دارو
    drug_icon, drug_icon_bg = _get_drug_icon(drug.drug_form)

    ctx = {
        **base_context(request),
        'drug':               drug,
        'drug_otc_normalized': drug_otc_normalized,
        'drug_icon':          drug_icon,
        'drug_icon_bg':       drug_icon_bg,
    }
    return render(request, 'pharmacy/drug_detail.html', ctx)


@login_required
@require_POST
def drug_to_product(request, pk):
    """
    Convert a drug from the drug bank into a product entry.
    Handles JSON body (from fetch()) and form POST data.
    تبدیل یک دارو از بانک دارو به یک رکورد محصول.
    هم JSON body (از fetch()) و هم داده‌های form POST را پردازش می‌کند.

    FIXED: drug.drug_category → drug.category (correct field name)
    اصلاح شد: drug.drug_category → drug.category (نام فیلد صحیح)
    """
    from .models import Drug

    drug = get_object_or_404(Drug, pk=pk, is_active=True)

    # ── Parse price and code from request body ───────────────────
    # خواندن قیمت و کد از بدنه درخواست
    # Support both JSON (fetch) and form POST — هم JSON و هم form POST پشتیبانی می‌کند
    content_type = request.content_type or ''
    if 'application/json' in content_type:
        try:
            body_data = json.loads(request.body)
        except json.JSONDecodeError:
            body_data = {}
        price = body_data.get('price', 0)
        code  = body_data.get('code', f'DRUG-{drug.pk}')
    else:
        price = request.POST.get('price', 0)
        code  = request.POST.get('code', f'DRUG-{drug.pk}')

    # ── Check for duplicate product code ────────────────────────
    # بررسی تکراری بودن کد محصول
    if Product.objects.filter(code=code, is_deleted=False).exists():
        return JsonResponse(
            {'success': False, 'message': f'کد محصول «{code}» قبلاً ثبت شده.'},
            status=400
        )

    # ── Map drug category to product category ───────────────────
    # تبدیل دسته دارو به دسته محصول
    # drug.category is a DrugCategory instance; we get_or_create a matching Category
    # drug.category یک نمونه DrugCategory است؛ ما یک Category مطابق می‌سازیم یا پیدا می‌کنیم
    cat = None
    if drug.category:
        cat, _ = Category.objects.get_or_create(name=drug.category.name)

    # ── Create the product from drug data ───────────────────────
    # ساخت محصول از اطلاعات دارو
    p = Product.objects.create(
        name        = drug.name_fa,
        code        = code,
        category    = cat,
        price       = price or 0,
        description = drug.indications or '',
        is_active   = True,
    )

    # ── Log activity ────────────────────────────────────────────
    # ثبت فعالیت
    UserActivity.objects.create(
        user=request.user,
        action=f"افزودن از بانک دارو: {p.name} (کد: {p.code})",
        path=request.path,
    )

    return JsonResponse({
        'success':    True,
        'message':    f'داروی «{drug.name_fa}» با موفقیت به محصولات اضافه شد.',
        'product_id': p.pk,
    })


# ══════════════════════════════════════════════════════════════════
# SECTION 18 — DRUG BANK EXCEL EXPORT
# بخش ۱۸ — خروجی Excel بانک دارو
# ══════════════════════════════════════════════════════════════════

@login_required
def drug_export_excel(request):
    """
    Export drug bank to a professionally styled Excel file.
    Respects the same search/category filters as the main drug_bank view.
    خروجی Excel از بانک دارو با قالب‌بندی حرفه‌ای.
    همان فیلترهای جستجو/دسته‌بندی view اصلی drug_bank را اعمال می‌کند.

    FIXED FIELDS vs old broken code — فیلدهای اصلاح‌شده:
    ① drug.category  (was drug.drug_category — field does not exist)
       drug.category  (قبلاً drug.drug_category بود — فیلد وجود ندارد)
    ② drug.drug_form (was drug.dosage_form — field does not exist)
       drug.drug_form  (قبلاً drug.dosage_form بود — فیلد وجود ندارد)
    ③ drug.otc_rx displayed correctly (was drug.is_otc — boolean field that doesn't exist)
       drug.otc_rx به درستی نمایش داده می‌شود (قبلاً drug.is_otc بود — فیلد بولین که وجود ندارد)
    ④ Removed all references to irc_code (field does not exist in model)
       تمام ارجاعات به irc_code حذف شدند (فیلد در model وجود ندارد)
    """
    from .models import Drug

    # ── Read same filter params as drug_bank view ───────────────
    # خواندن همان پارامترهای فیلتر مانند view اصلی drug_bank
    search_query      = request.GET.get('q', '').strip()
    selected_category = request.GET.get('category', '').strip()
    selected_form     = request.GET.get('form', '').strip()
    selected_otc      = request.GET.get('otc', '').strip()

    # ── Build filtered queryset ──────────────────────────────────
    # ساخت کوئری‌ست فیلترشده
    qs = Drug.objects.filter(is_active=True).select_related('category')

    if search_query:
        qs = qs.filter(
            Q(name_fa__icontains=search_query)     |
            Q(name_en__icontains=search_query)     |
            Q(indications__icontains=search_query)
        )

    if selected_category:
        qs = qs.filter(category_id=selected_category)

    if selected_form:
        qs = qs.filter(drug_form__icontains=selected_form)

    # Use iexact to match stored 'OTC'/'RX' or model 'otc'/'rx'
    # از iexact استفاده می‌کند تا 'OTC'/'RX' ذخیره‌شده یا 'otc'/'rx' model را تشخیص دهد
    if selected_otc:
        qs = qs.filter(otc_rx__iexact=selected_otc)

    qs = qs.order_by('name_fa')

    # ── Setup workbook ───────────────────────────────────────────
    # راه‌اندازی workbook
    now        = timezone.now()
    jalali_str = tehran_jalali_full(now)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'بانک داروها'
    ws.sheet_view.rightToLeft = True   # RTL for Persian — راست به چپ برای فارسی

    # ── Style helper functions ───────────────────────────────────
    # توابع کمکی استایل
    def mkfill(h):
        """Create solid fill — ساخت پر کردن جامد"""
        return PatternFill('solid', fgColor=h)

    def mkfont(bold=False, size=10, color='1E293B', italic=False):
        """Create font — ساخت فونت"""
        return Font(bold=bold, size=size, color=color, italic=italic, name='Calibri')

    def mkalign(h='center', wrap=False):
        """Create alignment — ساخت تراز"""
        return Alignment(horizontal=h, vertical='center', wrap_text=wrap, readingOrder=2)

    thin = Side(style='thin', color='A7F3D0')
    brd  = Border(left=thin, right=thin, top=thin, bottom=thin)

    # ── Row 1: Title header ──────────────────────────────────────
    # ردیف ۱: عنوان اصلی
    ws.merge_cells('A1:J1')
    c           = ws['A1']
    c.value     = '🏥   بانک جامع داروها — سازمان دارو شیراز'
    c.font      = Font(bold=True, size=16, color='FFFFFF', name='Calibri')
    c.fill      = mkfill('0D9488')
    c.alignment = mkalign()
    ws.row_dimensions[1].height = 44

    # ── Row 2: Date and count ────────────────────────────────────
    # ردیف ۲: تاریخ و تعداد
    drug_count = qs.count()
    ws.merge_cells('A2:J2')
    c           = ws['A2']
    c.value     = f'تاریخ تهیه: {jalali_str}  |  تعداد داروها: {drug_count} دارو'
    c.font      = mkfont(size=10, color='134E4A', italic=True)
    c.fill      = mkfill('CCFBF1')
    c.alignment = mkalign()
    ws.row_dimensions[2].height = 24

    # ── Row 3: Decorative stripe ─────────────────────────────────
    # ردیف ۳: نوار تزئینی
    ws.merge_cells('A3:J3')
    ws['A3'].fill = mkfill('99F6E4')
    ws.row_dimensions[3].height = 5

    # ── Row 4: Column headers ────────────────────────────────────
    # ردیف ۴: سرستون‌ها
    # 10 columns covering all key drug fields — ۱۰ ستون شامل تمام فیلدهای اصلی دارو
    COLS = [
        ('نام فارسی',          30),   # Persian name — نام فارسی
        ('نام انگلیسی/ژنریک',  30),   # English/Generic name — نام انگلیسی/ژنریک
        ('نام تجاری/برند',     22),   # Brand name — نام تجاری
        ('گروه دارویی',        22),   # Drug category — گروه دارویی
        ('فرم دارو',           16),   # Drug form — فرم دارو
        ('دوز / قدرت',         16),   # Dose / strength — دوز / قدرت
        ('موارد مصرف',         40),   # Indications — موارد مصرف
        ('نوع تجویز',          14),   # Prescription type — نوع تجویز
        ('تولیدکننده',         22),   # Manufacturer — تولیدکننده
        ('ماده مؤثره',         24),   # Active ingredient — ماده مؤثره
    ]

    for ci, (hdr, w) in enumerate(COLS, 1):
        c           = ws.cell(row=4, column=ci, value=hdr)
        c.font      = Font(bold=True, size=11, color='FFFFFF', name='Calibri')
        c.fill      = mkfill('14B8A6')
        c.alignment = mkalign(wrap=True)
        c.border    = brd
        ws.column_dimensions[get_column_letter(ci)].width = w
    ws.row_dimensions[4].height = 30

    # ── Data rows ────────────────────────────────────────────────
    # ردیف‌های داده
    for idx, d in enumerate(qs, 1):
        r  = idx + 4
        bg = 'F0FDFA' if idx % 2 == 0 else 'FFFFFF'  # Alternating rows — ردیف‌های متناوب

        # Normalize otc_rx for display — نرمال‌سازی otc_rx برای نمایش
        # Handle both 'OTC'/'RX' (seed) and 'otc'/'rx' (model) stored values
        # هر دو 'OTC'/'RX' (seed) و 'otc'/'rx' (model) ذخیره‌شده را پردازش می‌کند
        otc_display = '—'
        if d.otc_rx:
            otc_lower = d.otc_rx.lower().strip()
            if otc_lower == 'otc':
                otc_display = 'OTC — بدون نسخه'
            elif otc_lower == 'rx':
                otc_display = 'Rx — نیاز به نسخه'
            elif otc_lower == 'na':
                otc_display = 'غیر دارویی'

        vals = [
            d.name_fa or '—',                                     # Persian name — نام فارسی
            d.name_en or '—',                                      # English name — نام انگلیسی
            d.brand_name or '—',                                   # Brand name — نام تجاری
            d.category.name if d.category else '—',                # Category — دسته‌بندی
            d.drug_form or '—',                                    # Drug form — فرم دارو
            d.strength or '—',                                     # Strength — دوز
            d.indications or '—',                                  # Indications — موارد مصرف
            otc_display,                                           # OTC/Rx display — نمایش OTC/Rx
            d.manufacturer or '—',                                 # Manufacturer — تولیدکننده
            d.active_ingredient or '—',                            # Active ingredient — ماده مؤثره
        ]

        for ci, val in enumerate(vals, 1):
            c        = ws.cell(row=r, column=ci, value=val)
            c.fill   = mkfill(bg)
            c.border = brd
            c.font   = mkfont(size=9)

            # Column-specific alignment — تراز خاص هر ستون
            if ci in (1, 2, 3, 7):
                c.alignment = mkalign('right', wrap=(ci == 7))
            else:
                c.alignment = mkalign('center')

            # Highlight OTC/Rx cell — برجسته کردن سلول OTC/Rx
            if ci == 8:
                if d.otc_rx and d.otc_rx.lower() == 'otc':
                    c.font = Font(bold=True, size=9, color='166534', name='Calibri')
                    c.fill = mkfill('DCFCE7')
                elif d.otc_rx and d.otc_rx.lower() == 'rx':
                    c.font = Font(bold=True, size=9, color='DC2626', name='Calibri')
                    c.fill = mkfill('FEF2F2')

        ws.row_dimensions[r].height = 22

    # ── Freeze header rows ───────────────────────────────────────
    # ثابت کردن ردیف‌های سرستون
    ws.freeze_panes = 'A5'

    # ── Build and return response ────────────────────────────────
    # ساخت و بازگرداندن پاسخ
    filename = f'drug_bank_{tehran_jalali_filename(now)}.xlsx'
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


# ══════════════════════════════════════════════════════════════════
# SECTION 19 — DATABASE FIX UTILITY (RUN ONCE)
# بخش ۱۹ — ابزار تصحیح دیتابیس (یک بار اجرا کنید)
#
# This view fixes the data stored incorrectly by seed scripts.
# Run it ONCE by visiting: /pharmacy/fix-drug-data/
# Then remove the URL from urls.py.
#
# این view داده‌هایی که توسط اسکریپت‌های seed به اشتباه ذخیره شدند را تصحیح می‌کند.
# فقط یک بار آن را با مراجعه به: /pharmacy/fix-drug-data/ اجرا کنید.
# سپس URL را از urls.py حذف کنید.
# ══════════════════════════════════════════════════════════════════

@login_required
def fix_drug_data(request):
    """
    One-time database fix for drug data stored with wrong casing/values by seed scripts.

    Fixes:
    ① otc_rx: 'OTC' → 'otc',  'RX' → 'rx'  (uppercase → lowercase)
    ② drug_form: Persian text / mixed values → correct English model keys

    This is safe to run multiple times (idempotent).
    Run once, then remove the URL from urls.py for security.

    تصحیح یک‌باره دیتابیس برای داده‌های دارویی که با مقادیر/کیس اشتباه توسط seed ذخیره شدند.

    تصحیح‌ها:
    ① otc_rx: 'OTC' → 'otc',  'RX' → 'rx'  (حروف بزرگ → حروف کوچک)
    ② drug_form: متن فارسی / مقادیر ترکیبی → کلیدهای انگلیسی صحیح model

    اجرای مکرر بی‌خطر است (idempotent).
    یک بار اجرا کنید، سپس برای امنیت URL را از urls.py حذف کنید.
    """
    from .models import Drug

    # ── Only superusers can run this fix ─────────────────────────
    # فقط superuser می‌تواند این تصحیح را اجرا کند
    if not request.user.is_superuser:
        return JsonResponse({'error': 'دسترسی مجاز نیست. فقط superuser می‌تواند این عملیات را انجام دهد.'}, status=403)

    results = {
        'otc_fixed':  0,
        'form_fixed': 0,
        'errors':     [],
    }

    # ── Fix 1: Normalize otc_rx casing ──────────────────────────
    # تصحیح ۱: نرمال‌سازی بزرگی/کوچکی حروف otc_rx
    # Map from seed-stored values → correct model choice keys
    # نگاشت از مقادیر ذخیره‌شده توسط seed → کلیدهای صحیح model
    OTC_FIX_MAP = {
        'OTC':  'otc',
        'RX':   'rx',
        'Rx':   'rx',
        'rx ':  'rx',   # strip trailing space — حذف فاصله انتهایی
        'otc ': 'otc',
        'NA':   'na',
        'N/A':  'na',
    }

    for wrong_val, correct_val in OTC_FIX_MAP.items():
        updated = Drug.objects.filter(otc_rx=wrong_val).update(otc_rx=correct_val)
        results['otc_fixed'] += updated

    # ── Fix 2: Normalize drug_form values ────────────────────────
    # تصحیح ۲: نرمال‌سازی مقادیر drug_form
    # Map from Persian/mixed seed values → English model FORM_CHOICES keys
    # نگاشت از مقادیر فارسی/ترکیبی seed → کلیدهای انگلیسی FORM_CHOICES مدل
    FORM_FIX_MAP = {
        # Persian forms stored by seed — فرم‌های فارسی ذخیره‌شده توسط seed
        'قرص':                  'tablet',
        'قرص جوشان':            'tablet',
        'قرص زیر زبانی':        'tablet',
        'کپسول':                'capsule',
        'شربت':                 'syrup',
        'قطره':                 'drop',
        'آمپول':                'injection',
        'آمپول / تزریقی':       'injection',
        'سرم':                  'serum',
        'پماد':                 'ointment',
        'کرم':                  'cream',
        'ژل':                   'gel',
        'اسپری':                'spray',
        'اینهالر':              'inhaler',
        'پودر استنشاقی':        'inhaler',
        'پچ':                   'patch',
        'پچ / چسب':             'patch',
        'شیاف':                 'suppository',
        'پودر':                 'powder',
        'محلول':                'solution',
        'لوسیون':               'lotion',
        'شامپو':                'shampoo',
        'صابون':                'soap',
        'دستگاه / تجهیزات':     'device',
        'باند / گاز / پانسمان': 'bandage',
        'پانسمان':              'bandage',
        # Combined values from seed — مقادیر ترکیبی از seed
        'قرص/اسپری':            'tablet',
        'قرص/پودر':             'tablet',
        'کپسول/پچ':             'capsule',
        'قرص/آمپول':            'tablet',
        'آمپول/شربت':           'injection',
        'آمپول/محلول':          'injection',
        'قرص/آمپول/کرم':        'tablet',
        'زیر زبانی':            'tablet',
        'تزریقی':               'injection',
        'آمپول دپو':            'injection',
        'نبولایزر':             'solution',
        'ساشه':                 'powder',
        'ویال':                 'injection',
        'محلول/ویال':           'solution',
    }

    for wrong_val, correct_val in FORM_FIX_MAP.items():
        try:
            updated = Drug.objects.filter(drug_form=wrong_val).update(drug_form=correct_val)
            results['form_fixed'] += updated
        except Exception as e:
            results['errors'].append(f"{wrong_val}: {str(e)}")

    # ── Log this fix activity ────────────────────────────────────
    # ثبت فعالیت تصحیح
    UserActivity.objects.create(
        user=request.user,
        action=(
            f"تصحیح دیتابیس دارو: "
            f"{results['otc_fixed']} otc_rx اصلاح، "
            f"{results['form_fixed']} drug_form اصلاح"
        ),
        path=request.path,
    )

    total_drugs = Drug.objects.count()
    return JsonResponse({
        'success':        True,
        'otc_rx_fixed':   results['otc_fixed'],
        'drug_form_fixed': results['form_fixed'],
        'errors':         results['errors'],
        'total_drugs':    total_drugs,
        'message': (
            f"تصحیح کامل شد. "
            f"{results['otc_fixed']} مقدار otc_rx و "
            f"{results['form_fixed']} مقدار drug_form اصلاح شدند. "
            f"کل داروها: {total_drugs}"
        ),
    })
# ══════════════════════════════════════════════════════════════════
# SECTION 20 — AI PHARMACY ASSISTANT (Powered by Groq)
# بخش ۲۰ — دستیار هوشمند دارویی (با استفاده از Groq)
# ══════════════════════════════════════════════════════════════════

@login_required
@require_POST
def ai_chat(request):
    """
    AI pharmacy assistant endpoint — answers drug-related questions via Groq API.
    نقطه پایانی دستیار هوشمند دارویی — پاسخ به سوالات دارویی از طریق API Groq.
    """
    try:
        body = json.loads(request.body)
        user_message = body.get('message', '').strip()
    except Exception:
        return JsonResponse({'error': 'درخواست نامعتبر'}, status=400)

    if not user_message:
        return JsonResponse({'error': 'پیام خالی است'}, status=400)

    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)

        completion = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[
                {
                    'role': 'system',
                    'content': (
                        'تو یک دستیار دارویی متخصص هستی که در سیستم مدیریت داروخانه  کار می‌کنی. '
                        'فقط به سوالات دارویی پاسخ بده: موارد مصرف، عوارض جانبی، تداخل دارویی، دوز مصرف، '
                        'اطلاعات دارویی عمومی. پاسخ‌هایت را به فارسی، مختصر و مفید بنویس.'
                    )
                },
                {'role': 'user', 'content': user_message}
            ],
            max_tokens=500,
        )

        reply = completion.choices[0].message.content
        return JsonResponse({'reply': reply})

    except Exception as e:
        return JsonResponse({'error': f'خطا در ارتباط با سرویس هوش مصنوعی: {str(e)}'}, status=500)
# ══════════════════════════════════════════════════════════════════
# SECTION 19 — TEMPORARY ADMIN SETUP (REMOVE AFTER USE)
# بخش ۱۹ — ساخت موقت یوزر ادمین (بعد از استفاده حذف شود)
# ══════════════════════════════════════════════════════════════════
def temp_setup_admin(request):
    username = "amir"
    password = "Amir12345"

    user, created = PharmacyUser.objects.get_or_create(username=username)
    user.set_password(password)
    user.is_active = True
    user.is_staff = True
    user.save()

    user.refresh_from_db()
    check = user.check_password(password)

    status = "ساخته شد" if created else "به‌روزرسانی شد"
    return HttpResponse(
        f"کاربر «{username}» با موفقیت {status}.<br>"
        f"یوزرنیم: {username}<br>"
        f"پسورد: {password}<br>"
        f"is_active: {user.is_active}<br>"
        f"is_staff: {user.is_staff}<br>"
        f"check_password نتیجه: {check}<br>"
        f"username دقیق ذخیره‌شده: '{user.username}'<br>"
        f"تعداد کل یوزرها: {PharmacyUser.objects.count()}<br><br>"
        f"<b>هشدار: همین حالا این صفحه و خط مربوط به آن در urls.py را حذف کنید.</b>"
    )