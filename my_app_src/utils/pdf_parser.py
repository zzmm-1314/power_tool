"""PDF 结算单解析工具：从 pdfplumber 表格中提取月报字段"""

import os
import re
from typing import Dict, List

import pdfplumber

# ==================== 字段定义 ====================
FIELDS_META = {
    "plant_name": "电厂名称",
    "company_name": "发电企业名称",
    "account_number": "户号",
    "report_month": "报告月份",
    "actual_online_energy": "实际上网电量(MWh)",
    "settlement_price": "结算均价(元/MWh)",
    "settlement_fee": "结算电费(元)",
    "settlement_fee_wan": "结算电费(万元)",
    "settlement_fee_cn": "结算电费大写",
    "contract_energy": "合同电量(MWh)",
    "medium_long_term_energy": "中长期合约电量(MWh)",
    "medium_long_term_ratio": "中长期合约占比",
    "spot_total_fee_wan": "现货日前+实时电费(万元)",
    "energy_clearing_total_wan": "电量清分项合计(万元)",
    "energy_clearing_plan_energy": "电量清分-计划电量(MWh)",
    "energy_clearing_settlement_energy": "电量清分-结算电量(MWh)",
    "energy_clearing_plan_price": "电量清分-电价(元/MWh)",
    "energy_clearing_price": "电量清分-电价(元/MWh)(模板用)",
    "energy_clearing_fee": "电量清分-电费(元)",
    "other_direct_plan_energy": "其他电力直接交易-计划电量(MWh)",
    "other_direct_settlement_energy": "其他电力直接交易-结算电量(MWh)",
    "other_direct_price": "其他电力直接交易-电价(元/MWh)",
    "other_direct_fee": "其他电力直接交易-电费(元)",
    "day_ahead_plan_energy": "日前交易-计划电量(MWh)",
    "day_ahead_settlement_energy": "日前交易-结算电量(MWh)",
    "day_ahead_price": "日前交易-电价(元/MWh)",
    "day_ahead_fee": "日前交易-电费(元)",
    "real_time_plan_energy": "实时交易-计划电量(MWh)",
    "real_time_settlement_energy": "实时交易-结算电量(MWh)",
    "real_time_price": "实时交易-电价(元/MWh)",
    "real_time_fee": "实时交易-电费(元)",
    "rights_clearing_energy": "权益凭证类-结算电量(MWh)",
    "rights_clearing_price": "权益凭证类-电价(元/MWh)",
    "rights_clearing_fee": "权益凭证类-电费(元)",
    "cost_compensation_energy": "成本补偿-结算电量(MWh)",
    "cost_compensation_price": "成本补偿-电价(元/MWh)",
    "cost_compensation_fee": "成本补偿-电费(元)",
    "other_market_energy": "其他市场运营-结算电量(MWh)",
    "other_market_price": "其他市场运营-电价(元/MWh)",
    "other_market_et_price": "其他市场运营-电价(元/MWh)(模板旧拼写)",
    "other_market_fee": "其他市场运营-电费(元)",
    "demand_response_energy": "需求侧响应-结算电量(MWh)",
    "demand_response_price": "需求侧响应-电价(元/MWh)",
    "demand_response_fee": "需求侧响应-电费(元)",
    "demand_respons_energy": "需求侧响应-结算电量(MWh)(模板旧拼写)",
    "demand_respons_price": "需求侧响应-电价(元/MWh)(模板旧拼写)",
    "demand_respons_fee": "需求侧响应-电费(元)(模板旧拼写)",
    "ultra_low_emission_energy": "超低排放-结算电量(MWh)",
    "ultra_low_emission_price": "超低排放-电价(元/MWh)",
    "ultra_low_emission_fee": "超低排放-电费(元)",
    "total_settlement_energy": "合计-结算电量(MWh)",
    "total_settlement_price": "合计-结算电价(元/MWh)",
    "total_settlement_fee": "合计-结算电费(元)",
    "year_cumulative_online_energy": "年累计抄表电量(MWh)",
    "year_cumulative_contract_energy": "年累计合约电量(MWh)",
    "day_ahead_energy": "日前电能-结算电量(MWh)",
    "real_time_energy": "实时电能-结算电量(MWh)",
    "adjust_energy": "调整电量(MWh)",
    "adjust_price": "调整电量-电价(元/MWh)",
    "adjust_fee": "调整电量-电费(元)",
    "contract_market_energy": "合约市场-电量(MWh)",
    "contract_market_price": "合约市场-电价(元/MWh)",
    "contract_market_fee": "合约市场-电费(元)",
    "frequency_regulation_fee": "辅助服务调频(元)",
    "excess_profit_recovery": "超额获利回收(元)",
    "fixed_diff_compensation_energy": "固定差价补偿-电量(MWh)",
    "fixed_diff_compensation_price": "固定差价补偿-电价(元/MWh)",
    "fixed_diff_compensation_fee": "固定差价补偿-电费(元)",
    "total_energy": "月合计-电量(MWh)",
    "total_price": "月合计-电价(元/MWh)",
    "total_fee": "月合计-电费(元)",
    "year_day_ahead_energy": "年累计-日前电能-电量(MWh)",
    "year_day_ahead_price": "年累计-日前电能-电价(元/MWh)",
    "year_day_ahead_fee": "年累计-日前电能-电费(元)",
    "year_real_time_energy": "年累计-实时电能-电量(MWh)",
    "year_real_time_price": "年累计-实时电能-电价(元/MWh)",
    "year_real_time_fee": "年累计-实时电能-电费(元)",
    "year_adjust_energy": "年累计-调整电量(MWh)",
    "year_adjust_price": "年累计-调整电量-电价(元/MWh)",
    "year_adjust_fee": "年累计-调整电量-电费(元)",
    "year_monthly_auction_energy": "年累计-月度集中竞价-电量(MWh)",
    "year_monthly_auction_price": "年累计-月度集中竞价-电价(元/MWh)",
    "year_monthly_auction_fee": "年累计-月度集中竞价-电费(元)",
    "year_annual_auction_energy": "年累计-年度集中竞价-电量(MWh)",
    "year_annual_auction_price": "年累计-年度集中竞价-电价(元/MWh)",
    "year_annual_auction_fee": "年累计-年度集中竞价-电费(元)",
    "year_intraday_energy": "年累计-日内滚撮-电量(MWh)",
    "year_intraday_price": "年累计-日内滚撮-电价(元/MWh)",
    "year_intraday_fee": "年累计-日内滚撮-电费(元)",
    "year_cross_province_energy": "年累计-长三角D-3日跨省滚动撮合-电量(MWh)",
    "year_cross_province_price": "年累计-长三角D-3日跨省滚动撮合-电价(元/MWh)",
    "year_cross_province_fee": "年累计-长三角D-3日跨省滚动撮合-电费(元)",
    "year_total_energy": "年累计-合计-电量(MWh)",
    "year_total_price": "年累计-合计-电价(元/MWh)",
    "year_total_fee": "年累计-合计-电费(元)",
}

