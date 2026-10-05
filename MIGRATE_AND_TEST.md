# پرتو نور — راه‌اندازی و تست

> مهاجرت‌ها تولید و همراه پروژه هستند؛ `manage.py check/test` اجرا شده است (نتیجه: `docs/TEST-RESULT.txt`).

## 1) مهاجرت دیتابیس
```
python manage.py migrate
python manage.py check
python manage.py makemigrations --check --dry-run   # باید «No changes detected» بدهد
```
مهاجرت `core.0002_remove_role_groups` فقط گروه‌های قدیمی «Content/Project/Article Manager» را حذف می‌کند و به کاربران یا محتوا دست نمی‌زند. `core.0003` نام انگلیسی شرکت را اختیاری می‌کند (مقدار پیش‌فرض قدیمی «PARTO NOOR» پاک می‌شود). `gallery.0002` دو فیلد اختیاری سئو به دسته‌های آثار می‌افزاید.

## 2) بارگذاری محتوای واقعی
```
python manage.py seed_real_media               # ایمن؛ چیزی که هست را رونویسی نمی‌کند
python manage.py seed_real_media --reset-works --reset-project --reset-home   # برای شروع تمیز
```
شامل: دسته‌های «آثار» از برگه‌ی مشتری، ۲۷ اثر (بعضی «در انتظار تأیید»)، پروژه‌ی هفت‌خان رستم با عکس‌های مرحله‌بندی‌شده، ریسه و مزیت‌ها، خدمات، دو مقاله، منوها و بخش‌های صفحه‌ی اصلی.

## 3) بررسی دستی (چک‌لیست)
- `/` `/gallery/` (گروه‌بندی + لایت‌باکس) `/projects/haft-khan-rostam/` `/products/risheh/` (ثبت سفارش و دیدن آن در `/admin/`) `/contact/` `/articles/` `/articles/<slug>/` `/services/` `/about/`
- ورود ادمین: داشبورد کاشی‌ای، «آثار» ← تغییر دسته‌ی یک عکس، آپلود عکس جدید، تأیید عکس‌های «در انتظار تأیید».
- 404 / 403 / 500، `sitemap.xml`، `robots.txt`، `/gallery/<slug>/` (و ریدایرکت ۳۰۱ از `?category=`).
- موبایل: منوی همبرگری، فیلترها، فرم‌ها.

## 4) نکات
- لوگو: فقط آیکون 32×32 موجود است؛ سایت تا آپلود لوگوی بزرگ (SVG/PNG ≥ 512px از «اطلاعات شرکت») از نشان برداری موقت استفاده می‌کند.
- فونت Estedad به‌صورت محلی ارائه می‌شود (`static/fonts/`)؛ چیزی از CDN بارگیری نمی‌شود. `SITE_URL` را در `.env` تولید تنظیم کنید (کانونیکال، sitemap، robots).
- ویدیوی شرکت برای وب به 1280px/17MB فشرده شد (`company_video_web.mp4`)؛ اصلی 103MB است.
- آدرس‌های `<slug>` به `<str:slug>` تغییر کرد تا اسلاگ فارسی 404 نشود.
