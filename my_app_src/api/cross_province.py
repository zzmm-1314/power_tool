from flask import Blueprint, request
from utils.response import success, fail
from io import BytesIO
import pandas as pd
from datetime import datetime
import traceback

cross_bp = Blueprint("cross_province", __name__)


def excel_date_col_to_datetime(col):
    if isinstance(col, (pd.Timestamp, datetime)):
        return pd.to_datetime(col).normalize()
    try:
        v = float(str(col).strip())
        return pd.to_datetime(v, unit="D", origin="1899-12-30").normalize()
    except Exception:
        return pd.to_datetime(col, errors="coerce").normalize()


def hour_to_period(h):
    if pd.isna(h):
        return pd.NA
    h = int(h)
    return f"{h:02d}:00-{h + 1:02d}:00"


@cross_bp.post("/upload")
def upload_and_process():
    file = request.files.get("file")
    if not file:
        return fail("未接收到上传文件")

    try:
        file_bytes = file.read()
        file_stream = BytesIO(file_bytes)

        # 1. 读取成交数据
        trade = pd.read_excel(file_stream, sheet_name="成交数据", engine="openpyxl")
        original_cols = list(trade.columns)

        pattern = r"^E(\d{2})(\d{2})(\d{2})\.(\d{2})H$"
        ext = trade["标的代码"].astype(str).str.extract(pattern)

        date_str = (
            "20" + ext[0].fillna("") + "-" + ext[1].fillna("") + "-" + ext[2].fillna("")
        )
        trade["日期"] = pd.to_datetime(date_str, errors="coerce")

        trade["小时"] = pd.to_numeric(ext[3], errors="coerce").astype("Int64")
        trade["时间"] = trade["小时"].apply(hour_to_period)

        trade["成交数量（MW）"] = pd.to_numeric(
            trade["成交数量（MW）"], errors="coerce"
        )
        buy_mask = trade["成交类型"].astype(str).str.strip().eq("购电")
        trade.loc[buy_mask, "成交数量（MW）"] = -trade.loc[
            buy_mask, "成交数量（MW）"
        ].abs()

        trade["成交价（元/MWh）"] = pd.to_numeric(
            trade["成交价（元/MWh）"], errors="coerce"
        )

        # 2. 读取日前价格
        price = None
        try:
            file_stream.seek(0)
            price = pd.read_excel(file_stream, sheet_name="日前价格", engine="openpyxl")
        except Exception:
            pass

        if price is None or price.empty:
            return fail(
                "未找到日前价格数据（请确保上传的 Excel 中包含名为 '日前价格' 的 Sheet）"
            )

        first_col = price.columns[0]
        price = price.rename(columns={first_col: "时间"})
        new_cols = ["时间"] + [excel_date_col_to_datetime(c) for c in price.columns[1:]]
        price.columns = new_cols
        price["时间"] = (
            price["时间"].astype(str).str.replace("：", ":", regex=False).str.strip()
        )

        price_long = price.melt(
            id_vars="时间", var_name="日期", value_name="日前价格（元/MWh）"
        )
        price_long["日期"] = pd.to_datetime(
            price_long["日期"], errors="coerce"
        ).dt.normalize()
        price_long["日前价格（元/MWh）"] = pd.to_numeric(
            price_long["日前价格（元/MWh）"], errors="coerce"
        )
        price_long = price_long.dropna(subset=["日期", "日前价格（元/MWh）"])

        # 3. 匹配并计算
        result = trade.merge(price_long, on=["日期", "时间"], how="left")
        result["价差（元/MWh）"] = (
            result["成交价（元/MWh）"] - result["日前价格（元/MWh）"]
        )
        result["价差金额（元）"] = result["价差（元/MWh）"] * result["成交数量（MW）"]

        # 处理日期序列化
        if "日期" in result.columns:
            result["日期"] = result["日期"].dt.strftime("%Y-%m-%d")

        out_cols = original_cols + [
            "日期",
            "时间",
            "日前价格（元/MWh）",
            "价差（元/MWh）",
            "价差金额（元）",
        ]
        out_cols = [c for c in out_cols if c in result.columns]
        result = result[out_cols]

        # 4. 极其关键的防错：将 DataFrame 转为 JSON 兼容格式（剔除 NaN 和 numpy 专属类型）
        # 否则 Flask 的 jsonify 会因为 NaN 报 500 错误
        records = result.to_dict(orient="records")
        clean_records = []
        for rec in records:
            clean_rec = {}
            for k, v in rec.items():
                if pd.isna(v):
                    clean_rec[k] = None
                elif isinstance(v, pd.Timestamp):
                    clean_rec[k] = v.strftime("%Y-%m-%d")
                else:
                    clean_rec[k] = v
            clean_records.append(clean_rec)

        return success(clean_records)

    except Exception as e:
        # 打印详细堆栈到终端
        traceback.print_exc()
        # 把真实错误信息返回给前端
        return fail(f"解析异常: {str(e)}")
