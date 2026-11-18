from flask import Blueprint, request, send_file
from utils.response import success, fail
from services.contract_service import (
    generate_contract_decomposition,
    save_uploaded_file,
    BASE_DIR,
    NODES_DIR,
    ensure_dirs,
)
from services.db_store import save_contract_config  # 顶部引入
from io import BytesIO
import pandas as pd
import os
import re
import json
from services.db_store import save_contract_data

contract_bp = Blueprint("contract", __name__)


# ==================== 模板下载 ====================
@contract_bp.route("/template", methods=["GET"])
def download_template():
    df = pd.DataFrame(
        {
            "日期": ["2026-01-01", "2026-02-17", "2026-10-01"],
            "备注": ["元旦", "春节", "国庆节"],
        }
    )
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="节假日")
    output.seek(0)
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="节假日模板.xlsx",
    )


@contract_bp.route("/actual-template", methods=["GET"])
def download_actual_template():
    columns = ["日期"] + [f"电力点{i}" for i in range(1, 49)]
    sample_data = {"日期": ["2026-10-01"]}
    for i in range(1, 49):
        sample_data[f"电力点{i}"] = [0.0]
    df = pd.DataFrame(sample_data, columns=columns)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="实际发电量")
    output.seek(0)
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="实际发电量上传模板.xlsx",
    )


# ==================== 配置上传 ====================
@contract_bp.route("/config/base", methods=["POST"])
def upload_base_config():
    ensure_dirs()
    curve_file = request.files.get("curve")
    holiday_file = request.files.get("holiday")

    msg_parts = []

    if curve_file:
        # 存本地作为备份
        save_path = os.path.join(BASE_DIR, "typical_curve.xlsx")
        save_uploaded_file(curve_file, save_path)

        # ⭐ 解析并存入数据库
        from services.contract_service import _load_typical_curve_from_file

        try:
            curves = _load_typical_curve_from_file(save_path)
            if curves:
                save_contract_config(
                    "typical_curve", json.dumps(curves, ensure_ascii=False)
                )
                msg_parts.append("典型曲线入库成功")
        except Exception as e:
            return fail(f"典型曲线解析或入库失败: {e}")

    if holiday_file:
        # 存本地作为备份
        save_path = os.path.join(BASE_DIR, "holidays.xlsx")
        save_uploaded_file(holiday_file, save_path)

        # ⭐ 解析并存入数据库
        from services.contract_service import _load_holidays_from_file

        try:
            holidays = _load_holidays_from_file(save_path)
            if holidays:
                save_contract_config(
                    "holidays", json.dumps(list(holidays), ensure_ascii=False)
                )
                msg_parts.append("节假日入库成功")
        except Exception as e:
            return fail(f"节假日解析或入库失败: {e}")

    return success(msg="基础配置保存成功：" + "，".join(msg_parts))