INTERNAL_FIELDS = [
    "settlement_energy",
    "monthly_auction_energy",
    "monthly_auction_price",
    "monthly_auction_fee",
    "annual_auction_energy",
    "annual_auction_price",
    "annual_auction_fee",
    "intraday_energy",
    "intraday_price",
    "intraday_fee",
    "year_fixed_diff_compensation_energy",
    "year_fixed_diff_compensation_price",
    "year_fixed_diff_compensation_fee",
]


class StringWithCN(str):
    """支持 {{settlement_fee.cn}} 的字符串子类"""

    def __new__(cls, value, cn_value=""):
        obj = super().__new__(cls, str(value))
        obj.cn = cn_value
        return obj


# ==================== 基础工具 ====================

_settings_candidates = [
    {"vertical_strategy": "lines", "horizontal_strategy": "lines"},
    {"vertical_strategy": "lines", "horizontal_strategy": "text"},
    {"vertical_strategy": "text", "horizontal_strategy": "text"},
]


def normalize(v):
    return str(v or "").replace("\n", "").strip()


def cell_text(v):
    if v is None:
        return ""
    return normalize(v)


def to_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def _extract_page_tables(page):
    for s in _settings_candidates:
        s = {
            **s,
            "snap_tolerance": 3,
            "join_tolerance": 3,
            "intersection_tolerance": 5,
        }
        tables = page.extract_tables(table_settings=s)
        if tables:
            return tables
    return []


