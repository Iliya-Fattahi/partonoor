> بازگرفته‌شده در پاس نهایی: Desktop 27 (شامل صفحه‌ی تعمیرات و دو صفحه‌ی پنل) · Mobile 22 · بدون overflow افقی در 390/768/1024/1440، بدون خطای JS.

# گزارش اسکرین‌شات هر صفحه

همه‌ی تصاویر از سایت واقعی در حال اجرا (Chromium، DEBUG خاموش) گرفته شده‌اند: دسکتاپ ۱۴۴۰ پیکسل، موبایل ۳۹۰ پیکسل (DPR=2). در تصاویر تمام‌صفحه، هدر ثابت و نوار پایین موبایل برای جلوگیری از تکرار وسط تصویر، حالت `absolute/hidden` گرفته‌اند. نمای واقعی هدر در بالای هر صفحه دیده می‌شود.

| صفحه | دسکتاپ | موبایل | وضعیت | مشکلات یافته‌شده | رفع‌شده |
|---|---|---|---|---|---|
| صفحه اصلی | `screenshots/desktop/01-home.png` | `screenshots/mobile/01-home.png` | ✔ 200 | فونت قدیمی (وزیرمتن/CDN)؛ لودر تمام‌صفحه LCP را عقب می‌انداخت؛ تیتر h2 تکرارشونده در فوتر؛ ستون «تماس» فوتر خالی | فونت Estedad محلی؛ لودر حذف؛ فوتر بدون تیتر تکراری؛ در نبود تماس، لینک فرم تماس |
| آثار (فهرست) | `screenshots/desktop/02-works.png` | `screenshots/mobile/02-works.png` | ✔ 200 | فیلتر فقط با جاوااسکریپت و ?category؛ عنوان/توضیح مشترک برای همه‌ی دسته‌ها؛ تب‌های موبایل شکسته | جدا شدن هر دسته در صفحه‌ی مستقل با عنوان/توضیح/کانونیکال؛ ریدایرکت ۳۰۱ از نشانی قدیمی؛ تب‌ها nowrap |
| آثار — المان‌های زمینی و مناسبتی | `screenshots/desktop/03-works-cat-1.png` | `screenshots/mobile/03-works-cat-1.png` | ✔ 200 | — | — |
| آثار — المان‌های داستانی | `screenshots/desktop/04-works-cat-2.png` | `screenshots/mobile/04-works-cat-2.png` | ✔ 200 | — | — |
| آثار — لوسترهای شهری | `screenshots/desktop/05-works-cat-3.png` | — (دلیل: در فهرست حداقلیِ موبایل نبود؛ چیدمان همین قالب در صفحه‌ی مشابه موبایل بررسی شد) | ✔ 200 | — | — |
| آثار — ریسه‌های عرض خیابانی | `screenshots/desktop/06-works-cat-4.png` | — (دلیل: در فهرست حداقلیِ موبایل نبود؛ چیدمان همین قالب در صفحه‌ی مشابه موبایل بررسی شد) | ✔ 200 | — | — |
| فهرست پروژه‌ها | `screenshots/desktop/07-projects.png` | `screenshots/mobile/07-projects.png` | ✔ 200 | عنوان کوتاه (۱۹ نویسه) | عنوان و توضیح کامل‌تر؛ فیلتر noindex |
| هفت‌خان رستم | `screenshots/desktop/08-haft-khan-rostam.png` | `screenshots/mobile/08-haft-khan-rostam.png` | ✔ 200 | توضیح متا ۸۶ نویسه؛ alt تکراری (۸ مورد)؛ عکس‌ها بدون ابعاد و JPEG سنگین؛ تک‌عکس یتیم در شبکه | seo_title/description؛ ۳۱ alt یکتا از روی عکس‌ها؛ WebP+srcset+ابعاد؛ آخرین عکس فرد تمام‌عرض |
| محصولات (فهرست ریسه) | `screenshots/desktop/09-risheh-list.png` | — (دلیل: در فهرست حداقلیِ موبایل نبود؛ چیدمان همین قالب در صفحه‌ی مشابه موبایل بررسی شد) | ✔ 200 | — | عنوان/توضیح اختصاصی |
| ریسه نوری | `screenshots/desktop/10-risheh.png` | `screenshots/mobile/10-risheh.png` | ✔ 200 | alt یکسان برای سه عکس؛ بدون SEO اختصاصی | alt یکتا؛ عنوان/توضیح اختصاصی؛ اسکیمای Product |
| خدمات | `screenshots/desktop/11-services.png` | `screenshots/mobile/11-services.png` | ✔ 200 | عنوان‌ها کوتاه و بی‌زمینه (۱۴–۲۰ نویسه)؛ بدون لینک داخلی | عنوان/توضیح کامل‌تر؛ نوار «مراحل دیگر» و لینک به پروژه؛ اسکیمای Service |
| خدمت (نمونه: بازدید) | `screenshots/desktop/12-service-detail.png` | `screenshots/mobile/12-service-detail.png` | ✔ 200 | محتوای کوتاه (در انتظار متن مشتری) | لینک داخلی و Service schema؛ محتوای بیشتر نیازمند متن مشتری |
| مقالات | `screenshots/desktop/13-articles.png` | `screenshots/mobile/13-articles.png` | ✔ 200 | کانونیکال با query؛ OG عمومی | فیلتر برچسب/جست‌وجو noindex با کانونیکال به فهرست؛ مقاله‌ی ویژه با تصویر WebP |
| مقاله ۱: نور و مسئولیت شهری | `screenshots/desktop/14-article-1.png` | `screenshots/mobile/14-article-1.png` | ✔ 200 | بدون برچسب؛ excerpt با «چکیده»؛ alt تصویر خالی؛ تاریخ میلادی؛ نویسنده در JSON-LD خالی | ۶ برچسب واقعی؛ excerpt اصلاح؛ alt تصویر؛ تاریخ شمسی؛ نویسنده/jobTitle در Article؛ لینک‌های داخلی و مقاله‌ی مرتبط |
| مقاله ۲: نورپردازی شهری؛ پیوند علم، هنر و فناوری | `screenshots/desktop/15-article-2.png` | `screenshots/mobile/15-article-2.png` | ✔ 200 | همان مشکلات مقاله ۱ | همان اصلاحات؛ ۶ برچسب مخصوص این مقاله |
| درباره‌ی ما | `screenshots/desktop/16-about.png` | `screenshots/mobile/16-about.png` | ✔ 200 | بدون مسیرنما | مسیرنما + عنوان/توضیح اختصاصی |
| کارگاه | `screenshots/desktop/17-workshop.png` | `screenshots/mobile/17-workshop.png` | ✔ 200 | بدون مسیرنما | مسیرنما + عنوان/توضیح اختصاصی |
| تماس و مشاوره | `screenshots/desktop/18-contact.png` | `screenshots/mobile/18-contact.png` | ✔ 200 | اطلاعات تماس شرکت هنوز ثبت نشده (وابسته به مشتری) | مسیرنما و SEO اختصاصی؛ متن جایگزین تا ثبت اطلاعات |
| جست‌وجو | `screenshots/desktop/19-search.png` | `screenshots/mobile/19-search.png` | ✔ 200 | قابل ایندکس بود | noindex,follow و کانونیکال /search/ |
| خطای ۴۰۴ | `screenshots/desktop/20-404.png` | `screenshots/mobile/20-404.png` | ✔ 404 (صفحه‌ی خطا، مورد انتظار) | — | noindex؛ فونت و چیدمان یکدست |
| خطای ۴۰۳ | `screenshots/desktop/21-403.png` | `screenshots/mobile/21-403.png` | ✔ 403 (صفحه‌ی خطا، مورد انتظار) | — | noindex |
| خطای ۵۰۰ | `screenshots/desktop/22-500.png` | `screenshots/mobile/22-500.png` | ✔ 500 (صفحه‌ی خطا، مورد انتظار) | — | noindex |
| ورود به پنل مدیریت | `screenshots/desktop/23-login.png` | `screenshots/mobile/23-login.png` | ✔ 200 | فونت CDN | فونت محلی |
| داشبورد مدیریت | `screenshots/desktop/24-admin-dashboard.png` | `screenshots/mobile/24-admin-dashboard.png` | ✔ 200 | گروه «دسترسی‌ها» و Group/نقش؛ وزن تیترها نازک | فقط «حساب مدیر»؛ بدون Group؛ تیترهای ۷۰۰ |

## نتیجه‌ی بررسی خودکار
- هیچ خطای جاوااسکریپت یا سرریز افقی در هیچ‌کدام از صفحه‌ها (دسکتاپ و موبایل) گزارش نشد.
- هیچ پاسخ ۴xx/۵xx برای منابع (CSS/JS/فونت/تصویر) ثبت نشد؛ تنها پاسخ‌های ۴۰۴/۴۰۳/۵۰۰ مربوط به خودِ صفحه‌های خطای عمدی‌اند.
- موبایل: همه‌ی صفحه‌های اصلی (به‌جز دسته‌های ۳ و ۴ آثار و فهرست محصولات که قالب مشترک با نمونه‌های گرفته‌شده دارند) گرفته شد؛ ۴ دسته‌ی آثار در دسکتاپ هر ۴ مورد.