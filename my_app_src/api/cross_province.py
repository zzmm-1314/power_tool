from flask import Blueprint, request
from utils.response import success, fail
from services.bid_space_service import fetch_day_ahead

cross_bp = Blueprint("cross_province", __name__)


@cross_bp.route("/spot-analysis", methods=["GET"])
def spot_analysis():
    unit_name = request.args.get("node")
    start_date = request.args.get("startDate")
    end_date = request.args.get("endDate")

    if not unit_name or not start_date or not end_date:
        return fail("缺少参数 node / startDate / endDate")

    from services.db_store import fetch_cross_province_spot

    records = fetch_cross_province_spot(unit_name, start_date, end_date)
    if not records:
        return success([])

    by_trade_date = {}
    for r in records:
        t_date = str(r["trade_date"])[:10]
        by_trade_date.setdefault(t_date, []).append(r)

    result = []
    for t_date, items in by_trade_date.items():
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

            # 1. 转换类型为 float
            qty_val = float(r["qty"])
            price_val = float(r["price"])

            # 2. 交易逻辑：购电(买方) 和 售电(卖方)
            if r["direction"] == "购电":
                trade_qty = -qty_val  # ⭐ 改用 qty_val
                price_diff = price_val - clear_price  # ⭐ 改用 price_val
            else:
                trade_qty = qty_val  # ⭐ 改用 qty_val
                price_diff = price_val - clear_price  # ⭐ 改用 price_val

            final_diff = trade_qty * price_diff

            result.append(
                {
                    "opDate": r["op_date"],
                    "tradeDate": r["trade_date"],
                    "timeType": t_type,
                    "direction": r["direction"],
                    "qty": qty_val,  # ⭐ 返回 float
                    "price": price_val,  # ⭐ 返回 float
                    "tradeQty": trade_qty,
                    "clearPrice": clear_price,
                    "priceDiff": round(price_diff, 3),
                    "finalDiff": round(final_diff, 2),
                    "tradePath": r["trade_path"],
                }
            )

    result.sort(key=lambda x: (x["opDate"], x["tradeDate"], x["timeType"]))
    return success(result)