def build_sheets(pdf_path: str) -> Dict[str, List]:
    sheets = {}
    with pdfplumber.open(pdf_path) as pdf:
        for pno, page in enumerate(pdf.pages, start=1):
            for tno, table in enumerate(_extract_page_tables(page), start=1):
                sheets[f"P{pno}_T{tno}"] = table
    return sheets


def detect_table_type(table):
    if not table:
        return None
    head_text = "".join(normalize(c) for row in table[:5] for c in row)
    if "实际上网电量" in head_text and "结算电费" in head_text:
        return "summary"
    if "结算科目" in head_text and "分月交易计划电量" in head_text:
        return "detail"
    if (
        "抄表电量" in head_text
        and "合约电量" in head_text
        and "结算科目" not in head_text
    ):
        return "meter"
    if "结算项目明细" in head_text and "结算电量/容量" in head_text:
        if "年累计" in head_text and "本月" not in head_text:
            return "year"
        return "month"
    return None


def find_header_row(table, keywords):
    for i, row in enumerate(table):
        line = "".join(normalize(c) for c in row)
        if all(kw in line for kw in keywords):
            return i
    return None


def build_col_map(table, header_idx):
    col_map = {}
    if header_idx is None:
        return col_map
    for j, c in enumerate(table[header_idx]):
        name = normalize(c)
        if name:
            col_map[name] = j
    return col_map


def get_val(table, row_idx, col_idx):
    if row_idx is None or col_idx is None:
        return ""
    if row_idx >= len(table) or col_idx >= len(table[row_idx]):
        return ""
    return cell_text(table[row_idx][col_idx])


def find_row_exact(table, label, label_cols=(0, 1), start_row=0):
    for i, row in enumerate(table):
        if i < start_row:
            continue
        for c in label_cols:
            if c < len(row) and normalize(row[c]) == label:
                return i
    return None


def find_row_contains(table, keyword, label_cols=(0, 1), start_row=0):
    for i, row in enumerate(table):
        if i < start_row:
            continue
        for c in label_cols:
            if c < len(row) and keyword in normalize(row[c]):
                return i
    return None


# ==================== 各类表格提取 ====================


def extract_summary(table, data):
    header_idx = find_header_row(table, ["实际上网电量", "结算电费"])
    if header_idx is None:
        return
    col_map = build_col_map(table, header_idx)
    month_idx = find_row_exact(table, "本月", start_row=header_idx + 1)
    if month_idx is not None:
        for field, col_name in [
            ("actual_online_energy", "实际上网电量"),
            ("settlement_energy", "结算电量"),
            ("contract_energy", "合同电量"),
            ("settlement_fee", "结算电费"),
        ]:
            if col_name in col_map:
                data[field] = get_val(table, month_idx, col_map[col_name])
    cn_idx = find_row_contains(table, "大写金额", label_cols=(0,))
    if cn_idx is not None:
        for cell in table[cn_idx]:
            n = normalize(cell)
            if (
                n
                and "大写" not in n
                and "金额" not in n
                and any("\u4e00" <= ch <= "\u9fa5" for ch in n)
            ):
                m = re.match(r"^.*?分", n)
                data["settlement_fee_cn"] = m.group(0) if m else n
                break


def extract_meter(table, data):
    for i, row in enumerate(table):
        norm_row = [normalize(c) for c in row]

        if "抄表电量" in norm_row and len(row) > 2:
            v = get_val(table, i, 2)
            if v:
                data["year_cumulative_online_energy"] = v

        if "合约电量" in norm_row and len(row) > 2:
            v = get_val(table, i, 2)
            if v:
                data["year_cumulative_contract_energy"] = v

        for j, c in enumerate(row):
            n = normalize(c)
            if "发电企业名称" in n and j + 1 < len(row):
                v = normalize(row[j + 1])
                if v and v != "户号":
                    data["company_name"] = v
            if n == "户号" and j + 1 < len(row):
                v = normalize(row[j + 1])
                if v:
                    data["account_number"] = v


