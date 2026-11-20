from flask import Blueprint, request
from utils.response import success, fail
from services.spot_profit import compute_rolling_spot_profit

rolling_bp = Blueprint("rolling", __name__)

# 滚撮分析涉及的数据读取（江苏库日前价格 + 日前价格服务）缓存前缀
PRICE_CACHE_PREFIXES = (
    "fetch_day_ahead",
    "fetch_realtime",
    "fetch_unified_heatmap",
)


@rolling_bp.route("/analysis", methods=["GET"])
def rolling_analysis():
    target_date = request.args.get("targetDate")
    if not target_date:
        return fail("请选择标的日")

    # refresh=1：先失效滚撮/日前价格相关缓存再查，确保拿到刚上传的数据
    if str(request.args.get("refresh", "")).strip() in ("1", "true", "yes"):
        from utils.cache import clear_cache

        clear_cache(PRICE_CACHE_PREFIXES)

    try:
        from services.rolling_analysis import get_rolling_analysis

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

    # 口径统一到 services.spot_profit（与模拟结算单共用）
    try:
        result = compute_rolling_spot_profit(unit_name, start_date, end_date)
    except Exception as e:
        return fail(str(e))
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

    # 新数据已落库，失效相关读取缓存，避免紧接着的查询命中旧结果
    from utils.cache import clear_cache

    clear_cache(PRICE_CACHE_PREFIXES)

    msg = f"市场滚撮上传成功，共 {total_count} 条"
    if date_set:
        msg += f"（操作日期：{', '.join(sorted(date_set))}）"
    if errors:
        msg += f"，{len(errors)} 个文件失败"

    return success(
        {"count": total_count, "dates": sorted(date_set), "errors": errors},
        msg=msg,
    )