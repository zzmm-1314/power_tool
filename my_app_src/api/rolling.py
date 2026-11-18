from flask import Blueprint, request
from utils.response import success, fail
from services.rolling_analysis import get_rolling_analysis

rolling_bp = Blueprint("rolling", __name__)


@rolling_bp.route("/analysis", methods=["GET"])
def rolling_analysis():
    target_date = request.args.get("targetDate")
    if not target_date:
        return fail("请选择标的日")
    try:
        data = get_rolling_analysis(target_date)
        return success(data)
    except Exception as e:
        return fail(str(e))


@rolling_bp.route("/spot-analysis", methods=["GET"])
def spot_analysis():
    unit_name = request.args.get("node")
    start_date = request.args.get("startDate")
    end_date = request.args.get("endDate")

    if not unit_name or not start_date or not end_date:
        return fail("缺少参数 node / startDate / endDate")

    from services.db_store import fetch_rolling_spot

    records = fetch_rolling_spot(unit_name, start_date, end_date)
    if not records:
        return success([])

    from services.bid_space_service import fetch_day_ahead

    # 按标的日分组，因为电价需要按标的日查
    by_trade_date = {}
    for r in records:
        t_date = str(r["trade_date"])[:10]
        by_trade_date.setdefault(t_date, []).append(r)

    result = []
    for t_date, items in by_trade_date.items():
        # 查标的日的日前电价
        day_pts = fetch_day_ahead(t_date)

        day_map = {}
        if day_pts:
            day_dict = {
                p["time"]: p["value"] for p in day_pts if p["value"] is not None
            }
            for h in range(24):
                t1 = f"{h:02d}:30"
                t2 = f"{(h+1):02d}:00" if h < 23 else "24:00"
                v1 = day_dict.get(t1)
                v2 = day_dict.get(t2)

                if v1 is not None and v2 is not None:
                    day_map[f"{h:02d}:00-{(h+1):02d}:00"] = round((v1 + v2) / 2, 3)
                elif v1 is not None:
                    day_map[f"{h:02d}:00-{(h+1):02d}:00"] = v1
                elif v2 is not None:
                    day_map[f"{h:02d}:00-{(h+1):02d}:00"] = v2

        for r in items:
            t_type = r["time_type"]
            clear_price = day_map.get(t_type, 0.0)

            # ⭐ 修复：强制将 Decimal 转换为 float
            qty_val = float(r["qty"])
            price_val = float(r["price"])

            if r["direction"] == "卖方":
                trade_qty = qty_val
                price_diff = price_val - clear_price
            else:
                trade_qty = -qty_val
                price_diff = clear_price - price_val

            final_diff = trade_qty * price_diff

            result.append(
                {
                    "opDate": r["op_date"],
                    "tradeDate": r["trade_date"],
                    "timeType": t_type,
                    "direction": r["direction"],
                    "qty": qty_val,
                    "price": price_val,
                    "tradeQty": trade_qty,
                    "clearPrice": clear_price,
                    "priceDiff": round(price_diff, 3),
                    "finalDiff": round(final_diff, 2),
                }
            )

    result.sort(key=lambda x: (x["opDate"], x["tradeDate"], x["timeType"]))
    return success(result)


@rolling_bp.post("/market-upload")
def market_upload():
    """上传市场滚撮 Excel（市场交易信息 sheet）"""
    files = request.files.getlist("files")
    if not files:
        single = request.files.get("file")
        if single:
            files = [single]
    if not files:
        return fail("未选择文件")

    from services.market_rolling_parser import parse_market_rolling_excel
    from services.db_store import save_market_rolling
    import tempfile
    import os

    total_count = 0
    date_set: set = set()
    errors: list = []

    for f in files:
        if not f.filename or not f.filename.lower().endswith((".xlsx", ".xls")):
            errors.append(f"{f.filename}: 仅支持 .xlsx / .xls")
            continue

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=os.path.splitext(f.filename)[1]
            ) as tmp:
                f.save(tmp.name)
                tmp_path = tmp.name

            records = parse_market_rolling_excel(tmp_path)
            if not records:
                errors.append(f"{f.filename}: 未解析到有效数据")
                continue

            cnt = save_market_rolling(records, os.path.basename(f.filename))
            total_count += cnt
            date_set.update(r["op_date"] for r in records)
        except Exception as e:
            errors.append(f"{f.filename}: {e}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    if total_count == 0:
        return fail("上传失败：" + ("; ".join(errors) if errors else "无有效数据"))

    msg = f"市场滚撮上传成功，共 {total_count} 条"
    if date_set:
        msg += f"（操作日期：{', '.join(sorted(date_set))}）"
    if errors:
        msg += f"，{len(errors)} 个文件失败"

    return success(
        {"count": total_count, "dates": sorted(date_set), "errors": errors},
        msg=msg,
    )