def extract_detail(table, data):
    header_idx = find_header_row(table, ["结算科目", "分月交易计划电量"])
    if header_idx is None:
        return
    col_map = build_col_map(table, header_idx)
    subject_col = col_map.get("结算科目", 1)
    plan_col = col_map.get("分月交易计划电量")
    energy_col = col_map.get("结算电量/容量")
    price_col = col_map.get("结算电价/均价")
    fee_col = col_map.get("结算电费")
    year_plan_col = col_map.get("年累计交易计划电量") or col_map.get("年累计交易电量")
    year_energy_col = col_map.get("年累计结算电量")

    def find_subject(name):
        return find_row_contains(
            table, name, label_cols=(subject_col,), start_row=header_idx + 1
        )

    r = find_subject("电量清分")
    if r is not None:
        data["energy_clearing_plan_energy"] = get_val(table, r, plan_col)
        data["energy_clearing_settlement_energy"] = get_val(table, r, energy_col)
        data["energy_clearing_plan_price"] = get_val(table, r, price_col)
        data["energy_clearing_fee"] = get_val(table, r, fee_col)
    r = find_subject("其他电力直接交易")
    if r is not None:
        data["other_direct_plan_energy"] = get_val(table, r, plan_col)
        data["other_direct_settlement_energy"] = get_val(table, r, energy_col)
        data["other_direct_price"] = get_val(table, r, price_col)
        data["other_direct_fee"] = get_val(table, r, fee_col)
    r = find_subject("日前交易")
    if r is not None:
        data["day_ahead_plan_energy"] = get_val(table, r, plan_col)
        data["day_ahead_settlement_energy"] = get_val(table, r, energy_col)
        data["day_ahead_price"] = get_val(table, r, price_col)
        data["day_ahead_fee"] = get_val(table, r, fee_col)
    r = find_subject("实时交易")
    if r is not None:
        data["real_time_plan_energy"] = get_val(table, r, plan_col)
        data["real_time_settlement_energy"] = get_val(table, r, energy_col)
        data["real_time_price"] = get_val(table, r, price_col)
        data["real_time_fee"] = get_val(table, r, fee_col)
    r = find_subject("权益凭证类")
    if r is not None:
        data["rights_clearing_energy"] = get_val(table, r, energy_col)
        data["rights_clearing_price"] = get_val(table, r, price_col)
        data["rights_clearing_fee"] = get_val(table, r, fee_col)
    r = find_subject("成本补偿")
    if r is not None:
        data["cost_compensation_energy"] = get_val(table, r, energy_col)
        data["cost_compensation_price"] = get_val(table, r, price_col)
        data["cost_compensation_fee"] = get_val(table, r, fee_col)
    r = find_subject("其他市场运营费用")
    if r is not None:
        data["other_market_energy"] = get_val(table, r, energy_col)
        data["other_market_price"] = get_val(table, r, price_col)
        data["other_market_fee"] = get_val(table, r, fee_col)
    r = find_subject("需求侧响应")
    if r is not None:
        data["demand_response_energy"] = get_val(table, r, energy_col)
        data["demand_response_price"] = get_val(table, r, price_col)
        data["demand_response_fee"] = get_val(table, r, fee_col)
    r = find_subject("超低排放")
    if r is not None:
        data["ultra_low_emission_energy"] = get_val(table, r, energy_col)
        data["ultra_low_emission_price"] = get_val(table, r, price_col)
        data["ultra_low_emission_fee"] = get_val(table, r, fee_col)
    r = find_row_exact(table, "合计", label_cols=(0, 1, 2), start_row=header_idx + 1)
    if r is not None:
        data["total_settlement_energy"] = get_val(table, r, energy_col)
        data["total_settlement_price"] = get_val(table, r, price_col)
        data["total_settlement_fee"] = get_val(table, r, fee_col)
        data["total_energy"] = get_val(table, r, energy_col)
        data["total_price"] = get_val(table, r, price_col)
        data["total_fee"] = get_val(table, r, fee_col)
        if not data["year_cumulative_online_energy"]:
            data["year_cumulative_online_energy"] = get_val(table, r, year_energy_col)
        if not data["year_cumulative_contract_energy"]:
            data["year_cumulative_contract_energy"] = get_val(table, r, year_plan_col)