@contract_bp.route("/config/node-data", methods=["POST"])
def upload_node_data():
    ensure_dirs()
    node_name = request.form.get("node_name")
    data_type = request.form.get("data_type")
    op_date = request.form.get("op_date")  # ⭐ 新增：提取操作日期

    if not node_name or not data_type:
        return fail("缺少节点或数据类型参数")

    files = request.files.getlist("files")
    if not files:
        return fail("未选择文件")

    node_dir = os.path.join(NODES_DIR, node_name, data_type)
    if os.path.exists(node_dir):
        import shutil

        shutil.rmtree(node_dir)
    os.makedirs(node_dir, exist_ok=True)

    saved_files = []
    for i, f in enumerate(files):
        save_path = os.path.join(node_dir, f"{i}_{f.filename}")
        save_uploaded_file(f, save_path)
        saved_files.append(save_path)

    # ================= 特殊处理：长三角省间交易 =================
    if data_type == "cross_province":
        from services.db_store import save_cross_province_spot
        from datetime import datetime, timedelta

        total_count = 0
        try:
            for path in saved_files:
                try:
                    df = pd.read_excel(path, dtype=str)
                except ImportError:
                    return fail(
                        "当前环境缺少解析 .xls 文件的依赖库，请将文件另存为 .xlsx 后上传"
                    )
                except Exception as e:
                    return fail(f"Excel 文件读取失败: {e}")

                df.columns = df.columns.str.strip()

                if "标的代码" not in df.columns:
                    return fail("未找到「标的代码」列，请检查 Excel 模板是否正确")

                df = df.dropna(subset=["标的代码"])
                if df.empty:
                    continue

                records = []
                for idx, row in df.iterrows():
                    try:
                        code = str(row["标的代码"]).strip()
                        if len(code) < 10:
                            continue

                        # 1. 解析标的日
                        yy = code[1:3]
                        mm = code[3:5]
                        dd = code[5:7]
                        trade_date_str = f"20{yy}-{mm}-{dd}"

                        # ⭐ 2. 自动计算操作日期 (标的日 - 3天)
                        td = datetime.strptime(trade_date_str, "%Y-%m-%d")
                        op_date_str = (td - timedelta(days=3)).strftime("%Y-%m-%d")

                        # 3. 解析时段
                        hh_str = code[8:10]
                        hh = int(hh_str)
                        time_type = f"{hh:02d}:00-{hh+1:02d}:00"

                        unit_name = str(row.get("交易单元", "")).strip()
                        direction = str(row.get("成交类型", "")).strip()
                        qty = float(row.get("成交数量（MW）", 0))
                        price = float(row.get("成交价（元/MWh）", 0))
                        trade_path = str(row.get("交易路径", "")).strip()

                        records.append(
                            {
                                "op_date": op_date_str,  # 存入计算出的日期
                                "trade_date": trade_date_str,
                                "time_type": time_type,
                                "unit_name": unit_name,
                                "direction": direction,
                                "qty": qty,
                                "price": price,
                                "trade_path": trade_path,
                            }
                        )
                    except Exception as row_err:
                        print(f"[省间解析] 第 {idx+1} 行解析异常: {row_err}")
                        continue

                if records:
                    total_count += save_cross_province_spot(
                        records, os.path.basename(path)
                    )

        except Exception as e:
            import traceback

            traceback.print_exc()
            return fail(f"省间数据入库失败: {e}")

        if total_count == 0:
            return fail("未能解析出任何有效数据，请检查 Excel 格式")

        return success(msg=f"省间数据上传成功，解析 {total_count} 条")

    # ================= 合约数据（年/月/旬/实际发电量） =================
    all_records = []  # ⭐ 收集所有文件的记录
    try:
        for path in saved_files:
            # 读取时不设表头，直接读 raw，避免表头行数不固定导致的错位
            df = pd.read_excel(path, header=None, dtype=str)

            # ========================================================
            # 1. 解析实际发电量（特殊模板）
            # ========================================================
            if data_type == "actual":
                # 寻找表头行（包含 "设备名" 和 "00:30" 的行）
                header_idx = -1
                for i in range(min(10, len(df))):
                    row_strs = [str(x) for x in df.iloc[i].tolist() if pd.notna(x)]
                    if any("设备名" in s for s in row_strs) and any(
                        "00:30" in s for s in row_strs
                    ):
                        header_idx = i
                        break

                if header_idx == -1:
                    return fail(
                        "未找到包含「设备名」和「00:30」的表头行，请检查 Excel 模板"
                    )

                # 提取时间点映射 (列索引 -> 时间标签)
                time_map = {}
                for col_idx, val in enumerate(df.iloc[header_idx]):
                    if pd.notna(val):
                        v = str(val).strip()
                        if ":" in v:
                            parts = v.split(":")
                            time_map[col_idx] = (
                                f"{int(parts[0]):02d}:{int(parts[1]):02d}"
                            )

                records = []
                # 从表头下一行开始遍历数据
                for i in range(header_idx + 1, len(df)):
                    row = df.iloc[i]
                    if row.isna().all():
                        continue

                    # 解析日期：从 A 列（第0列）提取，如 "时间：2026-11-05"
                    date_text = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
                    m = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", date_text)
                    if not m:
                        continue
                    date_str = (
                        f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                    )

                    # 解析设备名（第1列）
                    unit = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
                    if not unit:
                        continue

                    # 提取 48 点
                    for col_idx, time_label in time_map.items():
                        try:
                            val = float(row.iloc[col_idx])
                        except (ValueError, TypeError):
                            val = 0.0

                        # 计算 seq (0 ~ 47)
                        if time_label == "24:00":
                            seq = 47
                        else:
                            h = int(time_label.split(":")[0])
                            mi = int(time_label.split(":")[1])
                            seq = h * 2 + (mi // 30) - 1

                        records.append(
                            {
                                "date": date_str,
                                "unit_name": unit,
                                "time_label": time_label,
                                "value": val,
                                "seq": seq,
                            }
                        )
                all_records.extend(records)  # ⭐ 累加

            # ========================================================
            # 2. 解析年度/月度/旬度合约（原逻辑）
            # ========================================================
            else:
                # 合约数据默认第一行是表头
                df = pd.read_excel(path, dtype=str)
                df.columns = df.columns.str.strip()

                point_cols = []
                for i in range(1, 49):
                    col_name = next((c for c in df.columns if f"电力点{i}" == c), None)
                    if not col_name:
                        col_name = next(
                            (c for c in df.columns if f"电力点{i}" in c), None
                        )
                    point_cols.append(col_name)

                if any(c is None for c in point_cols):
                    return fail("未找齐 48 个电力点列")

                col_unit = next((c for c in df.columns if "售方交易单元" in c), None)
                col_date = next(
                    (c for c in df.columns if "发电日期" in c or "日期" in c), None
                )
                if not col_unit or not col_date:
                    return fail("未找到「售方交易单元」或「发电日期」列")

                df = df.dropna(subset=[col_date])
                records = []
                for _, row in df.iterrows():
                    unit = str(row[col_unit]).strip()
                    date_str = str(row[col_date]).strip()[:10]
                    if not unit or not date_str:
                        continue

                    for i, col in enumerate(point_cols):
                        h = (i + 1) // 2
                        m = 30 if (i % 2 == 0) else 0
                        time_label = f"{h:02d}:{m:02d}" if i < 47 else "24:00"

                        try:
                            val = float(row[col])
                        except:
                            val = 0.0

                        records.append(
                            {
                                "date": date_str,
                                "unit_name": unit,
                                "time_label": time_label,
                                "value": val,
                                "seq": i,
                            }
                        )
                all_records.extend(records)  # ⭐ 累加

        # ⭐ 所有文件收集完毕，一次性入库（内部会按 (date, unit) 删除后插入）
        total_count = 0
        if all_records:
            total_count = save_contract_data(all_records, data_type)

    except Exception as e:
        import traceback

        traceback.print_exc()
        return fail(f"合约数据解析失败: {e}")

    return success(
        msg=f"{data_type} 上传成功，聚合 {len(saved_files)} 个文件，入库 {total_count} 条"
    )

    # ================= 特殊处理：滚撮数据 =================
    if data_type == "rolling":
        if not op_date:
            return fail("请提供滚撮数据的操作日期")

        from services.db_store import save_rolling_spot

        total_count = 0
        try:
            for path in saved_files:
                df = pd.read_excel(path, sheet_name="我的交易结果", dtype=str)
                df.columns = df.columns.str.strip()
                df = df.dropna(subset=["标的日开始日期"])
                if df.empty:
                    continue

                records = []
                for _, row in df.iterrows():
                    try:
                        records.append(
                            {
                                "op_date": op_date,
                                # ⭐ 修改点：增加 [:10] 防止时间戳后缀引起脏数据
                                "trade_date": str(row["标的日开始日期"]).strip()[:10],
                                "time_type": str(row["分时段类型"]).strip(),
                                "unit_name": str(row["交易单元"]).strip(),
                                "direction": str(row["买卖方向"]).strip(),
                                "qty": float(row["成交电量"]),
                                "price": float(row["成交均价"]),
                            }
                        )
                    except (ValueError, KeyError):
                        continue

                if records:
                    total_count += save_rolling_spot(records, os.path.basename(path))
        except Exception as e:
            import traceback

            traceback.print_exc()
            return fail(f"滚撮数据解析失败: {e}")

        return success(msg=f"滚撮数据上传成功，解析 {total_count} 条")

    # ================= 其他数据保持原样 =================
    return success(msg=f"{data_type} 数据上传成功")


# ==================== 合约分解计算 ====================
@contract_bp.route("/decompose", methods=["POST"])
def decompose():
    try:
        data = request.get_json(silent=True) or {}
        year = int(data.get("year", 2026))
        month = int(data.get("month", 1))
        qty_year = float(data.get("qty_year", 0))
        qty_month = float(data.get("qty_month", 0))
        qty_tenday1 = float(data.get("qty_tenday1", 0))
        qty_tenday2 = float(data.get("qty_tenday2", 0))
        qty_tenday3 = float(data.get("qty_tenday3", 0))

        result = generate_contract_decomposition(
            year, month, qty_year, qty_month, qty_tenday1, qty_tenday2, qty_tenday3
        )
        return success(result)
    except Exception as e:
        return fail(str(e))


@contract_bp.route("/export", methods=["POST"])
def export_result():
    """将前端传回来的结果数据导出为包含 5 个 Sheet 的 Excel"""
    data = request.get_json(silent=True) or {}
    result_data = data.get("resultData")
    times = data.get("times", [])

    if not result_data or not times:
        return fail("无数据可导出")

    try:
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            sheet_names = {
                "year": "年度分解",
                "month": "月度分解",
                "tenday1": "上旬分解",
                "tenday2": "中旬分解",
                "tenday3": "下旬分解",
            }

            for key, sheet_name in sheet_names.items():
                days_data = result_data.get(key, [])
                if not days_data:
                    continue

                rows = []
                for day in days_data:
                    row_dict = {
                        "日期": day["date"],
                        "类型": day["day_type"],
                        "日电量": day["daily_qty"],
                    }
                    # 展开 48 点
                    for i, t in enumerate(times):
                        row_dict[t] = day["points"][i]
                    rows.append(row_dict)

                df = pd.DataFrame(rows)
                df.to_excel(writer, index=False, sheet_name=sheet_name)

        output.seek(0)
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="合约分解结果.xlsx",
        )
    except Exception as e:
        return fail(f"导出失败: {str(e)}")


