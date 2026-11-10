/* MedFind language layer: the interface is Persian only (RTL).
 * Source strings are written in English keys; every known string
 * (exact match or pattern) is translated in place, including text the scripts
 * add later, and digits become Persian digits. Medicine and shop names are data,
 * not UI, so they are never touched. */
(function () {
  "use strict";
  const lang = "fa";
  const root = document.documentElement;
  root.lang = "fa"; root.dir = "rtl";

  const D = {
    // nav + common
    "Find medicine": "جستجوی دارو", "My pharmacy": "داروخانه من", "Admin": "مدیریت", "For pharmacies": "برای داروخانه‌ها",
    "Log in": "ورود", "Log out": "خروج", "Create account": "ساخت حساب", "Cancel": "انصراف", "Save": "ذخیره", "Close": "بستن",
    "Details": "جزئیات", "Call": "تماس", "Directions": "مسیریابی", "Switch theme": "تغییر پوسته",
    "Switch to light theme": "پوسته روشن", "Switch to dark theme": "پوسته تیره", "Skip to results": "رفتن به نتایج",
    "Skip to content": "رفتن به محتوا", "Skip to form": "رفتن به فرم",
    "MedFind: find your medicine at a pharmacy near you": "مدفایند: داروی خود را در داروخانه‌های اطراف پیدا کنید",
    "Compare prices · MedFind": "مقایسه قیمت · مدفایند",
    // hero
    "Which pharmacy has your medicine right now?": "داروی شما همین الان در کدام داروخانه موجود است؟",
    "Search once. Compare availability, price and distance across nearby pharmacies, with the time each listing was last confirmed.": "یک بار جستجو کنید. موجودی، قیمت و فاصله را بین داروخانه‌های اطراف مقایسه کنید، همراه با زمان آخرین تأیید هر مورد.",
    "Search": "جستجو", "MedFind": "مدفایند", "Medicine name": "نام دارو", "Medicine, brand or generic name": "نام دارو، برند یا ژنریک",
    "Medicine suggestions": "پیشنهاد دارو", "Quick searches": "جستجوهای سریع", "Try:": "امتحان کنید:",
    "Use my location": "استفاده از موقعیت من", "Location on": "موقعیت روشن است", "Locating…": "در حال یافتن موقعیت…",
    "Location stays in your browser and is only used to measure distance.": "موقعیت شما فقط در مرورگر می‌ماند و تنها برای محاسبه فاصله استفاده می‌شود.",
    "Showing distance from you. Click again to turn it off.": "فاصله از شما نمایش داده می‌شود. برای خاموش کردن دوباره کلیک کنید.",
    "Example result": "نمونه نتیجه", "Best match": "بهترین گزینه", "Limited stock": "موجودی محدود", "Available": "موجود",
    "Out of stock": "ناموجود", "Unknown": "نامشخص", "Stock unknown": "موجودی نامشخص",
    // results page
    "Results": "نتایج", "Something went wrong": "مشکلی پیش آمد", "We couldn't run that search": "جستجو انجام نشد",
    "Try again": "تلاش دوباره", "Filters": "فیلترها", "Show results": "نمایش نتایج", "Clear filters": "پاک کردن فیلترها",
    "Availability": "موجودی", "In stock only": "فقط موجود", "Verified pharmacies only": "فقط داروخانه‌های تأییدشده",
    "Distance": "فاصله", "Any distance": "هر فاصله‌ای", "Turn on your location to filter by distance.": "برای فیلتر بر اساس فاصله، موقعیت خود را روشن کنید.",
    "Sort results": "مرتب‌سازی نتایج", "Best overall": "بهترین کلی", "Nearest": "نزدیک‌ترین", "Lowest price": "کمترین قیمت", "Recently updated": "تازه‌ترین",
    "Card view": "نمای کارتی", "Comparison table view": "نمای جدول مقایسه", "Result layout": "چیدمان نتایج",
    "Narrow by product": "محدود کردن به یک دارو", "All": "همه",
    "No pharmacy lists this yet": "هنوز هیچ داروخانه‌ای این دارو را ثبت نکرده",
    "Check the spelling, or try the generic or brand name.": "املا را بررسی کنید یا نام ژنریک یا برند را امتحان کنید.",
    "Nothing matches your filters": "هیچ موردی با فیلترهای شما مطابقت ندارد",
    "Try removing a filter or widening the distance.": "یک فیلتر را بردارید یا فاصله را بیشتر کنید.",
    "Price not listed": "قیمت ثبت نشده", "Rx only": "نیازمند نسخه", "Verified": "تأییدشده", "Verified pharmacy": "داروخانه تأییدشده",
    "Pharmacy": "داروخانه", "Medicine": "دارو", "Price": "قیمت", "Status": "وضعیت", "Confirmed": "تأیید شده", "Actions": "اقدامات", "n/a": "–",
    "Can't reach the MedFind API, so you're seeing sample data.": "اتصال به سرور مدفایند برقرار نشد؛ داده‌های نمونه نمایش داده می‌شود.",
    "Change API address": "تغییر آدرس سرور", "API address": "آدرس سرور", "Save and retry": "ذخیره و تلاش دوباره",
    "Where is the MedFind API running?": "سرور مدفایند کجا اجرا می‌شود؟",
    // online results
    "Medicines found online": "داروهای یافت‌شده در اینترنت",
    "Prices are collected automatically from pharmacy websites and may be out of date. Open a medicine to compare shops.": "قیمت‌ها به‌طور خودکار از وب‌سایت داروخانه‌ها جمع‌آوری می‌شوند و ممکن است قدیمی باشند. برای مقایسه فروشگاه‌ها، دارو را باز کنید.",
    "Sort online results": "مرتب‌سازی نتایج آنلاین", "Cheapest": "ارزان‌ترین", "Most shops": "بیشترین فروشگاه",
    "From": "از", "Last price": "آخرین قیمت", "/ unit": "/ واحد", "/ mL": "/ میلی‌لیتر", "/ g": "/ گرم", "Toman": "تومان",
    "Open": "مشاهده", "Cheapest at": "ارزان‌ترین در", "Compare": "مقایسه",
    // product page
    "Back to results": "بازگشت به نتایج", "Lowest price": "کمترین قیمت", "Average": "میانگین", "Price history": "تاریخچه قیمت",
    "Go to shop": "رفتن به فروشگاه", "Also check partner pharmacies near you": "داروخانه‌های همکار نزدیک شما را هم ببینید",
    "No product selected": "هیچ دارویی انتخاب نشده", "Search medicines": "جستجوی دارو",
    "We can't find that medicine": "این دارو پیدا نشد", "Couldn't load this page": "بارگذاری صفحه ممکن نشد",
    "The price chart builds up as we re-check the shops (about every 6 hours). Come back soon.": "نمودار قیمت با بررسی دوباره فروشگاه‌ها (تقریباً هر ۶ ساعت) ساخته می‌شود. به‌زودی سر بزنید.",
    "Lowest price over time": "کمترین قیمت در طول زمان",
    // why / footer
    "One search, every pharmacy": "یک جستجو، همه داروخانه‌ها",
    "Use a brand, a generic name or an alternative spelling. Results come from every approved pharmacy at once, so you stop calling around.": "از نام برند، نام ژنریک یا املای دیگر استفاده کنید. نتایج هم‌زمان از همه داروخانه‌های تأییدشده می‌آید و دیگر لازم نیست تلفنی بپرسید.",
    "See how fresh each answer is": "ببینید هر پاسخ چقدر تازه است",
    "Every listing shows when the pharmacy last confirmed it, and warns you when the information is old.": "هر مورد زمان آخرین تأیید داروخانه را نشان می‌دهد و اگر اطلاعات قدیمی باشد هشدار می‌دهد.",
    "Pharmacies you can trust": "داروخانه‌های قابل اعتماد",
    "Pharmacies are reviewed before they appear. A shield marks the ones that have been verified.": "داروخانه‌ها پیش از نمایش بررسی می‌شوند. نشان سپر مخصوص داروخانه‌های تأییدشده است.",
    "Run a pharmacy?": "داروخانه دارید؟", "List your pharmacy": "داروخانه خود را ثبت کنید",
    "Keep your stock visible to people searching nearby. Update prices and availability in seconds, or import a spreadsheet.": "موجودی خود را برای افرادی که در نزدیکی جستجو می‌کنند نمایش دهید. قیمت و موجودی را در چند ثانیه به‌روز کنید یا فایل اکسل وارد کنید.",
    "Good to know.": "خوب است بدانید.",
    "MedFind shows availability and prices reported by pharmacies. It does not give medical advice or recommend medicines. Stock and prices change quickly, so confirm with the pharmacy before you travel. Prescription-only medicines need a valid prescription.": "مدفایند موجودی و قیمت‌های اعلام‌شده توسط داروخانه‌ها را نشان می‌دهد. مشاوره پزشکی نمی‌دهد و دارویی را توصیه نمی‌کند. موجودی و قیمت سریع تغییر می‌کنند، پس پیش از رفتن با داروخانه تماس بگیرید. داروهای نسخه‌ای به نسخه معتبر نیاز دارند.",
    "Prices and availability are collected automatically from pharmacy websites and can change at any time. Confirm on the shop's site before you order. MedFind does not give medical advice. Prescription-only medicines need a valid prescription.": "قیمت و موجودی به‌طور خودکار از وب‌سایت داروخانه‌ها جمع‌آوری می‌شود و هر لحظه ممکن است تغییر کند. پیش از سفارش در سایت فروشگاه تأیید کنید. مدفایند مشاوره پزشکی نمی‌دهد. داروهای نسخه‌ای به نسخه معتبر نیاز دارند.",
    Tablet: "قرص", Capsule: "کپسول", Syrup: "شربت", Injection: "آمپول", Drops: "قطره", Cream: "کرم", Ointment: "پماد",
    Gel: "ژل", Spray: "اسپری", Sachet: "ساشه", Suppository: "شیاف", Powder: "پودر", Solution: "محلول", Suspension: "سوسپانسیون",
    "Appear in search the moment an admin approves you": "به محض تأیید مدیر در جستجو نمایش داده می‌شوید",
    "Compare price and distance across pharmacies": "قیمت و فاصله را بین داروخانه‌ها مقایسه کنید",
    "Create a free account to keep your preferences.": "برای حفظ تنظیمات خود یک حساب رایگان بسازید.",
    "Create a pharmacy owner account to list your pharmacy.": "برای ثبت داروخانه خود یک حساب صاحب داروخانه بسازید.",
    "Enter your email and password.": "ایمیل و گذرواژه را وارد کنید.", "Enter your name and email.": "نام و ایمیل را وارد کنید.",
    "Find your medicine without the phone calls": "داروی خود را بدون تماس تلفنی پیدا کنید",
    "Log in to manage your pharmacy's listings or your account.": "برای مدیریت داروخانه یا حساب خود وارد شوید.",
    "No account needed just to search": "برای جستجو به حساب کاربری نیازی نیست",
    "Password must be at least 8 characters.": "گذرواژه باید دست‌کم ۸ نویسه باشد.", "Please wait…": "لطفاً صبر کنید…",
    "Put your stock in front of people who need it": "موجودی خود را به نیازمندان نشان دهید",
    "See how fresh every listing is": "ببینید هر مورد چقدر تازه است",
    "Show customers exactly when you last confirmed": "به مشتریان نشان دهید آخرین بار کی تأیید کرده‌اید",
    "Update price and stock in a few clicks": "قیمت و موجودی را با چند کلیک به‌روز کنید",
    "Wrong email or password.": "ایمیل یا گذرواژه اشتباه است.",
    "No online shop lists this yet": "هیچ فروشگاه آنلاینی هنوز این دارو را ثبت نکرده",
    "Prescription-only medicines are rarely sold online. Try a vitamin, syrup, drops or the generic name.": "داروهای نسخه‌ای معمولاً آنلاین فروخته نمی‌شوند. یک ویتامین، شربت، قطره یا نام ژنریک را امتحان کنید.",
    "Showing close matches. Check the spelling.": "نتایج نزدیک نمایش داده می‌شود. املای عبارت را بررسی کنید.",
    "Last confirmed": "آخرین تأیید", "A valid prescription is required.": "نسخه معتبر لازم است.",
    "Address": "نشانی", "Opening hours": "ساعت کاری", "Phone": "تلفن", "Website": "وب‌سایت",
    // login
    "Welcome back to MedFind": "به مدفایند خوش آمدید", "Log in to manage your pharmacy's listings.": "برای مدیریت داروخانه خود وارد شوید.",
    "Email": "ایمیل", "Password": "گذرواژه", "I am a…": "من…", "Customer": "مشتری", "Find medicine nearby": "دارو را در نزدیکی پیدا می‌کنم",
    "Pharmacy owner": "صاحب داروخانه", "List my stock": "موجودی‌ام را ثبت می‌کنم", "Full name": "نام کامل",
    "(8+ characters)": "(حداقل ۸ نویسه)", "(optional)": "(اختیاری)", "Account": "حساب کاربری",
    "Add a medicine": "افزودن دارو",
    "Pick a medicine from the list.": "یک دارو را از فهرست انتخاب کنید.",
    "Not confirmed": "تأیید نشده",
    "Stock": "موجودی",
    "Add listing": "افزودن مورد",
    "Import stock from a file": "وارد کردن موجودی از فایل",
    "Download a template": "دانلود قالب",
    "File (.csv or .xlsx, up to 2 MB)": "فایل (csv یا xlsx، حداکثر ۲ مگابایت)",
    "Import": "وارد کردن",
    "Start typing a name…": "نام را شروع به نوشتن کنید…",
    "Medicines": "داروها",
    "Approve pharmacies and manage the medicine catalogue.": "داروخانه\u200cها را تأیید کنید و فهرست داروها را مدیریت کنید.",
    "Pharmacies": "داروخانه\u200cها",
    "Categories": "دسته\u200cبندی\u200cها",
    "Data sources": "منابع داده",
    "Users": "کاربران",
    "Sections": "بخش\u200cها",
    "Couldn't load your dashboard": "بارگذاری داشبورد ممکن نشد",
    "Retry": "تلاش دوباره",
    "Set up your pharmacy": "داروخانهٔ خود را راه\u200cاندازی کنید",
    "An admin reviews new pharmacies before they show up in search.": "مدیر، داروخانه\u200cهای جدید را پیش از نمایش در جستجو بررسی می\u200cکند.",
    "Pharmacy name": "نام داروخانه",
    "Latitude": "عرض جغرافیایی",
    "Longitude": "طول جغرافیایی",
    "Use my current location": "استفاده از موقعیت فعلی من",
    "Needed so customers see distance.": "برای نمایش فاصله به مشتریان لازم است.",
    "Submit for approval": "ارسال برای تأیید",
    "Couldn't get your location.": "موقعیت شما دریافت نشد.",
    "Location isn't available in this browser.": "موقعیت\u200cیابی در این مرورگر در دسترس نیست.",
    "Name and address are required.": "نام و نشانی الزامی است.",
    "Submitted. We'll review it shortly.": "ارسال شد. به\u200cزودی بررسی می\u200cکنیم.",
    "Filter by medicine name": "فیلتر بر اساس نام دارو",
    "Confirm nothing has changed": "تأیید می\u200cکنم تغییری نکرده",
    "Confirmed, no change": "تأیید شد، بدون تغییر",
    "Row": "ردیف",
    "Import CSV": "وارد کردن CSV",
    "New medicine": "داروی جدید",
    "Name": "نام",
    "Generic": "ژنریک",
    "Brand": "برند",
    "Form": "شکل دارویی",
    "Aliases": "نام\u200cهای دیگر",
    "No medicines found": "دارویی پیدا نشد",
    "Saved": "ذخیره شد",
    "Prescription required": "نیازمند نسخه",
    "Name is required.": "نام الزامی است.",
    "Alternative names customers might search for.": "نام\u200cهای دیگری که مشتریان ممکن است جستجو کنند.",
    "None yet.": "هنوز چیزی نیست.",
    "New category": "دستهٔ جدید",
    "Pharmacy approved": "داروخانه تأیید شد",
    "Remove this pharmacy from public search?": "این داروخانه از جستجوی عمومی حذف شود؟",
    "Approval revoked": "تأیید لغو شد",
    "Crawl started. Refresh in a minute.": "خزش شروع شد. یک دقیقه دیگر صفحه را تازه کنید.",
    "Can't reach the MedFind API": "اتصال به سرور مدفایند برقرار نشد",
    "Your browser can't share a location.": "مرورگر شما موقعیت را به اشتراک نمی\u200cگذارد.",
    "Couldn't get your location. Check the browser permission.": "موقعیت دریافت نشد. دسترسی مرورگر را بررسی کنید.",
    "Searching…": "در حال جستجو…",
    "Description": "توضیحات",
    "Nothing waiting for review": "موردی در انتظار بررسی نیست",
    "No categories yet": "هنوز دسته\u200cای نیست",
    "Approved": "تأییدشده",
    "Pending": "در انتظار",
    "Working": "فعال",
    "Not crawled yet": "هنوز خزش نشده",
    "Crawl now": "خزش اکنون",
    "Last run": "آخرین اجرا",
    "Products": "محصولات",
    "Import a price list": "وارد کردن فهرست قیمت",
    "Source name": "نام منبع",
    "File": "فایل",
    "Prices are in": "قیمت\u200cها به",
    "Rial": "ریال",
    "Auto (Rial unless header says Toman)": "خودکار (ریال، مگر آنکه عنوان ستون تومان باشد)",
    "The crawler runs automatically (see scripts/crawl.py) and only reads sites that allow it in robots.txt.": "خزنده به\u200cطور خودکار اجرا می\u200cشود (scripts/crawl.py) و فقط سایت\u200cهایی را می\u200cخواند که robots.txt اجازه دهد.",
    "Role": "نقش",
    "Active": "فعال",
    "admin": "مدیر",
    "owner": "صاحب داروخانه",
    "pharmacy owner": "صاحب داروخانه",
    "customer": "مشتری",
    "Approve": "تأیید",
    "Revoke": "لغو تأیید",
    "Reject": "رد",
    "Edit": "ویرایش",
    "Delete": "حذف",
    "Add": "افزودن",
    "Update": "به\u200cروزرسانی",
    "Confirm": "تأیید",
    "Confirm all": "تأیید همه",
    "Save changes": "ذخیره تغییرات",
    "Add medicine": "افزودن دارو",
    "Medicine #": "دارو #",
    "Selected:": "انتخاب\u200cشده:",
    "Blocked by robots.txt": "مسدود با robots.txt",
    "Unreachable": "در دسترس نیست",
    "No sitemap": "بدون sitemap",
    "No product data": "بدون داده محصول",
    "Recent changes": "تغییرات اخیر",
    "Your listings": "موردهای شما",
    "No listings yet": "هنوز موردی ثبت نشده",
    "Add your first medicine to appear in search.": "اولین داروی خود را اضافه کنید تا در جستجو نمایش داده شوید.",
    "In stock": "موجود",
    "Low stock": "موجودی کم",
    "Out": "ناموجود",
    "Limited": "محدود",
    "Unconfirmed": "تأیید نشده",
    "Pending approval": "در انتظار تأیید",
    "Your pharmacy is waiting for admin approval. It won't appear in search until then.": "داروخانه شما منتظر تأیید مدیر است و تا آن زمان در جستجو نمایش داده نمی\u200cشود.",
    "Status:": "وضعیت:",
    "Latest": "آخرین",
    "Date": "تاریخ",
    "Change": "تغییر",
    "Created": "ایجاد شد",
    "Description (optional)": "توضیحات (اختیاری)",
    "Medicine, brand or generic name": "نام دارو، برند یا ژنریک",
    "Close filters": "بستن فیلترها",
    "1.1 km away": "۱٫۱ کیلومتر فاصله",
    "Updated 5 min ago": "۵ دقیقه پیش به\u200cروزرسانی شد",
    "If you opened this page from the API itself (/app/), this is already correct.": "اگر این صفحه را از خود API باز کرده\u200cاید (/app/)، این مقدار از قبل درست است.",
    "Medicines found online": "داروهای یافت\u200cشده در اینترنت",
    "Within": "تا",
    "Request failed": "درخواست ناموفق بود",
  };

  const AGO = [
    [/just now/g, "همین الان"], [/(\d+) min ago/g, "$1 دقیقه پیش"], [/(\d+) hours? ago/g, "$1 ساعت پیش"],
    [/(\d+) days? ago/g, "$1 روز پیش"], [/\bunknown\b/g, "نامشخص"],
  ];
  const ago = (s) => AGO.reduce((a, [re, to]) => a.replace(re, to), s);
  const P = [
    [/^Results for “(.+)”$/, (m) => `نتایج برای «${m[1]}»`],
    [/^No results for “(.+)”$/, (m) => `نتیجه‌ای برای «${m[1]}» پیدا نشد`],
    [/^(\d+) listings? from (\d+) pharmac(?:y|ies)$/, (m) => `${m[1]} مورد از ${m[2]} داروخانه`],
    [/^(\d+) medicines? from (\d+) online pharmac(?:y|ies)$/, (m) => `${m[1]} دارو از ${m[2]} داروخانه آنلاین`],
    [/^(\d+) results$/, (m) => `${m[1]} نتیجه`],
    [/^(\d+) shops?$/, (m) => `${m[1]} فروشگاه`],
    [/^(\d+) listings?$/, (m) => `${m[1]} مورد`],
    [/^(\d+) in stock$/, (m) => `${m[1]} موجود`],
    [/^Within (\d+) km$/, (m) => `تا ${m[1]} کیلومتر`],
    [/^([\d.]+) km$/, (m) => `${m[1]} کیلومتر`],
    [/^Only (\d+) left$/, (m) => `فقط ${m[1]} عدد مانده`],
    [/^Prices in (\d+) shops?$/, (m) => `قیمت در ${m[1]} فروشگاه`],
    [/^Shops? · (\d+) in stock$/, (m) => `فروشگاه · ${m[1]} موجود`],
    [/^([\d,.]+) Toman$/, (m) => `${m[1]} تومان`],
    [/^Up to (.+)$/, (m) => `تا ${tr(m[1])}`],
    [/^(\d+(?:\.\d+)?)(mg|mcg|g|IU|ml|%)$/, (m) => `${m[1]} ${{ mg: "میلی‌گرم", mcg: "میکروگرم", g: "گرم", IU: "واحد", ml: "میلی‌لیتر", "%": "درصد" }[m[2]]}`],
    [/^(Updated|checked|Last updated|Last confirmed) (.+?)(\. .*)?$/, (m) => ({ Updated: "به‌روزرسانی", checked: "بررسی", "Last updated": "آخرین به‌روزرسانی", "Last confirmed": "آخرین تأیید" }[m[1]]) + " " + ago(m[2]) + (m[3] ? ". " + tr(m[3].slice(2)) : "")],
    [/^This listing hasn't been confirmed in over (\d+) hours\. Call before you go\.$/, (m) => `این مورد بیش از ${m[1]} ساعت است تأیید نشده. پیش از رفتن تماس بگیرید.`],
    [/^Stock changes quickly, so call before you travel\.$/, () => "موجودی سریع تغییر می‌کند؛ پیش از رفتن تماس بگیرید."],
    [/^(.+) away$/, (m) => `${tr(m[1])} فاصله`],
    [/^Go to shop$/, () => "رفتن به فروشگاه"],
    [/^Maximum distance in kilometres$/, () => "حداکثر فاصله به کیلومتر"],
  ];

  function tr(s) {
    const t = s.trim();
    if (!t) return s;
    let out = D[t];
    if (out === undefined) for (const [re, fn] of P) { const m = t.match(re); if (m) { out = fn(m); break; } }
    if (out === undefined) { const a = ago(t); out = a !== t ? a : undefined; }
    return out === undefined ? s : s.replace(t, out);
  }
  const FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹";
  const digits = (s) => s.replace(/\d/g, (d) => FA_DIGITS[d]);

  const ATTRS = ["placeholder", "aria-label", "title", "alt"];
  const SKIP = new Set(["SCRIPT", "STYLE", "TEXTAREA", "CODE"]);
  function node(n) {
    if (n.nodeType === 3) {
      const p = n.parentNode;
      if (!p || SKIP.has(p.nodeName) || (p.closest && p.closest("[data-nofa]"))) return;
      const t = tr(n.nodeValue);
      const v = /[A-Za-z]/.test(t) ? t : digits(t);
      if (v !== n.nodeValue) n.nodeValue = v;
    } else if (n.nodeType === 1 && !SKIP.has(n.nodeName)) {
      for (const a of ATTRS) if (n.hasAttribute(a)) { const v = tr(n.getAttribute(a)); if (v !== n.getAttribute(a)) n.setAttribute(a, v); }
      n.childNodes.forEach(node);
    }
  }
  function start() {
    const fixTitle = () => { const t = document.title.replace(/\s*[·|:-]\s*MedFind$/, " · مدفایند"); const v = tr(t); if (v !== document.title) document.title = v; };
    fixTitle();
    const tEl = document.querySelector("title");
    if (tEl) new MutationObserver(fixTitle).observe(tEl, { childList: true });
    node(document.body);
    new MutationObserver((ms) => {
      for (const m of ms) {
        if (m.type === "characterData") node(m.target);
        else if (m.type === "attributes") node(m.target);
        else m.addedNodes.forEach(node);
      }
    }).observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS });
  }

  window.I18N = {
    lang,
    t: (en, vars) => { let s = en; if (vars) for (const k in vars) s = s.replace("{" + k + "}", vars[k]); return digits(tr(s)); },
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