def extract_month(table, data):
    header_idx = find_header_row(table, ["结算电量/容量", "结算费用"])
    if header_idx is None:
        return
    col_map = build_col_map(table, header_idx)
    energy_col = col_map.get("结算电量/容量")
    price_col = col_map.get("电价")
    fee_col = col_map.get("结算费用")

    def row_of(label):
        return find_row_contains(
            table, label, label_cols=(0, 1), start_row=header_idx + 1
        )

    def row_eq(label):
        return find_row_exact(table, label, label_cols=(0, 1), start_row=header_idx + 1)

    r = row_eq("日前电能")
    if r is not None:
        data["day_ahead_energy"] = get_val(table, r, energy_col)
        data["day_ahead_settlement_energy"] = data["day_ahead_energy"]
        data["day_ahead_price"] = get_val(table, r, price_col)
        data["day_ahead_fee"] = get_val(table, r, fee_col)
    r = row_eq("实时电能")
    if r is not None:
        data["real_time_energy"] = get_val(table, r, energy_col)
        data["real_time_settlement_energy"] = data["real_time_energy"]
        data["real_time_price"] = get_val(table, r, price_col)
        data["real_time_fee"] = get_val(table, r, fee_col)
    r = row_eq("调整电量")
    if r is not None:
        data["adjust_energy"] = get_val(table, r, energy_col)
        data["adjust_price"] = get_val(table, r, price_col)
        data["adjust_fee"] = get_val(table, r, fee_col)
    r = row_of("月度集中竞价直接交易")
    if r is not None:
        data["monthly_auction_energy"] = get_val(table, r, energy_col)
        data["monthly_auction_price"] = get_val(table, r, price_col)
        data["monthly_auction_fee"] = get_val(table, r, fee_col)
    r = row_of("年度集中竞价直接交易")
    if r is not None:
        data["annual_auction_energy"] = get_val(table, r, energy_col)
        data["annual_auction_price"] = get_val(table, r, price_col)
        data["annual_auction_fee"] = get_val(table, r, fee_col)
    r = row_of("日内滚撮")
    if r is not None:
        data["intraday_energy"] = get_val(table, r, energy_col)
        data["intraday_price"] = get_val(table, r, price_col)
        data["intraday_fee"] = get_val(table, r, fee_col)
    r = row_of("超额获利回收")
    if r is not None:
        data["excess_profit_recovery"] = get_val(table, r, fee_col)
    r = row_of("调频")
    if r is not None:
        data["frequency_regulation_fee"] = get_val(table, r, fee_col)
    r = row_of("固定差价费用补偿")
    if r is not None:
        data["fixed_diff_compensation_energy"] = get_val(table, r, energy_col)
        data["fixed_diff_compensation_price"] = get_val(table, r, price_col)
        data["fixed_diff_compensation_fee"] = get_val(table, r, fee_col)
    r = row_eq("月合计")
    if r is not None:
        data["total_settlement_energy"] = get_val(table, r, energy_col)
        data["total_settlement_price"] = get_val(table, r, price_col)
        data["total_settlement_fee"] = get_val(table, r, fee_col)
        data["total_energy"] = get_val(table, r, energy_col)
        data["total_price"] = get_val(table, r, price_col)
        data["total_fee"] = get_val(table, r, fee_col)


def extract_year(table, data):
    header_idx = find_header_row(table, ["结算电量/容量", "结算费用"])
    if header_idx is None:
        return
    col_map = build_col_map(table, header_idx)
    energy_col = col_map.get("结算电量/容量")
    price_col = col_map.get("电价")
    fee_col = col_map.get("结算费用")

    def row_of(label):
        return find_row_contains(
            table, label, label_cols=(0, 1), start_row=header_idx + 1
        )

    def row_eq(label):
        return find_row_exact(table, label, label_cols=(0, 1), start_row=header_idx + 1)

    pairs = [
        ("日前电能", "year_day_ahead", "eq"),
        ("实时电能", "year_real_time", "eq"),
        ("调整电量", "year_adjust", "eq"),
        ("月度集中竞价直接交易", "year_monthly_auction", "of"),
        ("年度集中竞价直接交易", "year_annual_auction", "of"),
        ("日内滚撮", "year_intraday", "of"),
        ("长三角", "year_cross_province", "of"),
        ("固定差价费用补偿", "year_fixed_diff_compensation", "of"),
    ]
    for label, prefix, mode in pairs:
        r = row_eq(label) if mode == "eq" else row_of(label)
        if r is not None:
            data[f"{prefix}_energy"] = get_val(table, r, energy_col)
            data[f"{prefix}_price"] = get_val(table, r, price_col)
            data[f"{prefix}_fee"] = get_val(table, r, fee_col)
    r = row_eq("年合计")
    if r is not None:
        data["year_total_energy"] = get_val(table, r, energy_col)
        data["year_total_price"] = get_val(table, r, price_col)
        data["year_total_fee"] = get_val(table, r, fee_col)


