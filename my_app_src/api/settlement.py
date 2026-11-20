"""结算单更新 API 蓝图"""

import os
from flask import Blueprint, request
import shutil
from services.settlement.general_builder import build_general_data
from services.settlement import start_task, get_task
from utils.response import success, fail

settlement_bp = Blueprint("settlement", __name__)

# 合约电量五个组成部分
_CONTRACT_PARTS = ("year", "month", "tenday1", "tenday2", "tenday3")


def _as_bool(value) -> bool:
    """开关值转布尔：兼容 true/"true"/1/"on" 等写法"""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in ("1", "true", "yes", "y", "on")


def _is_decompose(value) -> bool:
    """判断某项是否为「调用合约分解」。

    同时接受布尔值/0-1 与 'decompose' 字符串（前端直接传来源名）。
    """
    if isinstance(value, str) and value.strip().lower() in ("decompose", "database"):
        return value.strip().lower() == "decompose"
    return _as_bool(value)


def _parse_contract_sources(params: dict) -> dict:
    """解析五项合约电量开关 → {'year': 'decompose'|'database', ...}

    勾选（True）表示调用合约分解接口，未勾选表示取数据库已录入。
    兼容两种传参：
    - contract_sources: {"year": true, "month": false, ...}
    - 扁平字段 contract_year / contract_month / contract_tenday1/2/3
    兼容旧参数 year_source：仍按原值决定五项（仅在未传新开关时生效）。
    """
    nested = params.get("contract_sources") or params.get("contractSources")
    nested = nested if isinstance(nested, dict) else {}

    legacy = params.get("year_source") or params.get("yearSource")
    legacy_default = (
        None if legacy is None else ("decompose" if legacy == "decompose" else "database")
    )

    sources = {}
    for part in _CONTRACT_PARTS:
        raw = nested.get(part)
        if raw is None:
            raw = params.get(f"contract_{part}")
        if raw is None:
            sources[part] = legacy_default or "database"
        else:
            sources[part] = "decompose" if _is_decompose(raw) else "database"
    return sources


@settlement_bp.post("/start/<task_type>")
def start(task_type: str):
    # ⭐ 统一使用 simulate 处理
    if task_type not in ("actual", "simulate"):
        return fail(f"不支持的任务类型: {task_type}")

    data = request.get_json(silent=True) or {}
    params = data.get("params") or {}

    node_name = params.get("node_name") or params.get("nodeName")
    start_date = params.get("start_date") or params.get("startDate")
    end_date = params.get("end_date") or params.get("endDate")

    qty_year = float(params.get("qty_year", 0) or 0)
    qty_month = float(params.get("qty_month", 0) or 0)
    qty_tenday1 = float(params.get("qty_tenday1", 0) or 0)
    qty_tenday2 = float(params.get("qty_tenday2", 0) or 0)
    qty_tenday3 = float(params.get("qty_tenday3", 0) or 0)
    if task_type == "simulate":
        if not node_name or not start_date or not end_date:
            return fail("需要参数 node_name, start_date, end_date")
        try:
            # 五项合约电量开关：勾选=调用合约分解接口，未勾选=取数据库
            contract_sources = _parse_contract_sources(params)
            # 调用通用引擎
            gen_data = build_general_data(
                node_name,
                start_date,
                end_date,
                qty_year,
                qty_month,
                qty_tenday1,
                qty_tenday2,
                qty_tenday3,
                contract_sources=contract_sources,
            )
            # 将数据塞入 params，供 sim_v2 渲染
            params["spot_data"] = gen_data["spot"]
            params["stat_data"] = gen_data["stat"]
            params["strategy_month_data"] = gen_data["strategy_month"]
            params["strategy_tenday_data"] = gen_data["strategy_tenday"]
            params["info_spot_day_data"] = gen_data["info_spot_day"]
            params["info_spot_rt_data"] = gen_data["info_spot_rt"]
            params["info_contract_data"] = gen_data["info_contract"]

            # 任务类型转为 general 给 task_runner 执行 v2 渲染引擎
            task_type = "general"
        except Exception as e:
            import traceback

            traceback.print_exc()
            return fail(f"内存生成数据失败: {e}")

    # 路径校验
    required = {
        "actual": ["folder", "target_file"],
        "general": [
            "target_file",
            "annual_price",
            "monthly_price",
            "tenday_early",
            "tenday_mid",
            "tenday_late",
        ],
    }[task_type]

    for k in required:
        v = params.get(k)
        if v is None or (isinstance(v, str) and not v.strip()):
            return fail(f"缺少参数 {k}")

    for k in required:
        if k.endswith("_file"):
            p = params[k]
            if isinstance(p, str) and not os.path.isfile(p):
                return fail(f"文件不存在: {p}")
        elif k == "folder":
            p = params["folder"]
            if isinstance(p, str) and not os.path.isdir(p):
                return fail(f"文件夹不存在: {p}")

    try:
        task_id = start_task(task_type, params)
    except Exception as e:
        return fail(f"启动失败: {e}")

    return success({"taskId": task_id}, msg="任务已启动")


