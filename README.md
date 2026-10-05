# پرتو نور — وب‌سایت شرکتی (Django)

وب‌سایت فارسی/راست‌چین شرکت **پرتو نور** (طراحی، ساخت و اجرای المان‌های نوری شهری) با پنل مدیریت ساده برای یک مدیر.
Django 5.0 · PostgreSQL (تولید) · فونت Estedad به‌صورت self-host · بدون سبد خرید و پرداخت آنلاین.

## نیازمندی‌ها
- Python 3.11+ (تست‌شده با 3.13)
- PostgreSQL 14+ برای تولید (برای اجرای محلی/تست، SQLite کافی است)
- کتابخانه‌ی `libmagic` در سیستم‌عامل (برای اعتبارسنجی فایل‌های آپلودی)
- یک وب‌سرور/WSGI (gunicorn + nginx)

## نصب
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt          # در سرور: requirements/production.txt
cp .env.example .env                         # و مقادیر را پر کنید
```

## متغیرهای محیطی (`.env`)
| متغیر | توضیح |
|---|---|
| `SECRET_KEY` | **اجباری در تولید.** رشته‌ی تصادفی بلند؛ هرگز در مخزن قرار نمی‌گیرد. |
| `SITE_URL` | **اجباری در تولید.** آدرس عمومی با https (برای canonical، sitemap، robots و JSON-LD). دامنه‌ای در کد ثابت نشده است. |
| `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | اختیاری؛ در صورت خالی بودن از `SITE_URL` ساخته می‌شود. |
| `DATABASE_NAME/USER/PASSWORD/HOST/PORT` | اتصال PostgreSQL |
| `STATIC_ROOT`, `MEDIA_ROOT` | مسیر فایل‌های استاتیک و رسانه |
| `EMAIL_*`, `CONSULTATION_NOTIFY_EMAIL` | اعلان ایمیلی درخواست مشاوره (اختیاری) |
| `LOG_FILE` | مسیر فایل لاگ (پوشه در صورت نبودن ساخته می‌شود) |

## پایگاه داده و migrations
Migrationها همراه پروژه هستند و **نیازی به اجرای `makemigrations` نیست.**
```bash
python manage.py migrate
python manage.py makemigrations --check --dry-run   # باید «No changes detected» بدهد
```

## داده‌ی اولیه (seed)
```bash
python manage.py seed_real_media          # دسته‌های آثار، آثار واقعی، هفت‌خان رستم، ریسه، مقالات، صفحه‌ی اصلی
python manage.py seed_real_media --help   # گزینه‌های --reset-* برای بازنویسی یک بخش
python manage.py optimize_images          # نسخه‌های WebP (در seed هم اجرا می‌شود)
python manage.py createsuperuser          # تنها حساب مدیر
```
فایل‌های تصویری seed در پوشه‌ی `seed_assets/` هستند. هیچ شماره‌ی تماس، ایمیل، آدرس یا لوگویی ساخته نشده است؛ این‌ها را مدیر در «تنظیمات سایت» وارد می‌کند.

## اجرا
```bash
python manage.py runserver                                   # توسعه (PostgreSQL)
DJANGO_SETTINGS_MODULE=config.settings.sqlite_test python manage.py runserver   # بدون PostgreSQL
```

## تست
```bash
DJANGO_SETTINGS_MODULE=config.settings.sqlite_test python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
```
نتیجه‌ی آخرین اجرا در `docs/TEST-RESULT.txt` ثبت شده است.

## چک‌لیست تولید
1. `.env` با `SECRET_KEY` واقعی، `SITE_URL`، اطلاعات PostgreSQL و (در صورت نیاز) ایمیل.
2. `DJANGO_SETTINGS_MODULE=config.settings.production` (پیش‌فرض `wsgi.py`).
3. `python manage.py migrate && python manage.py collectstatic --noinput`
4. `python manage.py check --deploy` — باید بدون هشدار باشد.
5. HTTPS فعال و `X-Forwarded-Proto` از nginx ارسال شود (تنظیمات SSL redirect، کوکی امن و HSTS در `production.py` است).
6. nginx: سرو `/static/` و `/media/`؛ دسترسی نوشتن فقط برای پوشه‌ی media و logs.
7. در پنل: تنظیمات سایت (لوگو، تلفن، ایمیل، آدرس، شبکه‌ها) را کامل کنید.
8. آدرس `SITE_URL/sitemap.xml` را در Search Console ثبت کنید.

## پنل مدیریت
آدرس `/admin/` — یک مدیر (superuser) همه‌ی محتوا را اداره می‌کند؛ نقش یا گروه دیگری وجود ندارد.
بخش‌ها: صفحه‌ی اصلی، آثار (دسته‌ها و تصاویر)، پروژه‌ها (از جمله هفت‌خان رستم)، ریسه و سفارش‌های ریسه، خدمات، مقالات و برچسب‌ها،
گالری، درباره‌ی ما، کارگاه، تیم، منوها، تنظیمات سایت (لوگو و اطلاعات تماس)، درخواست‌های مشاوره، پیام‌های تماس.
راهنمای کوتاه‌تر برای مدیر: `HANDOVER.md`.

- **صفحه اصلی:** «بخش‌های صفحه اصلی» — هر بخش برچسب، عنوان، متن، عکس/ویدیو و دکمه‌ی خودش را دارد (راهنمای هر بخش بالای فرم نوشته شده). ترتیب با عدد «ترتیب نمایش» و نمایش/مخفی با تیک تغییر می‌کند.
- **اطلاعات تماس:** «تنظیمات سایت» — شماره تماس، اینستاگرام و تیک نمایش واتس‌اپ/تلگرام (پیوندها از همان شماره ساخته می‌شوند).
- **صفحه‌ی تعمیرات:** «تنظیمات سایت ← صفحه‌ی تعمیرات» — با تیک «حالت تعمیرات فعال باشد» بازدیدکنندگان صفحه‌ی تعمیرات (کد 503، noindex) را می‌بینند؛ پنل مدیریت و مدیر واردشده سایت را عادی می‌بینند.

## رسانه
آپلودها در `MEDIA_ROOT` ذخیره می‌شوند؛ تصاویر اعتبارسنجی و به WebP بهینه می‌شوند، SVG پاک‌سازی می‌شود، و متن مقالات با bleach تمیز می‌شود.

## استقرار
gunicorn پشت nginx، `config.wsgi:application`. برای نسخه‌ی بعدی: `git pull`، `pip install -r requirements/production.txt`، `migrate`، `collectstatic`، ریستارت سرویس.

## ساختار
`apps/` (articles, company, contact, core, gallery, products, projects, services) · `config/` (settings, urls, sitemaps) · `templates/` · `static/` · `seed_assets/` · `docs/` (ممیزی SEO، تایپوگرافی، اسکرین‌شات‌ها) · `screenshots/`
