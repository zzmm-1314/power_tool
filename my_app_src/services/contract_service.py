import os
import calendar
import re
from datetime import datetime
import openpyxl
import pandas as pd
import json
from services.db_store import fetch_contract_config
from utils.logger import get_logger

logger = get_logger("services.contract_service")

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

            if is_hour_weight:
                try:
                    # 直接读取第 2 列到第 5 列的值，不依赖 A 列的时间格式
                    w_work = float(row[1]) if len(row) > 1 and pd.notna(row[1]) else 0
                    w_sat = float(row[2]) if len(row) > 2 and pd.notna(row[2]) else 0
                    w_sun = float(row[3]) if len(row) > 3 and pd.notna(row[3]) else 0
                    w_hol = float(row[4]) if len(row) > 4 and pd.notna(row[4]) else 0

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
                except (ValueError, TypeError):
                    # 遇到表头等非数字行会自动跳过
                    pass
        wb.close()
    except Exception as e:
        logger.warning(f"解析 Excel 失败: {e}")
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
        logger.warning(f"解析节假日失败: {e}")
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
    """完全根据数据库配置进行分解计算"""
    ensure_dirs()

    # 1. 完全从数据库读取 JSON 配置
    db_curve_json = fetch_contract_config("typical_curve")
    if not db_curve_json:
        raise ValueError("数据库中未找到典型曲线，请先在「中长期合约配置」中上传")

    try:
        raw_curves = json.loads(db_curve_json)
        # 因为 JSON 的 key 都是字符串，需要转回 int
        typical_curves = {int(k): v for k, v in raw_curves.items()}
    except Exception as e:
        raise ValueError(f"解析数据库中的典型曲线失败: {e}")

    holiday_set = set()
    db_holiday_json = fetch_contract_config("holidays")
    if db_holiday_json:
        try:
            holiday_set = set(json.loads(db_holiday_json))
        except Exception as e:
            logger.warning(f"解析数据库中的节假日失败: {e}")

    # 2. 获取对应月份数据
    month_data = typical_curves.get(month)
    if not month_data and month == 12:
        month_data = typical_curves.get(11)
        if month_data:
            logger.info(
                "[ContractService] 提示：典型曲线中未找到 12 月的数据，已自动参考 11 月的分解系数。"
            )

    if not month_data:
        raise ValueError(f"典型曲线中未找到 {month} 月的数据")

    num_days = calendar.monthrange(year, month)[1]

    # 3. 构建每日基础数据
    days_info = []
    for d in range(1, num_days + 1):
        d_type = _get_date_type(year, month, d, holiday_set)
        weight = month_data["日权重"].get(d_type, 1.0)

        # 获取原始分时权重
        hour_weights = month_data["分时权重"].get(d_type, [])

        # 确保有 48 个点，如果不足（比如数据库里存了 47 个），剩余补 0（严格遵循系数）
        if not hour_weights:
            hour_weights = [1 / 48.0] * 48
        elif len(hour_weights) < 48:
            hour_weights = hour_weights + [0.0] * (48 - len(hour_weights))
        else:
            hour_weights = hour_weights[:48]

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
            # 严格依据系数生成 48 个点
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

    # ⭐ 4. 生成标准时间轴：00:30 ~ 24:00
    times = []
    for i in range(48):
        h = (i + 1) // 2
        m = 30 if (i % 2 == 0) else 0
        times.append("24:00" if i == 47 else f"{h:02d}:{m:02d}")

    return {
        "times": times,
        "year": build_period_data(qty_year, days_info),
        "month": build_period_data(qty_month, days_info),
        "tenday1": build_period_data(qty_tenday1, days_tenday1),
        "tenday2": build_period_data(qty_tenday2, days_tenday2),
        "tenday3": build_period_data(qty_tenday3, days_tenday3),
    }