@settlement_bp.get("/tasks/<task_id>")
def task_status(task_id: str):
    task = get_task(task_id)
    if not task:
        return fail("任务不存在", code=404), 404
    return success(task)


@settlement_bp.post("/browse-file")
def browse_file():
    """弹出系统文件选择对话框（需要 GUI 环境）"""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title="选择 Excel 文件",
            filetypes=[("Excel 文件", "*.xlsx *.xls"), ("所有文件", "*.*")],
        )
        root.destroy()
        return success({"path": path or ""})
    except Exception as e:
        return fail(f"弹出文件对话框失败：{e}（可能无 GUI 环境）")


@settlement_bp.post("/browse-folder")
def browse_folder():
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askdirectory(title="选择文件夹")
        root.destroy()
        return success({"path": path or ""})
    except Exception as e:
        return fail(f"弹出文件夹对话框失败：{e}（可能无 GUI 环境）")


@settlement_bp.get("/declaration-template")
def download_declaration_template():
    """下载 48 点申报电量模板：48 行（时段）× 31 列（每月每天）"""
    import pandas as pd
    from io import BytesIO
    from flask import send_file
    from openpyxl.styles import Font, Alignment
    from openpyxl.utils import get_column_letter

    # 48 个时段标签，与 sim_v2 / _common 一致：00:30 ~ 24:00
    time_labels = []
    for i in range(48):
        if i == 47:
            time_labels.append("24:00")
        else:
            h = (i + 1) // 2
            mi = 30 if (i % 2 == 0) else 0
            time_labels.append(f"{h:02d}:{mi:02d}")

    # 表头：时段 | 1日 | 2日 | ... | 31日
    headers = ["时段"] + [f"{d}日" for d in range(1, 32)]

    # 数据：48 行 × 32 列（第 1 列时段，其余 31 天初始 0）
    data = [[t] + [0.0] * 31 for t in time_labels]

    df = pd.DataFrame(data, columns=headers)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="申报电量")
        ws = writer.sheets["申报电量"]

        # 列宽
        ws.column_dimensions["A"].width = 10
        for col in range(2, 33):
            ws.column_dimensions[get_column_letter(col)].width = 10

        # 冻结首行首列，方便填写
        ws.freeze_panes = "B2"

        # 表头加粗
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center")

    output.seek(0)
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="48点申报电量模板.xlsx",
    )


@settlement_bp.post("/actual/upload")
def upload_actual_settlement():
    node_name = request.form.get("node_name")
    files = request.files.getlist("files")
    if not node_name or not files:
        return fail("缺少节点或未选择文件")

    from services.settlement_actual_parser import parse_settlement_actual
    from services.db_store import save_settlement_actual
    import tempfile, os

    records = []
    for f in files:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        f.save(tmp.name)
        tmp.close()
        try:
            res = parse_settlement_actual(tmp.name)
            if res:
                res["node_name"] = node_name
                records.append(res)
        finally:
            if os.path.exists(tmp.name):
                os.remove(tmp.name)

    if not records:
        return fail("未解析出有效数据，请检查文件格式或B4日期")

    try:
        save_settlement_actual(records)
    except Exception as e:
        return fail(f"入库失败: {e}")

    return success(msg=f"成功入库 {len(records)} 天的数据")


