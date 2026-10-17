"""Persian/Arabic text and price helpers (pure functions)."""
import re
from decimal import Decimal

_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_LETTERS = str.maketrans({"ي": "ی", "ك": "ک", "ۀ": "ه", "ة": "ه", "‌": " ", "‏": "", "‎": ""})
_FA = re.compile(r"[؀-ۿ]")
_LATIN_RUN = re.compile(r"[A-Za-z][A-Za-z0-9 .,%/+\-()]*[A-Za-z0-9%)]")


def digits(s: str) -> str:
    return str(s).translate(_DIGITS)


def norm(s: str) -> str:
    """Canonical form for comparing names: Latin digits, one Persian ya/kaf, no ZWNJ, single spaces."""
    return " ".join(digits(s).translate(_LETTERS).split())


def has_persian(s: str) -> bool:
    return bool(_FA.search(s or ""))


def split_title(title: str) -> tuple[str | None, str | None]:
    """'استامینوفن 500 میلی گرم Acetaminophen 500mg' -> ('Acetaminophen 500mg', persian_title).
    Returns (english_name or None, persian_alias or None)."""
    t = norm(title)
    runs = [m.group(0).strip() for m in _LATIN_RUN.finditer(t)]
    english = max(runs, key=len) if runs else None
    if english and len(re.findall(r"[A-Za-z]", english)) < 3:
        english = None
    persian = t if has_persian(t) else None
    return english, persian


def to_toman(price, currency: str | None) -> Decimal | None:
    """Iranian shops quote in Rial or Toman. Normalise everything to Toman."""
    if price is None:
        return None
    cur = (currency or "").strip().lower()
    if cur in ("irr", "rial", "rials", "ریال", "﷼"):
        return (Decimal(price) / 10).quantize(Decimal("1"))
    return Decimal(price)
