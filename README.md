# 💊 سیستم هوشمند مدیریت داروخانه
### Pharmacy Management System — Python · Django

<div dir="rtl">

> یک پلتفرم وب یکپارچه برای مدیریت هوشمند داروخانه‌ها با معماری چندداروخانه‌ای و دستیار هوشمند مبتنی بر هوش مصنوعی

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.x-green?logo=django)](https://djangoproject.com)
[![License](https://img.shields.io/badge/License-MIT-purple)](LICENSE)

---

## ✨ امکانات اصلی

- 🤖 **دستیار دارویی هوشمند** — چت‌بات تخصصی با مدل Llama 3.3 از طریق Groq API
- 🏗️ **معماری Multi-Tenant** — پایگاه داده مجزا برای هر داروخانه
- 💊 **بانک جامع دارویی** — جستجوی پیشرفته با خروجی Excel
- 📦 **مدیریت محصولات** — افزودن، ویرایش، حذف نرم و عملیات گروهی
- ⚡ **ویرایش AJAX** — تغییر قیمت و تخفیف بدون reload صفحه
- 🔔 **سیستم اعلانات** — ارسال پیام به کاربران خاص یا همه
- 🎫 **تیکت پشتیبانی** — پیگیری درخواست‌ها
- 📊 **خروجی Excel** — گزارش‌گیری با تاریخ شمسی
- 👤 **مدیریت پروفایل** — آواتار، رمز عبور و ردیابی فعالیت

---

## 🛠️ فناوری‌های استفاده‌شده

| فناوری | کاربرد |
|--------|---------|
| Python 3.11 | زبان اصلی |
| Django 4.x | فریمورک بک‌اند |
| SQLite | پایگاه داده (Multi-DB) |
| Groq API + Llama 3.3 | هوش مصنوعی |
| jQuery + AJAX | تعاملات بدون reload |
| OpenPyXL | تولید فایل Excel |
| jdatetime | تبدیل تاریخ شمسی |

---

## 🚀 نصب و راه‌اندازی

```bash
# ۱. کلون کردن پروژه
git clone https://github.com/username/pharmacy-management.git
cd pharmacy-management

# ۲. ساخت محیط مجازی
python -m venv venv
venv\Scripts\activate  # ویندوز
# source venv/bin/activate  # مک/لینوکس

# ۳. نصب وابستگی‌ها
pip install -r requirements.txt

# ۴. اجرای migrations
python manage.py migrate

# ۵. اجرای سرور
python manage.py runserver
```

---

## 👨‍💻 سازنده

**امیرمحمد محمدی**  
پایه یازدهم — رشته کامپیوتر | شیراز  
📧 xgadjet192@gmail.com

---

## 🏆 مسابقه

این پروژه برای **جشنواره برنامه‌نویسی استان فارس — خرداد ۱۴۰۵** طراحی و پیاده‌سازی شده است.  
موضوع: آزاد — حوزه سلامت و داروخانه

</div>