@settlement_bp.get("/actual/records")
def get_actual_records():
    node_name = request.args.get("node_name")
    if not node_name:
        return fail("缺少节点名")
    from services.db_store import fetch_settlement_actual

    records = fetch_settlement_actual(node_name)
    return success(records)


@settlement_bp.get("/actual/export")
def export_actual_records():
    node_name = request.args.get("node_name")
    month = (request.args.get("month") or "").strip()
    try:
        compensation = float(request.args.get("compensation", 153.515))
    except (TypeError, ValueError):
        compensation = 153.515

    if not node_name:
        return fail("缺少节点名")

    from services.db_store import fetch_settlement_actual
    import pandas as pd
    from io import BytesIO
    from flask import send_file

    records = fetch_settlement_actual(node_name)
    if not records:
        return fail("无数据可导出")

    # 按月过滤
    if month:
        records = [r for r in records if str(r.get("date", "")).startswith(month)]
    if not records:
        return fail("该月份无数据可导出")

    # 按日期排序
    records = sorted(records, key=lambda r: str(r.get("date", "")))

    # 数值安全转换
    def _f(v):
        try:
            return float(v) if v is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    # 计算衍生字段
    enriched = []
    cumulative = 0.0
    for r in records:
        online_qty = _f(r.get("online_qty"))
        total_fee = _f(r.get("total_fee"))
        da_qty = _f(r.get("da_qty"))
        da_price = _f(r.get("da_price"))
        da_fee = _f(r.get("da_fee"))
        rt_qty = _f(r.get("rt_qty"))
        rt_price = _f(r.get("rt_price"))
        rt_fee = _f(r.get("rt_fee"))

        settlement_price = total_fee / online_qty if online_qty != 0 else 0.0
        spot_fee = da_fee + rt_fee
        spot_profit = rt_qty * (rt_price - da_price)
        cumulative += spot_profit

        enriched.append(
            {
                "date": str(r.get("date", "")),
                "online_qty": online_qty,
                "total_fee": total_fee,
                "settlement_price": settlement_price,
                "da_qty": da_qty,
                "da_price": da_price,
                "da_fee": da_fee,
                "rt_qty": rt_qty,
                "rt_price": rt_price,
                "rt_fee": rt_fee,
                "spot_fee": spot_fee,
                "spot_profit": spot_profit,
                "cumulative_profit": cumulative,
                "year_qty": _f(r.get("year_qty")),
                "year_price": _f(r.get("year_price")),
                "year_fee": _f(r.get("year_fee")),
                "month_qty": _f(r.get("month_qty")),
                "month_price": _f(r.get("month_price")),
                "month_fee": _f(r.get("month_fee")),
                "intraday_qty": _f(r.get("intraday_qty")),
                "intraday_price": _f(r.get("intraday_price")),
                "intraday_fee": _f(r.get("intraday_fee")),
                "cs_qty": _f(r.get("cs_qty")),
                "cs_price": _f(r.get("cs_price")),
                "cs_fee": _f(r.get("cs_fee")),
            }
        )

    # 汇总计算
    count = len(enriched)

    def _sum(key):
        return sum(item[key] for item in enriched)

    def _avg(key):
        return _sum(key) / count if count > 0 else 0.0

    total_online_qty = _sum("online_qty")
    total_fee_sum = _sum("total_fee")
    avg_settlement_price = (
        total_fee_sum / total_online_qty if total_online_qty != 0 else 0.0
    )

    # 差价补偿 & 含补贴
    comp_qty = total_online_qty * 0.45
    comp_price = compensation
    comp_fee = comp_qty * comp_price

    with_sub_qty = total_online_qty
    with_sub_fee = total_fee_sum + comp_fee
    with_sub_price = with_sub_fee / with_sub_qty if with_sub_qty != 0 else 0.0

    # ============ 概览 Sheet ============
    overview_rows = []
    for item in enriched:
        overview_rows.append(
            {
                "日期": item["date"],
                "结算电量": round(item["online_qty"], 3),
                "结算均价": round(item["settlement_price"], 3),
                "结算电费": round(item["total_fee"], 2),
            }
        )
    overview_rows.append(
        {
            "日期": "合计",
            "结算电量": round(total_online_qty, 3),
            "结算均价": round(avg_settlement_price, 3),
            "结算电费": round(total_fee_sum, 2),
        }
    )
    overview_rows.append(
        {
            "日期": "固定差价补偿",
            "结算电量": round(comp_qty, 3),
            "结算均价": round(comp_price, 3),
            "结算电费": round(comp_fee, 2),
        }
    )
    overview_rows.append(
        {
            "日期": "含补贴均价",
            "结算电量": round(with_sub_qty, 3),
            "结算均价": round(with_sub_price, 3),
            "结算电费": round(with_sub_fee, 2),
        }
    )
    overview_df = pd.DataFrame(overview_rows)

    # ============ 详细 Sheet ============
    detail_rows = []
    for item in enriched:
        detail_rows.append(
            {
                "日期": item["date"],
                "实际电量": round(item["online_qty"], 3),
                "日前电量": round(item["da_qty"], 3),
                "实时电量": round(item["rt_qty"], 3),
                "日前结算均价": round(item["da_price"], 3),
                "日前结算费用": round(item["da_fee"], 2),
                "实时结算均价": round(item["rt_price"], 3),
                "实时结算费用": round(item["rt_fee"], 2),
                "现货收益结算费用": round(item["spot_fee"], 2),
                "现货相对日前曲线盈亏": round(item["spot_profit"], 2),
                "现货累计盈亏": round(item["cumulative_profit"], 2),
                "年度集中合约电量": round(item["year_qty"], 3),
                "年度集中合约电价": round(item["year_price"], 3),
                "年度集中合约费用": round(item["year_fee"], 2),
                "月度集中合约电量": round(item["month_qty"], 3),
                "月度集中合约电价": round(item["month_price"], 3),
                "月度集中合约费用": round(item["month_fee"], 2),
                "日内滚撮电量": round(item["intraday_qty"], 3),
                "日内滚撮电价": round(item["intraday_price"], 3),
                "日内滚撮费用": round(item["intraday_fee"], 2),
                "省间滚撮电量": round(item["cs_qty"], 3),
                "省间滚撮电价": round(item["cs_price"], 3),
                "省间滚撮费用": round(item["cs_fee"], 2),
            }
        )
    detail_rows.append(
        {
            "日期": "汇总",
            "实际电量": round(_sum("online_qty"), 3),
            "日前电量": round(_sum("da_qty"), 3),
            "实时电量": round(_sum("rt_qty"), 3),
            "日前结算均价": round(_avg("da_price"), 3),
            "日前结算费用": round(_sum("da_fee"), 2),
            "实时结算均价": round(_avg("rt_price"), 3),
            "实时结算费用": round(_sum("rt_fee"), 2),
            "现货收益结算费用": round(_sum("spot_fee"), 2),
            "现货相对日前曲线盈亏": round(_sum("spot_profit"), 2),
            "现货累计盈亏": (
                round(enriched[-1]["cumulative_profit"], 2) if enriched else 0.0
            ),
            "年度集中合约电量": round(_sum("year_qty"), 3),
            "年度集中合约电价": round(_avg("year_price"), 3),
            "年度集中合约费用": round(_sum("year_fee"), 2),
            "月度集中合约电量": round(_sum("month_qty"), 3),
            "月度集中合约电价": round(_avg("month_price"), 3),
            "月度集中合约费用": round(_sum("month_fee"), 2),
            "日内滚撮电量": round(_sum("intraday_qty"), 3),
            "日内滚撮电价": round(_avg("intraday_price"), 3),
            "日内滚撮费用": round(_sum("intraday_fee"), 2),
            "省间滚撮电量": round(_sum("cs_qty"), 3),
            "省间滚撮电价": round(_avg("cs_price"), 3),
            "省间滚撮费用": round(_sum("cs_fee"), 2),
        }
    )
    detail_df = pd.DataFrame(detail_rows)

    # ============ 写入 Excel ============
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        overview_df.to_excel(writer, index=False, sheet_name="概览")
        detail_df.to_excel(writer, index=False, sheet_name="详细")
    out.seek(0)

    filename = (
        f"实际结算单_{node_name}_{month}.xlsx"
        if month
        else f"实际结算单_{node_name}.xlsx"
    )
    return send_file(
        out,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


@settlement_bp.get("/actual/query")
def query_actual_comparison():
    month = request.args.get("month")
    nodes_str = request.args.get("nodes", "")
    if not month or not nodes_str:
        return fail("缺少月份或节点参数")

    node_list = [n.strip() for n in nodes_str.split(",") if n.strip()]
    if not node_list:
        return fail("节点列表为空")

    from services.db_store import fetch_settlement_actual, fetch_official_prices

    # 补偿参数，默认153.515
    try:
        compensation = float(request.args.get("compensation", 153.515))
    except (TypeError, ValueError):
        compensation = 153.515

    official_prices = fetch_official_prices(month)

    def _f(v):
        try:
            return float(v) if v is not None else 0.0
        except:
            return 0.0

    results = []
    for node in node_list:
        # 一次性取出该节点所有数据，按月份过滤
        all_records = fetch_settlement_actual(node)
        # ⭐ 计算最新日期
        latest_date = ""
        if all_records:
            dates = [str(r.get("date", "")) for r in all_records if r.get("date")]
            if dates:
                latest_date = max(dates)
        records = [r for r in all_records if str(r.get("date", "")).startswith(month)]
        if not records:
            # 节点没数据，也给一行留空占位
            results.append(
                {
                    "node": node,
                    "latestDate": latest_date,  # ⭐ 新增
                    "barePrice": 0,
                    "settlementPrice": 0,
                    "officialPrice": official_prices.get(node),
                    "yearFee": 0,
                    "monthFee": 0,
                    "intradayFee": 0,
                    "intradayBuyQty": 0,
                    "intradayBuyPrice": 0,
                    "intradaySellQty": 0,
                    "intradaySellPrice": 0,
                    "spotProfit": 0,
                    "csFee": 0,
                    "csBuyQty": 0,
                    "csBuyPrice": 0,
                    "csSellQty": 0,
                    "csSellPrice": 0,
                    "diff": 0,
                }
            )
            continue

        # 初始化聚合数据
        sum_online_qty = 0.0
        sum_total_fee = 0.0
        sum_year_fee = 0.0
        sum_month_fee = 0.0
        sum_intraday_fee = 0.0

        intraday_buy_qty = 0.0
        intraday_buy_fee = 0.0
        intraday_sell_qty = 0.0
        intraday_sell_fee = 0.0

        spot_profit = 0.0
        sum_cs_fee = 0.0

        cs_buy_qty = 0.0
        cs_buy_fee = 0.0
        cs_sell_qty = 0.0
        cs_sell_fee = 0.0

        for r in records:
            online_qty = _f(r.get("online_qty"))
            total_fee = _f(r.get("total_fee"))
            sum_online_qty += online_qty
            sum_total_fee += total_fee

            sum_year_fee += _f(r.get("year_fee"))
            sum_month_fee += _f(r.get("month_fee"))

            i_qty = _f(r.get("intraday_qty"))
            i_fee = _f(r.get("intraday_fee"))
            sum_intraday_fee += i_fee
            if i_qty < 0:
                intraday_buy_qty += i_qty
                intraday_buy_fee += i_fee
            elif i_qty > 0:
                intraday_sell_qty += i_qty
                intraday_sell_fee += i_fee

            da_qty = _f(r.get("da_qty"))
            da_price = _f(r.get("da_price"))
            rt_qty = _f(r.get("rt_qty"))
            rt_price = _f(r.get("rt_price"))
            spot_profit += rt_qty * (rt_price - da_price)

            sum_cs_fee += _f(r.get("cs_fee"))
            c_qty = _f(r.get("cs_qty"))
            c_fee = _f(r.get("cs_fee"))
            if c_qty < 0:
                cs_buy_qty += c_qty
                cs_buy_fee += c_fee
            elif c_qty > 0:
                cs_sell_qty += c_qty
                cs_sell_fee += c_fee

        # 计算均价
        bare_price = sum_total_fee / sum_online_qty if sum_online_qty != 0 else 0.0
        comp_fee = sum_online_qty * 0.45 * compensation
        settlement_price = (
            (sum_total_fee + comp_fee) / sum_online_qty if sum_online_qty != 0 else 0.0
        )

        intraday_buy_price = (
            intraday_buy_fee / intraday_buy_qty if intraday_buy_qty != 0 else 0.0
        )
        intraday_sell_price = (
            intraday_sell_fee / intraday_sell_qty if intraday_sell_qty != 0 else 0.0
        )

        cs_buy_price = cs_buy_fee / cs_buy_qty if cs_buy_qty != 0 else 0.0
        cs_sell_price = cs_sell_fee / cs_sell_qty if cs_sell_qty != 0 else 0.0

        # 获取官方电价和差额
        official_data = official_prices.get(node, {})
        official_price = official_data.get("official_price")
        saved_diff = official_data.get("diff_amount")

        # ⭐ 修改计算逻辑：前端数据 - 后端数据
        diff = saved_diff
        if diff is None:
            if official_price is not None and sum_online_qty != 0:
                # 理论电费 = 官方均价 * 结算电量
                # 差额 = 理论电费 - 实际总电费
                diff = (official_price * sum_online_qty) - sum_total_fee
            else:
                diff = 0.0

        results.append(
            {
                "node": node,
                "latestDate": latest_date,  # ⭐ 新增
                "barePrice": round(bare_price, 3),
                "settlementPrice": round(settlement_price, 3),
                "officialPrice": official_price,
                "simulatedFee": (
                    saved_diff if saved_diff is not None else None
                ),  # ⭐ 把原 diff_amount 作为模拟电费返回
                "totalFee": round(sum_total_fee, 2),  # ⭐ 返回后端汇总的实际电费
                "yearFee": round(sum_year_fee, 2),
                "monthFee": round(sum_month_fee, 2),
                "intradayFee": round(sum_intraday_fee, 2),
                "intradayBuyQty": round(intraday_buy_qty, 3),
                "intradayBuyPrice": round(intraday_buy_price, 3),
                "intradaySellQty": round(intraday_sell_qty, 3),
                "intradaySellPrice": round(intraday_sell_price, 3),
                "spotProfit": round(spot_profit, 2),
                "csFee": round(sum_cs_fee, 2),
                "csBuyQty": round(cs_buy_qty, 3),
                "csBuyPrice": round(cs_buy_price, 3),
                "csSellQty": round(cs_sell_qty, 3),
                "csSellPrice": round(cs_sell_price, 3),
                "diff": round(diff, 2) if diff is not None else 0.0,
            }
        )

    return success(results)


@settlement_bp.post("/actual/save-official")
def save_official_price_api():
    data = request.get_json(silent=True) or {}
    node_name = data.get("node")
    month = data.get("month")
    official_price = data.get("officialPrice")
    simulated_fee = data.get("simulatedFee")  # ⭐ 接收模拟电费

    if not node_name or not month:
        return fail("缺少参数")

    from services.db_store import save_official_price

    try:
        save_official_price(
            node_name,
            month,
            float(official_price) if official_price is not None else None,
            (
                float(simulated_fee) if simulated_fee is not None else None
            ),  # ⭐ 存进 diff_amount 字段
        )
        return success(msg="保存成功")
    except Exception as e:
        return fail(f"保存失败: {e}")
