"""通用模拟结算单更新（原 sim_v2.py）"""

import os
import re
import openpyxl
from datetime import datetime
from utils.dates import get_tenday_value
from utils.excel_utils import find_sheet_by_keywords
from utils.number_format import apply_number_format_v2


def fill_simulation_data_v2(
    spot_data,
    stat_data,
    strategy_month_data,
    strategy_tenday_data,
    info_spot_day_data,
    info_spot_rt_data,
    info_contract_data,
    target_file,
    annual_price,
    monthly_price,
    tenday_prices,
    selected_dates=None,
    log_func=print,
    progress_func=None,
):
    if not os.path.isfile(target_file):
        log_func(f"错误：目标文件不存在 {target_file}")
        return

    try:
        wb_target = openpyxl.load_workbook(target_file)
    except Exception as e:
        log_func(f"加载目标文件失败: {e}")
        return

    target_sheets = []
    for name in wb_target.sheetnames:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", name.strip()):
            continue
        try:
            d = datetime.strptime(name.strip(), "%Y-%m-%d").date()
            target_sheets.append((d, name.strip(), wb_target[name]))
        except Exception:
            pass
    target_sheets.sort(key=lambda x: x[0])

    if selected_dates:
        sels = set(datetime.strptime(s, "%Y-%m-%d").date() for s in selected_dates if s)
        target_sheets = [(d, n, ws) for d, n, ws in target_sheets if d in sels]

    if not target_sheets:
        log_func("错误：无匹配日期")
        return

    summary_rows = []
    total = len(target_sheets)
    for loop_idx, (date_obj, date_str, ws_tgt) in enumerate(target_sheets):
        if progress_func:
            progress_func(loop_idx, total)
        log_func(f"处理日期 {date_str}")

        # 直接从内存字典读取
        actual_pts = spot_data.get(date_str, [0.0] * 48)
        day_pts = info_spot_day_data.get(date_str, [0.0] * 48)
        rt_pts = info_spot_rt_data.get(date_str, [0.0] * 48)

        stat_pts = stat_data.get(date_str, [0.0] * 48)
        month_pts = strategy_month_data.get(date_str, [0.0] * 48)
        tenday_pts = strategy_tenday_data.get(date_str, [0.0] * 48)
        contract_pts = info_contract_data.get(date_str, [0.0] * 48)

        for i in range(48):
            ws_tgt.cell(row=5 + i, column=2, value=actual_pts[i])
            ws_tgt.cell(row=5 + i, column=3, value=day_pts[i])
            declaration_pts = (
                declaration_data
                if declaration_data and len(declaration_data) == 48
                else [0.0] * 48
            )
            ws_tgt.cell(row=5 + i, column=5, value=declaration_pts[i])
            ws_tgt.cell(row=5 + i, column=7, value=rt_pts[i])

            ws_tgt.cell(row=5 + i, column=9, value=stat_pts[i])
            ws_tgt.cell(row=5 + i, column=10, value=annual_price)
            ws_tgt.cell(row=5 + i, column=11, value=contract_pts[i])

            ws_tgt.cell(row=5 + i, column=14, value=month_pts[i])
            ws_tgt.cell(row=5 + i, column=15, value=monthly_price)
            ws_tgt.cell(row=5 + i, column=16, value=contract_pts[i])

            ws_tgt.cell(row=5 + i, column=19, value=tenday_pts[i])
            tp = get_tenday_value(date_obj, tenday_prices)
            ws_tgt.cell(row=5 + i, column=20, value=tp)
            ws_tgt.cell(row=5 + i, column=21, value=contract_pts[i])

        B_sum = D_sum = 0.0
        for i in range(48):
            r = 5 + i
            b = ws_tgt.cell(row=r, column=2).value or 0
            c = ws_tgt.cell(row=r, column=3).value or 0
            e = ws_tgt.cell(row=r, column=5).value or 0
            g = ws_tgt.cell(row=r, column=7).value or 0
            ii = ws_tgt.cell(row=r, column=9).value or 0
            j = ws_tgt.cell(row=r, column=10).value or 0
            k = ws_tgt.cell(row=r, column=11).value or 0
            n = ws_tgt.cell(row=r, column=14).value or 0
            o = ws_tgt.cell(row=r, column=15).value or 0
            p = ws_tgt.cell(row=r, column=16).value or 0
            s = ws_tgt.cell(row=r, column=19).value or 0
            t = ws_tgt.cell(row=r, column=20).value or 0
            u = ws_tgt.cell(row=r, column=21).value or 0

            f = e - b
            d = b * c
            h = f * g
            l = j - k
            m = l * ii
            q = o - p
            rr = q * n
            v = t - u
            w = v * s

            B_sum += b + f
            D_sum += d + h + m + rr + w

        summary_rows.append((date_obj.day, B_sum, D_sum))

        date_label = f"{date_obj.month}月{date_obj.day}日"
        ws_tgt.cell(row=1, column=2, value=date_label)
        ws_tgt.cell(row=53, column=2, value=date_label)
        apply_number_format_v2(ws_tgt)

    if progress_func:
        progress_func(total, total)
    ws_summary = find_sheet_by_keywords(
        wb_target,
        keywords=["模拟结算", "汇总"],
        exact_names=["模拟结算汇总表", "模拟结算汇总", "结算汇总", "汇总"],
    )
    if ws_summary is None:
        log_func("错误：目标文件中缺少「模拟结算汇总」工作表，无法写入汇总")
        wb_target.close()
        return
    for day, b_sum, d_sum in summary_rows:
        ws_summary.cell(row=3 + day - 1, column=2, value=b_sum)
        ws_summary.cell(row=3 + day - 1, column=4, value=d_sum)

    try:
        wb_target.save(target_file)
        wb_target.close()
        log_func(f"✅ 完成！共处理 {len(summary_rows)} 天。")
    except Exception as e:
        log_func(f"保存失败: {e}")
