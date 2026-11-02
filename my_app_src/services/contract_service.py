import os
import calendar
import re
from datetime import datetime
import openpyxl
import pandas as pd

# 基础路径（合同配置属于正式业务数据，存放于 data/contract）
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "contract"
)
BASE_DIR = os.path.join(DATA_DIR, "base")
NODES_DIR = os.path.join(DATA_DIR, "nodes")


def ensure_dirs():
    os.makedirs(BASE_DIR, exist_ok=True)
    os.makedirs(NODES_DIR, exist_ok=True)


def save_uploaded_file(file_obj, save_path):
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    file_obj.save(save_path)


def _get_date_type(year: int, month: int, day: int, holiday_set: set) -> str:
    date_str = f"{year}-{month:02d}-{day:02d}"
    if date_str in holiday_set:
        return "法定节假日"
    weekday = datetime(year, month, day).weekday()
    if weekday == 5:
        return "周六"
    elif weekday == 6:
        return "周日"
    else:
        return "工作日"


def _load_typical_curve_from_file(file_path: str) -> dict:
    """解析本地文件"""
    curves = {}
    if not os.path.exists(file_path):
        return curves
    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        ws = wb.worksheets[0]
        rows = list(ws.iter_rows(values_only=True))

        current_month = None
        is_day_weight = False
        is_hour_weight = False

        for idx, row in enumerate(rows):
            row_str = "".join(
                [str(c).replace("\n", "").strip() for c in row if c is not None]
            )
            if not row_str:
                continue

            month_match = re.search(r"(\d+)\s*月-月分日权重比", row_str)
            if month_match:
                current_month = int(month_match.group(1))
                curves[current_month] = {"日权重": {}, "分时权重": {}}
                is_day_weight = True
                is_hour_weight = False
                continue

            if re.search(r"\d+\s*月-日分时权重比", row_str):
                is_day_weight = False
                is_hour_weight = True
                continue

            if not current_month:
                continue

            if is_day_weight and "日期类型" in row_str:
                if idx + 1 < len(rows):
                    weight_row = rows[idx + 1]
                    if weight_row and weight_row[0] and "日权重" in str(weight_row[0]):

                        def safe_get_val(r, i, default=1.0):
                            return float(r[i] or default) if i < len(r) else default

                        curves[current_month]["日权重"] = {
                            "工作日": safe_get_val(weight_row, 1),
                            "周六": safe_get_val(weight_row, 2),
                            "周日": safe_get_val(weight_row, 3),
                            "法定节假日": safe_get_val(weight_row, 4, 0.0),
                        }

            if is_hour_weight and any(
                ":" in str(c) and str(c)[0].isdigit() for c in row if c
            ):
                try:
                    w_work = float(row[1] or 0) if len(row) > 1 else 0
                    w_sat = float(row[2] or 0) if len(row) > 2 else 0
                    w_sun = float(row[3] or 0) if len(row) > 3 else 0
                    w_hol = float(row[4] or 0) if len(row) > 4 else 0

                    curves[current_month]["分时权重"].setdefault("工作日", []).append(
                        w_work
                    )
                    curves[current_month]["分时权重"].setdefault("周六", []).append(
                        w_sat
                    )
                    curves[current_month]["分时权重"].setdefault("周日", []).append(
                        w_sun
                    )
                    curves[current_month]["分时权重"].setdefault(
                        "法定节假日", []
                    ).append(w_hol)
                except Exception:
                    pass
        wb.close()
    except Exception as e:
        print(f"解析 Excel 失败: {e}")
    return curves


def _load_holidays_from_file(file_path: str) -> set:
    holiday_set = set()
    if not os.path.exists(file_path):
        return holiday_set
    try:
        df = pd.read_excel(file_path)
        if "日期" in df.columns:
            for val in df["日期"]:
                if pd.notna(val):
                    holiday_set.add(pd.to_datetime(val).strftime("%Y-%m-%d"))
    except Exception as e:
        print(f"解析节假日失败: {e}")
    return holiday_set


def generate_contract_decomposition(
    year: int,
    month: int,
    qty_year: float,
    qty_month: float,
    qty_tenday1: float,
    qty_tenday2: float,
    qty_tenday3: float,
) -> dict:
    """纯根据本地基础配置进行分解计算"""
    ensure_dirs()
    curve_path = os.path.join(BASE_DIR, "typical_curve.xlsx")
    holiday_path = os.path.join(BASE_DIR, "holidays.xlsx")

    if not os.path.exists(curve_path):
        raise ValueError("未找到典型曲线，请先在「设置-中长期合约配置」中上传")

    typical_curves = _load_typical_curve_from_file(curve_path)
    holiday_set = _load_holidays_from_file(holiday_path)

    month_data = typical_curves.get(month)

    # 如果当前月没有数据，且是 12 月，则自动降级参考 11 月的系数
    if not month_data and month == 12:
        month_data = typical_curves.get(11)
        if month_data:
            print(
                "[ContractService] 提示：典型曲线中未找到 12 月的数据，已自动参考 11 月的分解系数。"
            )

    if not month_data:
        raise ValueError(f"典型曲线中未找到 {month} 月的数据")

    num_days = calendar.monthrange(year, month)[1]

    def pad_weights(w_list):
        if not w_list:
            return [1 / 48.0] * 48
        if len(w_list) >= 48:
            return w_list[:48]
        return w_list + [0.0] * (48 - len(w_list))

    days_info = []
    for d in range(1, num_days + 1):
        d_type = _get_date_type(year, month, d, holiday_set)
        weight = month_data["日权重"].get(d_type, 1.0)
        hour_weights = pad_weights(month_data["分时权重"].get(d_type))
        if sum(hour_weights) == 0:
            hour_weights = [1 / 48.0] * 48

        days_info.append(
            {
                "day": d,
                "date": f"{month:02d}-{d:02d}",
                "day_type": d_type,
                "weight": weight,
                "hour_weights": hour_weights,
            }
        )

    days_tenday1 = [info for info in days_info if 1 <= info["day"] <= 10]
    days_tenday2 = [info for info in days_info if 11 <= info["day"] <= 20]
    days_tenday3 = [info for info in days_info if 21 <= info["day"] <= num_days]

    def build_period_data(total_qty, period_days):
        if not period_days or total_qty == 0:
            return []
        total_w = sum(info["weight"] for info in period_days) or len(period_days)
        res = []
        for info in period_days:
            daily_qty = total_qty * (info["weight"] / total_w)
            points = [daily_qty * info["hour_weights"][i] for i in range(48)]
            res.append(
                {
                    "date": info["date"],
                    "day_type": info["day_type"],
                    "daily_qty": daily_qty,
                    "points": points,
                }
            )
        return res

    times = [f"{i//2:02d}:{(i%2)*30:02d}" for i in range(48)]
    return {
        "times": times,
        "year": build_period_data(qty_year, days_info),
        "month": build_period_data(qty_month, days_info),
        "tenday1": build_period_data(qty_tenday1, days_tenday1),
        "tenday2": build_period_data(qty_tenday2, days_tenday2),
        "tenday3": build_period_data(qty_tenday3, days_tenday3),
    }
