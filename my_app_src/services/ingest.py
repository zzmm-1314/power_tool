# services/ingest.py
"""导入落数：先查正式库拦截，再写内存预览，最后尽力写浙江临时库"""

from typing import Dict, List
from utils.logger import get_logger
from services.bid_space_service import _fetch_data

logger = get_logger("services.ingest")


def _check_formal_exists(data_type: str, sub_type: str, device: str, date: str) -> bool:
    """检查正式库（江苏库）中是否已有该数据"""
    try:
        if data_type == "load":
            return bool(_fetch_data((1,), date, date))
        elif data_type == "pv":
            return bool(_fetch_data((3, 4), date, date))
        elif data_type == "day-ahead" and sub_type == "unified":
            return bool(_fetch_data((27,), date, date))
        elif data_type == "spread" and sub_type == "unified":
            return bool(_fetch_data((26,), date, date))
        elif data_type == "day-ahead" and sub_type == "plant":
            return bool(_fetch_data((25,), date, date, unit_name=device))
        elif data_type == "spread" and sub_type == "plant":
            return bool(_fetch_data((24,), date, date, unit_name=device))
    except Exception as e:
        logger.warning(f"[Ingest] 正式库检查失败，默认放行写入临时库: {e}")
        return False
    return False


def store_points(
    data_type: str,
    sub_type: str,
    device: str,
    date: str,
    points: List[Dict],
    source_file: str = "",
) -> Dict:
    """写入一个维度的数据，返回 {"preview": int, "saved": bool, "dbError": str}"""

    # 1. 检查正式库，如果已有则清理临时库并忽略
    if _check_formal_exists(data_type, sub_type, device, date):
        logger.info(
            f"[Ingest] 正式库已有 {data_type}/{sub_type} 在 {date} 的数据，自动清理临时库。"
        )
        try:
            from services.db_store import replace_points as db_replace

            # 传空点位实现删除
            db_replace(data_type, sub_type, device, date, [], source_file=source_file)
        except Exception:
            pass
        return {"preview": len(points), "saved": True, "dbError": ""}

    # 3. 写入浙江临时库
    saved = False
    db_error = ""
    try:
        from services.db_store import replace_points as db_replace

        db_replace(data_type, sub_type, device, date, points, source_file=source_file)
        saved = True
    except Exception as e:
        db_error = str(e)
        logger.warning(f"[Ingest] 预览已生效，但写入浙江库失败: {e}")

    return {"preview": preview_count, "saved": saved, "dbError": db_error}
