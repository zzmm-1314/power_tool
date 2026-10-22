"""日期工具（原 独立工具 dates.py 迁入）"""

import re
from datetime import datetime


def extract_date_from_filename(filename):
    m = re.search(r"(\d{4})年(\d{2})月(\d{2})日", filename)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", filename)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def extract_date_from_cell_value(cell_value):
    if cell_value is None:
        return None
    if isinstance(cell_value, datetime):
        return cell_value.date()
    if isinstance(cell_value, (int, float)):
        try:
            from openpyxl.utils.datetime import from_excel

            return from_excel(cell_value).date()
        except Exception:
            from datetime import timedelta

            base = datetime(1899, 12, 30).date()
            return base + timedelta(days=int(cell_value))
    if isinstance(cell_value, str):
        m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", cell_value)
        if m:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
        m = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", cell_value)
        if m:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
    return None


def normalize_date(date_str):
    if re.match(r"\d{4}-\d{2}-\d{2}", date_str):
        return date_str
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_str)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return date_str


def parse_sheet_name_date(name):
    s = str(name).strip()
    for pat in [
        r"^(\d{1,2})\.(\d{1,2})$",
        r"^(\d{1,2})月(\d{1,2})日?$",
        r"^(\d{4})-(\d{1,2})-(\d{1,2})$",
        r"^(\d{4})\.(\d{1,2})\.(\d{1,2})$",
    ]:
        m = re.match(pat, s)
        if m:
            groups = m.groups()
            return int(groups[-2]), int(groups[-1])
    return None


def get_month_days(date_obj):
    if date_obj.month == 2:
        if (date_obj.year % 4 == 0 and date_obj.year % 100 != 0) or (
            date_obj.year % 400 == 0
        ):
            return 29
        return 28
    if date_obj.month in [4, 6, 9, 11]:
        return 30
    return 31


def get_annual_contract_row(date_obj):
    days_in_month = get_month_days(date_obj)
    base_row = 34 + (days_in_month - 28)
    return base_row + (date_obj.day - 1)


def get_tenday_value(date_obj, tenday_prices):
    day = date_obj.day
    if day <= 10:
        return tenday_prices[0]
    if day <= 20:
        return tenday_prices[1]
    return tenday_prices[2]
