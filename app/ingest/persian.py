"""Persian/English helpers for Iranian pharmacy pages: digit and letter
normalisation, a drug-name dictionary (Persian -> English generic), strength
and dosage-form detection, and Toman/Rial price handling."""
import re

_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize(text: str) -> str:
    """ASCII digits, Persian ی/ک, no zero-width joiners (so 'آموکسی‌سیلین' == 'آموکسی سیلین')."""
    t = str(text or "").translate(_DIGITS)
    t = t.replace("ي", "ی").replace("ك", "ک").replace("‌", " ").replace("‏", "")
    t = t.replace("٬", ",").replace("٫", ".").replace("٪", "%")
    return re.sub(r"\s+", " ", t).strip()


# Persian generic/ingredient name -> English. Longer keys are tried first.
FA_EN = {
    "پاراستامول": "Paracetamol", "استامینوفن": "Paracetamol", "ایبوپروفن": "Ibuprofen", "آسپرین": "Aspirin",
    "ناپروکسن": "Naproxen", "دیکلوفناک": "Diclofenac", "ایندومتاسین": "Indomethacin", "پیروکسیکام": "Piroxicam",
    "ملوکسیکام": "Meloxicam", "سلکوکسیب": "Celecoxib", "کلشی سین": "Colchicine", "آلوپورینول": "Allopurinol",
    "آموکسی سیلین": "Amoxicillin", "آموکسیسیلین": "Amoxicillin", "آمپی سیلین": "Ampicillin", "پنی سیلین": "Penicillin",
    "آزیترومایسین": "Azithromycin", "کلاریترومایسین": "Clarithromycin", "سفکسیم": "Cefixime", "سفالکسین": "Cephalexin",
    "سیپروفلوکساسین": "Ciprofloxacin", "کوتریموکسازول": "Co-trimoxazole", "مترونیدازول": "Metronidazole",
    "داکسی سایکلین": "Doxycycline", "دوکسی سایکلین": "Doxycycline", "کلیندامایسین": "Clindamycin",
    "فلوکونازول": "Fluconazole", "نیستاتین": "Nystatin", "کتوکونازول": "Ketoconazole", "کلوتریمازول": "Clotrimazole",
    "آسیکلوویر": "Acyclovir", "امپرازول": "Omeprazole", "اومپرازول": "Omeprazole", "پانتوپرازول": "Pantoprazole",
    "رانیتیدین": "Ranitidine", "فاموتیدین": "Famotidine", "دومپریدون": "Domperidone", "متوکلوپرامید": "Metoclopramide",
    "اندانسترون": "Ondansetron", "لوپرامید": "Loperamide", "بیزاکودیل": "Bisacodyl", "سیمتیکون": "Simethicone",
    "ستیریزین": "Cetirizine", "لوراتادین": "Loratadine", "دیفن هیدرامین": "Diphenhydramine", "فکسوفنادین": "Fexofenadine",
    "کلرفنیرامین": "Chlorpheniramine", "سالبوتامول": "Salbutamol", "مونتلوکاست": "Montelukast", "مونته لوکاست": "Montelukast",
    "پردنیزولون": "Prednisolone", "دگزامتازون": "Dexamethasone", "هیدروکورتیزون": "Hydrocortisone", "بتامتازون": "Betamethasone",
    "متفورمین": "Metformin", "گلی بن کلامید": "Glibenclamide", "گلیبنکلامید": "Glibenclamide", "گلیمپیراید": "Glimepiride",
    "گلیکلازید": "Gliclazide", "سیتاگلیپتین": "Sitagliptin", "انسولین": "Insulin", "آتورواستاتین": "Atorvastatin",
    "سیمواستاتین": "Simvastatin", "روزواستاتین": "Rosuvastatin", "لوزارتان": "Losartan", "والسارتان": "Valsartan",
    "آملودیپین": "Amlodipine", "آتنولول": "Atenolol", "متوپرولول": "Metoprolol", "پروپرانولول": "Propranolol",
    "کارودیلول": "Carvedilol", "کاپتوپریل": "Captopril", "انالاپریل": "Enalapril", "لیزینوپریل": "Lisinopril",
    "هیدروکلروتیازید": "Hydrochlorothiazide", "فوروزماید": "Furosemide", "اسپیرونولاکتون": "Spironolactone",
    "وارفارین": "Warfarin", "کلوپیدوگرل": "Clopidogrel", "ریواروکسابان": "Rivaroxaban", "دیگوکسین": "Digoxin",
    "نیتروگلیسیرین": "Nitroglycerin", "لووتیروکسین": "Levothyroxine", "سرترالین": "Sertraline", "فلوکستین": "Fluoxetine",
    "سیتالوپرام": "Citalopram", "اسیتالوپرام": "Escitalopram", "آمی تریپتیلین": "Amitriptyline", "آلپرازولام": "Alprazolam",
    "دیازپام": "Diazepam", "کلونازپام": "Clonazepam", "لورازپام": "Lorazepam", "زولپیدم": "Zolpidem", "ملاتونین": "Melatonin",
    "گاباپنتین": "Gabapentin", "پرگابالین": "Pregabalin", "کاربامازپین": "Carbamazepine", "والپروات": "Valproate",
    "لاموتریژین": "Lamotrigine", "لوتیراستام": "Levetiracetam", "ریسپریدون": "Risperidone", "الانزاپین": "Olanzapine",
    "اولانزاپین": "Olanzapine", "کوئتیاپین": "Quetiapine", "هالوپریدول": "Haloperidol", "ترامادول": "Tramadol",
    "کدئین": "Codeine", "مورفین": "Morphine", "آلندرونات": "Alendronate", "سیلدنافیل": "Sildenafil", "تادالافیل": "Tadalafil",
    "تامسولوسین": "Tamsulosin", "فیناستراید": "Finasteride", "لووناژسترل": "Levonorgestrel", "ایزوترتینوئین": "Isotretinoin",
    "کلرهگزیدین": "Chlorhexidine", "بتادین": "Betadine", "سرم نمکی": "Normal Saline", "اسید فولیک": "Folic Acid",
    "فروس سولفات": "Ferrous Sulfate", "ویتامین د": "Vitamin D", "ویتامین ث": "Vitamin C", "ویتامین ای": "Vitamin E",
    "ویتامین ب": "Vitamin B", "مولتی ویتامین": "Multivitamin", "امگا 3": "Omega-3", "کلسیم": "Calcium", "منیزیم": "Magnesium",
    "زینک": "Zinc", "آهن": "Iron",
}
EN_FA = {}
for _fa, _en in FA_EN.items():
    EN_FA.setdefault(_en.lower(), _fa)
