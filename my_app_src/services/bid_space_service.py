"""对接外部 t_bid_space 业务库（浙江省数据）"""

import mysql.connector
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from config import Config
from utils.cache import ttl_cache
from utils.logger import get_logger

logger = get_logger("services.bid_space_service")


def _get_js_conn():
    try:
        conn = mysql.connector.connect(
            host=Config.JS_DB_HOST,
            port=Config.JS_DB_PORT,
            user=Config.JS_DB_USER,
            password=Config.JS_DB_PASS,
            database=Config.JS_DB_NAME,
            connection_timeout=5,
            ssl_disabled=True,
            use_pure=True,  # ← 新增：强制使用纯 Python 驱动，避免 C 扩展在打包环境报 SSL 错误
        )
        return conn
    except Exception as e:
        logger.error(
            f"[BidSpace] 数据库连接失败！请检查配置: {Config.JS_DB_HOST}:{Config.JS_DB_PORT}, 错误: {e}"
        )
        raise e


def _time_code_to_str(tc: str) -> str:
    """将库中的 time_code (如 '0030' 或 '00:30') 转为 '00:30'"""
    tc = str(tc).strip()
    if ":" in tc:
        parts = tc.split(":")
        return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
    else:
        tc = tc.zfill(4)
        return f"{tc[:2]}:{tc[2:]}"


