import pandas as pd
from datetime import datetime, timedelta
from services.db_store import get_db_conn
from utils.response import success, fail


def get_rolling_analysis(target_date_str: str) -> dict:
    if not target_date_str:
        raise ValueError("缺少标的日参数")

    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except Exception:
        raise ValueError("日期格式错误，应为 YYYY-MM-DD")

    # 计算 D-2, D-3, D-4 日期
    d2_date = (target_date - timedelta(days=2)).strftime("%Y-%m-%d")
    d3_date = (target_date - timedelta(days=3)).strftime("%Y-%m-%d")
    d4_date = (target_date - timedelta(days=4)).strftime("%Y-%m-%d")

    conn = get_db_conn()
    try:
        # 1. 查标的日的日前价格 (48点)
        # 假设表结构为 day_ahead_price(date, time_slot, price)
        sql_price = "SELECT time_slot, price FROM day_ahead_price WHERE date = %s"
        df_price = pd.read_sql(sql_price, conn, params=(target_date_str,))

        # 构造基础 48 点时间轴
        time_slots_48 = []
        for i in range(48):
            h = i // 2
            m = (i % 2) * 30
            time_slots_48.append(f"{h:02d}:{m:02d}")

        # 将价格转为字典映射，方便取值
        price_map = {row["time_slot"]: row["price"] for _, row in df_price.iterrows()}

        # 2. 查 D-2, D-3, D-4 的成交数据 (24点)
        # 假设表结构为 market_trade(date, time_slot, qty, price)
        sql_trade = """
            SELECT date, time_slot, qty, price 
            FROM market_trade 
            WHERE date IN (%s, %s, %s)
        """
        df_trade = pd.read_sql(sql_trade, conn, params=(d2_date, d3_date, d4_date))

        # 建立多维字典以便快速查询: {d2_date: {"00:00-01:00": {"qty": 10, "price": 400}}, ...}
        trade_map = {d2_date: {}, d3_date: {}, d4_date: {}}
        for _, row in df_trade.iterrows():
            d = (
                row["date"].strftime("%Y-%m-%d")
                if isinstance(row["date"], datetime)
                else str(row["date"])
            )
            if d in trade_map:
                trade_map[d][row["time_slot"]] = {
                    "qty": float(row["qty"]) if pd.notna(row["qty"]) else 0,
                    "price": float(row["price"]) if pd.notna(row["price"]) else 0,
                }

    finally:
        conn.close()

    # 3. 数据组装与计算
    result_rows = []
    for i in range(48):
        time_str = time_slots_48[i]

        # 推算对应的 24 点小时段 (例如 00:30 和 01:00 对应 00:00-01:00)
        hour_idx = i // 2
        # 构造类似 "00:00-01:00" 的标签，用来匹配数据库里的 time_slot
        # 假设数据库里存的是 "00:00-01:00" 或者 "00:00"
        # 这里我们兼容两种情况，优先找带横线的，找不到就找整点的
        trade_slot = f"{hour_idx:02d}:00-{hour_idx+1:02d}:00"
        trade_slot_short = f"{hour_idx:02d}:00"

        def get_trade(d: str):
            t = trade_map[d].get(trade_slot) or trade_map[d].get(trade_slot_short)
            if not t:
                return 0.0, 0.0
            return t["qty"], t["price"]

        da_price = price_map.get(time_str)
        if da_price is None:
            # 尝试匹配带横线的时间格式
            da_price = price_map.get(
                f"{time_str}-{time_str[:2]}:30"
                if time_str.endswith(":00")
                else f"{time_str[:2]}:00-{time_str[:2]}:30"
            )
        da_price = float(da_price) if pd.notna(da_price) else 0.0

        # D-2
        d2_qty, d2_price = get_trade(d2_date)
        d2_diff = d2_price - da_price if d2_price > 0 else None

        # D-3
        d3_qty, d3_price = get_trade(d3_date)
        d3_diff = d3_price - da_price if d3_price > 0 else None

        # D-4
        d4_qty, d4_price = get_trade(d4_date)
        d4_diff = d4_price - da_price if d4_price > 0 else None

        # 市场合计
        market_qty = d2_qty + d3_qty + d4_qty
        market_price = 0.0
        market_diff = None

        if market_qty > 0:
            # 加权均价 = 总和(电量 * 电价) / 总电量
            total_amount = (
                (d2_qty * d2_price) + (d3_qty * d3_price) + (d4_qty * d4_price)
            )
            market_price = total_amount / market_qty
            market_diff = market_price - da_price

        result_rows.append(
            {
                "time": time_str,
                "dayAheadPrice": round(da_price, 3) if da_price else None,
                "d2Qty": round(d2_qty, 3),
                "d2Price": round(d2_price, 3),
                "d2Diff": round(d2_diff, 3) if d2_diff is not None else None,
                "d3Qty": round(d3_qty, 3),
                "d3Price": round(d3_price, 3),
                "d3Diff": round(d3_diff, 3) if d3_diff is not None else None,
                "d4Qty": round(d4_qty, 3),
                "d4Price": round(d4_price, 3),
                "d4Diff": round(d4_diff, 3) if d4_diff is not None else None,
                "marketQty": round(market_qty, 3),
                "marketPrice": round(market_price, 3),
                "marketDiff": (
                    round(market_diff, 3) if market_diff is not None else None
                ),
            }
        )

    return {
        "targetDate": target_date_str,
        "d2Date": d2_date,
        "d3Date": d3_date,
        "d4Date": d4_date,
        "rows": result_rows,
    }