@contract_bp.route("/position-data", methods=["GET", "POST"])
def position_data():
    if request.method == "POST":
        req_data = request.get_json(silent=True) or {}
    else:
        req_data = request.args
    # ⭐ 统一从 req_data 取，POST 从 body、GET 从 query 都能拿到
    unit_name = req_data.get("node")
    year = req_data.get("year")
    month = req_data.get("month")
    forecast_data = req_data.get("forecastData") or {}
    if isinstance(forecast_data, str):
        try:
            forecast_data = json.loads(forecast_data)
        except Exception:
            forecast_data = {}

    # 兼容旧的旬度参数
    f_tenday1 = float(req_data.get("forecast_tenday1", 0) or 0)
    f_tenday2 = float(req_data.get("forecast_tenday2", 0) or 0)
    f_tenday3 = float(req_data.get("forecast_tenday3", 0) or 0)

    if not unit_name or not year or not month:
        return fail("缺少参数 node / year / month")

    import calendar
    from services.db_store import (
        fetch_contract_data,
        fetch_rolling_spot,
        fetch_cross_province_spot,
    )

    y, m = int(year), int(month)
    days_in_month = calendar.monthrange(y, m)[1]
    start_date = f"{y}-{m:02d}-01"
    end_date = f"{y}-{m:02d}-{days_in_month:02d}"

    c_rows = list(fetch_contract_data(unit_name, start_date, end_date) or [])
    r_rows = list(fetch_rolling_spot(unit_name, start_date, end_date) or [])
    cp_rows = list(fetch_cross_province_spot(unit_name, start_date, end_date) or [])

    # 初始化...
    daily_points = {}
    daily_year = {}
    daily_month = {}
    daily_tenday = {}
    daily_rolling = {}
    daily_actual = {}
    daily_actual_sum = {}
    daily_contract_sum = {}
    daily_rolling_buy_sum = {}
    daily_rolling_sell_sum = {}

    for d in range(1, days_in_month + 1):
        d_str = f"{y}-{m:02d}-{d:02d}"
        daily_points[d_str] = [0.0] * 48
        daily_year[d_str] = [0.0] * 48
        daily_month[d_str] = [0.0] * 48
        daily_tenday[d_str] = [0.0] * 48
        daily_rolling[d_str] = [0.0] * 48
        daily_actual[d_str] = [0.0] * 48

    # 1. 处理合约数据 (与原逻辑一致)
    for r in c_rows:
        d = str(r["date"])[:10]
        if d not in daily_points:
            continue
        dtype = str(r["data_type"])
        t = str(r["time_label"])
        val = float(r["value"])

        idx = -1
        for i in range(48):
            h = (i + 1) // 2
            mi = 30 if (i % 2 == 0) else 0
            tl = f"{h:02d}:{mi:02d}" if i < 47 else "24:00"
            if tl == t:
                idx = i
                break
        if idx != -1:
            if dtype == "actual":
                daily_actual[d][idx] += val
                daily_actual_sum[d] = daily_actual_sum.get(d, 0) + val
            elif dtype == "year":
                daily_year[d][idx] += val
                daily_contract_sum[d] = daily_contract_sum.get(d, 0) + val
            elif dtype == "month":
                daily_month[d][idx] += val
                daily_contract_sum[d] = daily_contract_sum.get(d, 0) + val
            elif dtype in ("tenday1", "tenday2", "tenday3"):
                daily_tenday[d][idx] += val
                daily_contract_sum[d] = daily_contract_sum.get(d, 0) + val

    # 2. 处理滚撮数据
    for r in r_rows + cp_rows:
        d = str(r["trade_date"])[:10]
        if d not in daily_points:
            continue

        direction = str(r["direction"])
        qty = float(r["qty"])
        if direction == "购电":
            daily_rolling_buy_sum[d] = daily_rolling_buy_sum.get(d, 0) + qty
            net_qty = -qty
        else:
            daily_rolling_sell_sum[d] = daily_rolling_sell_sum.get(d, 0) + qty
            net_qty = qty

        t_type = str(r["time_type"])
        h = int(t_type.split(":")[0])
        idx1 = h * 2
        idx2 = h * 2 + 1
        if 0 <= idx1 < 48:
            daily_rolling[d][idx1] += net_qty / 2
        if 0 <= idx2 < 48:
            daily_rolling[d][idx2] += net_qty / 2
        daily_contract_sum[d] = daily_contract_sum.get(d, 0) + net_qty

    # 3. 预测补全 & 汇总
    for d in range(1, days_in_month + 1):
        d_str = f"{y}-{m:02d}-{d:02d}"
        actual_sum = sum(daily_actual[d_str])

        if actual_sum <= 0:
            # ⭐ 优先使用上传的按日期的预测数据
            if d_str in forecast_data:
                f_val = float(forecast_data[d_str])
            else:
                # 若没有，兼容降级为按旬预测
                if d <= 10:
                    f_val = f_tenday1
                elif d <= 20:
                    f_val = f_tenday2
                else:
                    f_val = f_tenday3

            if f_val > 0:
                per_point = f_val / 48.0
                daily_actual[d_str] = [per_point] * 48
                daily_actual_sum[d_str] = f_val

        # ⭐ 严格计算每日 48 点明细 (年 + 月 + 旬 + 滚撮)
        for i in range(48):
            daily_points[d_str][i] = (
                daily_year[d_str][i]
                + daily_month[d_str][i]
                + daily_tenday[d_str][i]
                + daily_rolling[d_str][i]
            )

    # 4. 交集及卡片 summary 计算
    all_actual_dates = set(d for d, v in daily_actual_sum.items() if v > 0)
    all_contract_dates = set(d for d, v in daily_contract_sum.items() if v > 0)
    # 只要有合约且（有实际电量 或 有预测电量）就算有效日期
    valid_dates = (
        all_actual_dates.intersection(all_contract_dates)
        if all_actual_dates and all_contract_dates
        else (all_actual_dates or all_contract_dates)
    )

    summary = {
        "actual": 0.0,
        "year": 0.0,
        "month": 0.0,
        "tenday1": 0.0,
        "tenday2": 0.0,
        "tenday3": 0.0,
        "rolling": 0.0,
        "rolling_tenday1": 0.0,
        "rolling_tenday2": 0.0,
        "rolling_tenday3": 0.0,
    }
    # 累加合约数据
    for r in c_rows:
        d = str(r["date"])[:10]
        if d in valid_dates:
            dtype = str(r["data_type"])
            # 排除 actual 的重复累加，因为下面统一用 daily_actual 算
            if dtype in summary and dtype != "actual":
                summary[dtype] += float(r["value"])

    # 累加滚撮数据
    for r in r_rows + cp_rows:
        d = str(r["trade_date"])[:10]
        if d in valid_dates:
            direction = str(r["direction"])
            qty = float(r["qty"])
            net_qty = -qty if direction == "购电" else qty
            summary["rolling"] += net_qty

            day_num = int(d.split("-")[2])
            if day_num <= 10:
                summary["rolling_tenday1"] += net_qty
            elif day_num <= 20:
                summary["rolling_tenday2"] += net_qty
            else:
                summary["rolling_tenday3"] += net_qty
    # ⭐ 核心修改：实际总电量 = 有效日期内的 (实际+预测) 总和
    # 如果某天只有预测，daily_actual 里存的就是预测值，这里会直接算进去
    summary["actual"] = sum(sum(daily_actual[d]) for d in valid_dates)

    # 计算总持仓（含滚撮）
    total_contracts = (
        summary["year"]
        + summary["month"]
        + summary["tenday1"]
        + summary["tenday2"]
        + summary["tenday3"]
        + summary["rolling"]
    )

    # 5. 返回数据
    table_data = []
    chart_dates = sorted(daily_points.keys())
    for d in chart_dates:
        table_data.append(
            {
                "date": d,
                "points": [round(v, 4) for v in daily_points[d]],  # 严格包含 年月旬滚
                "yearPoints": [round(v, 4) for v in daily_year[d]],
                "monthPoints": [round(v, 4) for v in daily_month[d]],
                "tendayPoints": [round(v, 4) for v in daily_tenday[d]],
                "rollingPoints": [round(v, 4) for v in daily_rolling[d]],
                "actualPoints": [
                    round(v, 4) for v in daily_actual[d]
                ],  # 这里可能包含了预测的
                "rollingBuy": round(daily_rolling_buy_sum.get(d, 0), 4),
                "rollingSell": round(daily_rolling_sell_sum.get(d, 0), 4),
            }
        )

    return success(
        {
            "summary": {k: round(v, 4) for k, v in summary.items()}
            | {"totalContracts": round(total_contracts, 4)},
            "tableData": table_data,
            "chartData": {
                "dates": chart_dates,
                "year": [round(sum(daily_year[d]), 4) for d in chart_dates],
                "month": [round(sum(daily_month[d]), 4) for d in chart_dates],
                "tenday": [round(sum(daily_tenday[d]), 4) for d in chart_dates],
                "actual": [round(sum(daily_actual[d]), 4) for d in chart_dates],
                "rollingSell": [
                    round(daily_rolling_sell_sum.get(d, 0), 4) for d in chart_dates
                ],
                "rollingBuy": [
                    round(daily_rolling_buy_sum.get(d, 0), 4) for d in chart_dates
                ],
            },
        }
    )