_KEYS = sorted((normalize(k) for k in FA_EN), key=len, reverse=True)
_FA_EN_N = {normalize(k): v for k, v in FA_EN.items()}

FORMS = {"قرص": "Tablet", "کپسول": "Capsule", "شربت": "Syrup", "آمپول": "Injection", "قطره": "Drops",
         "کرم": "Cream", "پماد": "Ointment", "ژل": "Gel", "اسپری": "Spray", "ساشه": "Sachet", "شیاف": "Suppository",
         "پودر": "Powder", "محلول": "Solution", "سوسپانسیون": "Suspension"}
STRENGTH_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(میلی ?گرم|میکروگرم|mg|mcg|µg|گرم|g|واحد|iu|میلی ?لیتر|ml|%)(?![a-z])", re.I)
UNIT = {"میلی گرم": "mg", "میلیگرم": "mg", "mg": "mg", "میکروگرم": "mcg", "mcg": "mcg", "µg": "mcg", "گرم": "g", "g": "g",
        "واحد": "IU", "iu": "IU", "میلی لیتر": "ml", "میلیلیتر": "ml", "ml": "ml", "%": "%"}


def analyze_title(title: str) -> dict:
    """-> {generic, strength, form, name_en}; every value may be None."""
    t = normalize(title)
    low = t.lower()
    generic = next((_FA_EN_N[k] for k in _KEYS if k in t), None)
    if generic is None:  # English generic written in Latin letters
        for en in sorted(EN_FA, key=len, reverse=True):
            if re.search(r"\b" + re.escape(en) + r"\b", low):
                generic = en.title() if en not in ("co-trimoxazole",) else "Co-trimoxazole"
                break
    m = STRENGTH_RE.search(t)
    strength = f"{m.group(1)}{UNIT.get(m.group(2).lower().replace('  ', ' '), m.group(2))}" if m else None
    form = next((v for k, v in FORMS.items() if k in t), None)
    if form is None:
        form = next((f for f in FORMS.values() if f.lower() in low), None)
    if generic:
        name_en = " ".join(x for x in (generic, strength, form) if x)
    else:
        latin = " ".join(re.findall(r"[A-Za-z][A-Za-z0-9\-\.%/ ]{2,}", t)).strip()
        name_en = latin[:200] or None
    return {"generic": generic, "strength": strength, "form": form, "name_en": name_en}


def search_terms(q: str) -> list[str]:
    """Expand a query across English and Persian so either finds either."""
    n = normalize(q)
    terms = {n.lower()}
    for en, fa in EN_FA.items():
        if en in n.lower():
            terms.add(normalize(fa))
    for fa, en in _FA_EN_N.items():
        if fa in n:
            terms.add(en.lower())
    return [t for t in terms if t]


def to_toman(price, currency):
    """Iranian sites publish Rial (IRR/ریال) or Toman (IRT/تومان). Store Toman."""
    if price is None:
        return None, None
    c = (currency or "").upper()
    if c in ("IRR", "RIAL", "ریال"):
        return price / 10, "IRT"
    if c in ("IRT", "TOMAN", "تومان", "IRHT"):
        return price, "IRT"
    return price, (currency or None)
