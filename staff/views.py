# staff/views.py
from django.shortcuts import render

def staff_dashboard_view(request):
    """
    این ویو داشبورد پرسنل را نمایش می‌دهد.
    در آینده می‌توان منطق احراز هویت و دسترسی به اطلاعات پرسنل را اینجا اضافه کرد.
    """
    context = {
        'page_title': 'داشبورد پرسنل',
        # می‌تونی داده‌های لازم برای داشبورد رو اینجا به context اضافه کنی
        # مثال:
        # 'user_name': request.user.get_full_name() if request.user.is_authenticated else 'کاربر گرامی',
    }
    return render(request, "pharmacy/staff_dashboard.html")
from django.shortcuts import render