@contract_bp.post("/parse-forecast")
def parse_forecast():
    """解析上传的预测电量 Excel"""
    file = request.files.get("file")
    if not file:
        return fail("未接收到文件")
    try:
        df = pd.read_excel(file, dtype=str)
        df.columns = df.columns.str.strip()
        if len(df.columns) < 2:
            return fail("Excel至少需要两列：第一列日期，第二列预测电量")

        result = {}
        for _, row in df.iterrows():
            date_text = str(row.iloc[0]).strip()
            m = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", date_text)
            if m:
                d_str = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                try:
                    qty = float(row.iloc[1])
                    result[d_str] = qty
                except (ValueError, TypeError):
                    pass
        return success(result)
    except Exception as e:
        import traceback

        traceback.print_exc()
        return fail(f"解析失败: {e}")


@contract_bp.route("/forecast-template", methods=["GET"])
def download_forecast_template():
    """下载预测电量上传模板"""
    df = pd.DataFrame(
        {"日期": ["2026-11-01", "2026-11-02"], "预测电量(MWh)": [200.5, 210.0]}
    )
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="预测电量")
    output.seek(0)
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="预测电量上传模板.xlsx",
    )


@contract_bp.route("/config/status", methods=["GET"])
def get_config_status():
    """检测数据库中是否已上传典型曲线和节假日配置"""
    from services.db_store import fetch_contract_config

    curve_val = fetch_contract_config("typical_curve")
    holiday_val = fetch_contract_config("holidays")

    return success(
        {
            "has_curve": bool(curve_val and curve_val.strip()),
            "has_holiday": bool(holiday_val and holiday_val.strip()),
        }
    )