# ==================== 主入口 ====================


def extract_data(sheets, pdf_path: str) -> Dict:
    data = {k: "" for k in FIELDS_META.keys()}
    for k in INTERNAL_FIELDS:
        data[k] = ""

    fname = os.path.basename(pdf_path or "")
    m = re.search(r"(\d{4}年\d{1,2}月)", fname)
    if m:
        data["report_month"] = m.group(1)
        plant = fname[: m.start()].strip("-_ ")
        if plant:
            data["plant_name"] = plant

    for _name, table in sheets.items():
        ttype = detect_table_type(table)
        if ttype == "summary":
            extract_summary(table, data)
        elif ttype == "meter":
            extract_meter(table, data)
        elif ttype == "detail":
            extract_detail(table, data)
        elif ttype == "month":
            extract_month(table, data)
        elif ttype == "year":
            extract_year(table, data)

    print(
        f"[PDF] plant={data.get('plant_name')} month={data.get('report_month')} "
        f"company={data.get('company_name')} account={data.get('account_number')}"
    )

    # 别名
    data["energy_clearing_price"] = data.get("energy_clearing_plan_price", "")
    data["day_ahead_energy"] = data.get("day_ahead_energy") or data.get(
        "day_ahead_settlement_energy", ""
    )
    data["real_time_energy"] = data.get("real_time_energy") or data.get(
        "real_time_settlement_energy", ""
    )
    data["other_market_et_price"] = data.get("other_market_price", "")
    data["demand_respons_energy"] = data.get("demand_response_energy", "")
    data["demand_respons_price"] = data.get("demand_response_price", "")
    data["demand_respons_fee"] = data.get("demand_response_fee", "")

    # 合约市场合计
    me = (
        to_float(data["monthly_auction_energy"])
        + to_float(data["annual_auction_energy"])
        + to_float(data["intraday_energy"])
    )
    mf = (
        to_float(data["monthly_auction_fee"])
        + to_float(data["annual_auction_fee"])
        + to_float(data["intraday_fee"])
    )
    if me != 0:
        data["contract_market_energy"] = f"{me:.3f}"
        data["contract_market_fee"] = f"{mf:.2f}"
        data["contract_market_price"] = f"{mf / me:.3f}"

    # 结算均价
    if not data["settlement_price"] and data["total_settlement_price"]:
        data["settlement_price"] = data["total_settlement_price"]

    # 结算电费万元
    if data["settlement_fee"]:
        try:
            data["settlement_fee_wan"] = (
                f"{float(data['settlement_fee']) / 10000:.2f}万元"
            )
        except Exception:
            pass

    # 中长期合约
    ml = data.get("energy_clearing_plan_energy", "")
    se = data.get("settlement_energy") or data.get("total_settlement_energy", "")
    if ml:
        data["medium_long_term_energy"] = ml
        if se:
            try:
                ratio = float(ml) / float(se) * 100
                data["medium_long_term_ratio"] = f"{ratio:.2f}%"
            except Exception:
                pass

    # 现货电费（万元）
    spot = to_float(data.get("day_ahead_fee")) + to_float(data.get("real_time_fee"))
    if spot:
        data["spot_total_fee_wan"] = f"{spot / 10000:.2f}万元"

    # 电量清分（万元）
    ec = to_float(data.get("energy_clearing_fee"))
    if ec:
        data["energy_clearing_total_wan"] = f"{ec / 10000:.2f}万元"

    # 兼容 {{settlement_fee.cn}}
    data["settlement_fee"] = StringWithCN(
        data.get("settlement_fee", ""),
        data.get("settlement_fee_cn", ""),
    )

    return data