def _fetch_data(
    sample_types: tuple,
    start_date: str,
    end_date: str,
    unit_name: str = None,
) -> Dict[str, Dict]:
    """通用查询函数。返回: { "2026-10-01": { "00:30": {"v2": 10, "v4": 20}, ... } }"""
    # ====== 补全 sql 和 params 的构建 ======
    placeholders = ",".join(["%s"] * len(sample_types))
    sql = f"""
        SELECT a.sample_time, a.unit_name, b.time_code, 
               SUM(b.ext_type2) as val2, SUM(b.ext_type4) as val4
        FROM t_bid_space a
        JOIN t_bid_space_sub b ON a.id = b.parent_id
        WHERE a.sample_type IN ({placeholders})
          AND a.province = '浙江省'
          AND a.sample_time >= %s AND a.sample_time <= %s
    """
    params = list(sample_types) + [f"{start_date} 00:00:00", f"{end_date} 23:59:59"]
    if unit_name:
        sql += " AND a.unit_name = %s"
        params.append(unit_name)

    sql += " GROUP BY a.sample_time, a.unit_name, b.time_code ORDER BY a.sample_time, b.time_code"
    # =====================================

    result = {}
    try:
        conn = _get_js_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            # 手动转字典
            columns = [col[0] for col in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
    except Exception as e:
        logger.warning(f"[BidSpace] 查询外部库失败: {e}")
        return {}

    for r in rows:
        st = r["sample_time"]
        date_str = st.strftime("%Y-%m-%d") if hasattr(st, "strftime") else str(st)[:10]
        time_str = _time_code_to_str(r["time_code"])

        if time_str == "00:00":
            continue
        if time_str[-2:] not in ("00", "30"):
            continue

        result.setdefault(date_str, {})[time_str] = {
            "v2": float(r["val2"]) if r["val2"] is not None else None,
            "v4": float(r["val4"]) if r["val4"] is not None else None,
        }
    return result


# ================= 对外接口 =================


# 默认缓存 5 分钟 (300秒)
# 对于日期维度的查询，加缓存非常合适，因为历史数据不会改变
@ttl_cache(seconds=7200)
def fetch_load(date: str) -> List[Dict]:
    """负荷（短期负荷边界 / 出清）"""
    data = _fetch_data((1,), date, date)
    if not data or date not in data:
        return []

    points = []
    for t, v in sorted(data[date].items()):
        points.append({"time": t, "value": v["v2"], "actual": v["v4"]})
    return points


@ttl_cache(seconds=7200)
def fetch_pv(date: str) -> List[Dict]:
    """光伏（统调光伏边界 / 出清）"""
    data = _fetch_data((3, 4), date, date)
    if not data or date not in data:
        return []
    return [
        {"time": t, "value": v["v2"], "actual": v["v4"]}
        for t, v in sorted(data[date].items())
    ]


@ttl_cache(seconds=7200)
def fetch_day_ahead(date: str, node_name: str = None) -> List[Dict]:
    """日前电价（统一:27 / 节点:25）"""
    st = (25,) if node_name else (27,)
    data = _fetch_data(st, date, date, unit_name=node_name)
    if not data or date not in data:
        return []
    return [{"time": t, "value": v["v2"]} for t, v in sorted(data[date].items())]


@ttl_cache(seconds=7200)
def fetch_realtime(date: str, node_name: str = None) -> List[Dict]:
    """实时电价（统一:26 / 节点:24）"""
    st = (24,) if node_name else (26,)
    data = _fetch_data(st, date, date, unit_name=node_name)
    if not data or date not in data:
        return []
    return [{"time": t, "value": v["v2"]} for t, v in sorted(data[date].items())]


@ttl_cache(seconds=7200)
def fetch_spread(date: str, node_name: str = None) -> List[Dict]:
    """价差 = 日前 - 实时"""
    st_day = (25,) if node_name else (27,)
    st_rt = (24,) if node_name else (26,)

    day_data = _fetch_data(st_day, date, date, unit_name=node_name)
    rt_data = _fetch_data(st_rt, date, date, unit_name=node_name)

    if not day_data or not rt_data or date not in day_data or date not in rt_data:
        return []

    points = []
    for t in sorted(day_data[date].keys()):
        d_val = day_data[date][t]["v2"]
        r_val = rt_data[date].get(t, {}).get("v2")

        spread_val = None
        if d_val is not None and r_val is not None:
            spread_val = round(d_val - r_val, 3)

        points.append(
            {"time": t, "dayAhead": d_val, "realTime": r_val, "value": spread_val}
        )
    return points


@ttl_cache(seconds=7200)
def fetch_dates_in_month(
    start_date: str, end_date: str, sample_type: int, unit_name: str = None
) -> List[str]:
    """获取某个月中有数据的日期列表（用于填充热力图日期轴）"""
    placeholders = "%s"
    sql = f"""
        SELECT DISTINCT DATE(a.sample_time) as dt
        FROM t_bid_space a
        WHERE a.sample_type = {placeholders} AND a.province = '浙江省'
          AND a.sample_time >= %s AND a.sample_time <= %s
    """
    params = [sample_type, f"{start_date} 00:00:00", f"{end_date} 23:59:59"]
    if unit_name:
        sql += " AND a.unit_name = %s"
        params.append(unit_name)
    sql += " ORDER BY dt"

    try:
        conn = _get_js_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            # ====== 核心修复：手动将元组转为字典 ======
            columns = [col[0] for col in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            # =========================================
        conn.close()

        # 此时 r 绝对是一个字典
        return [r["dt"].strftime("%Y-%m-%d") for r in rows if r["dt"]]
    except Exception as e:
        logger.warning(f"[BidSpace] 查日期失败: {e}")
        return []


@ttl_cache(seconds=7200)
def fetch_unit_names() -> List[str]:
    """从 power_unit 表查询浙江省的节点名称"""
    sql = "SELECT DISTINCT unit_name FROM power_unit WHERE province = '浙江省' AND unit_name IS NOT NULL AND unit_name != ''"
    try:
        conn = _get_js_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql)
            # 兼容可能返回元组或字典的情况
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return [r["unit_name"] for r in rows]
            return []
    except Exception as e:
        logger.warning(f"[BidSpace] 查询节点列表失败: {e}")
        return []


@ttl_cache(seconds=7200)
def fetch_day_ahead_range(
    start_date: str, end_date: str, node_name: str = None
) -> Dict[str, Dict]:
    """一次性拉取日期范围内的日前电价"""
    st = (25,) if node_name else (27,)
    return _fetch_data(st, start_date, end_date, unit_name=node_name)


@ttl_cache(seconds=7200)
def fetch_realtime_range(
    start_date: str, end_date: str, node_name: str = None
) -> Dict[str, Dict]:
    """一次性拉取日期范围内的实时电价"""
    st = (24,) if node_name else (26,)
    return _fetch_data(st, start_date, end_date, unit_name=node_name)
