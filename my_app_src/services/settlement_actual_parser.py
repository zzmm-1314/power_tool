import openpyxl
import os
from utils.dates import extract_date_from_cell_value


def parse_settlement_actual(file_path):
    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        ws = wb.active

        date_val = ws["B4"].value
        d = extract_date_from_cell_value(date_val)
        if not d:
            return None

        res = {
            "date": d.strftime("%Y-%m-%d"),
            "online_qty": None,
            "da_qty": None,
            "da_price": None,
            "da_fee": None,
            "rt_qty": None,
            "rt_price": None,
            "rt_fee": None,
            "cs_qty": None,
            "cs_price": None,
            "cs_fee": None,
            "year_qty": None,
            "year_price": None,
            "year_fee": None,
            "month_qty": None,
            "month_price": None,
            "month_fee": None,
            "intraday_qty": None,
            "intraday_price": None,
            "intraday_fee": None,
            "total_fee": None,
        }

        for row in ws.iter_rows(values_only=True):
            if not row or len(row) < 3:
                continue
            col_b = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
            col_c = str(row[2]).strip() if len(row) > 2 and row[2] is not None else ""
            col_d = str(row[3]).strip() if len(row) > 3 and row[3] is not None else ""

            def _get_val(idx):
                if idx < len(row):
                    v = row[idx]
                    try:
                        return float(v)
                    except (ValueError, TypeError):
                        return None
                return None

            if "上网电量" in col_b:
                res["online_qty"] = _get_val(2)
            elif "日前市场" in col_c:
                res["da_qty"] = _get_val(4)
                res["da_price"] = _get_val(6)
                res["da_fee"] = _get_val(8)
            elif "实时市场" in col_c:
                res["rt_qty"] = _get_val(4)
                res["rt_price"] = _get_val(6)
                res["rt_fee"] = _get_val(8)
            elif "长三角D-3日跨省滚动撮合" in col_d:
                res["cs_qty"] = _get_val(4)
                res["cs_price"] = _get_val(6)
                res["cs_fee"] = _get_val(8)
            elif "年度集中合约" in col_d:
                res["year_qty"] = _get_val(4)
                res["year_price"] = _get_val(6)
                res["year_fee"] = _get_val(8)
            elif "月度集中合约" in col_d:
                res["month_qty"] = _get_val(4)
                res["month_price"] = _get_val(6)
                res["month_fee"] = _get_val(8)
            elif "日内滚撮合约" in col_d:
                res["intraday_qty"] = _get_val(4)
                res["intraday_price"] = _get_val(6)
                res["intraday_fee"] = _get_val(8)
            elif "合计" in col_c:
                res["total_fee"] = _get_val(8)

        wb.close()
        return res
    except Exception as e:
        print(f"解析失败: {e}")
        return None
