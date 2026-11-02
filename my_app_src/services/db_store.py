"""业务数据库存储：上传即解析，解析结果按点位写入数据库

字段约定：
- data_type : load / pv / day-ahead / spread
- sub_type  : 负荷与光伏存曲线类型（actual / forecast / pv / pv_forecast），
              电价存节点类别（unified / plant）
- device    : 设备或节点名（如 浙江电网、某电厂节点）
- date      : YYYY-MM-DD
- time_label: 时间点标签（HH:MM，15/30 分钟或小时粒度）
- value     : 数值（MW 或 元/MWh），可为 NULL

快速失败设计（重要）：
    未配置数据库时，页面查询必须"秒返回"，不能因为等 DNS / TCP 超时而卡住前端。
    - 连接参数带 connect_timeout / read_timeout / write_timeout，最长只等几秒
    - .env 里还是占位值（含中文）时直接判定为未配置，连都不连
    - 连接失败进入熔断，冷却期内所有读写立即跳过
"""

from datetime import datetime
from typing import Dict, List, Optional
import time

import pymysql

from config import Config

_TABLE = "tmp_curve_data"
_table_ready = False

# 连接与读写超时（秒）：宁可快速失败，也不要拖垮页面请求
_CONNECT_TIMEOUT = 3
_READ_TIMEOUT = 10
_WRITE_TIMEOUT = 10

# ===== 数据库可用性快速失败 =====
# 连接失败后冷却期内不再尝试，避免每次查询都等超时
_DB_COOLDOWN_SECONDS = 30
_UNCONFIGURED_COOLDOWN_SECONDS = 300
_db_failed_until = 0.0
_warned_unconfigured = False

_DDL = f"""
CREATE TABLE IF NOT EXISTS {_TABLE} (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    data_type VARCHAR(32) NOT NULL,
    sub_type VARCHAR(32) NOT NULL DEFAULT '',
    device VARCHAR(128) NOT NULL DEFAULT '',
    `date` VARCHAR(20) NOT NULL,
    time_label VARCHAR(16) NOT NULL,
    value DOUBLE NULL,
    seq INT NOT NULL DEFAULT 0,
    source_file VARCHAR(255) NOT NULL DEFAULT '',
    uploaded_at DATETIME NOT NULL,
    KEY idx_query (data_type, sub_type, device, `date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def _is_placeholder(value: str) -> bool:
    """空值或含非 ASCII 字符（如"你的阿里云RDS地址"）视为未配置"""
    if not value:
        return True
    return any(ord(ch) > 127 for ch in value)


def db_configured() -> bool:
    """数据库参数是否看起来已真实配置"""
    return not any(
        _is_placeholder(v)
        for v in (Config.DB_HOST, Config.DB_USER, Config.DB_NAME)
    )


def get_db_conn():
    """MySQL 连接（连接参数来自 my_app_src/.env，带超时，失败快速返回）"""
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASS,
        database=Config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        connect_timeout=_CONNECT_TIMEOUT,
        read_timeout=_READ_TIMEOUT,
        write_timeout=_WRITE_TIMEOUT,
    )


def _db_available() -> bool:
    """当前是否应该尝试访问数据库"""
    if not db_configured():
        return False
    return time.time() >= _db_failed_until


def _skip_reason() -> str:
    if not db_configured():
        return "数据库未配置（.env 中仍是占位值）"
    return "数据库处于熔断冷却期"


def _warn_unconfigured_once() -> None:
    global _warned_unconfigured
    if _warned_unconfigured:
        return
    _warned_unconfigured = True
    print(
        "[DbStore] 数据库未配置：.env 里 DB_HOST / DB_USER / DB_NAME 仍是占位值。\n"
        "          曲线数据仅保留在内存预览，重启后需重新上传；"
        "配好真实连接后即可持久化。"
    )


def _mark_db_failed(reason: str = "") -> None:
    global _db_failed_until
    if not db_configured():
        _db_failed_until = time.time() + _UNCONFIGURED_COOLDOWN_SECONDS
        _warn_unconfigured_once()
        return
    _db_failed_until = time.time() + _DB_COOLDOWN_SECONDS
    print(f"[DbStore] 数据库不可用（{reason}），{_DB_COOLDOWN_SECONDS} 秒内跳过读写")


def _mark_db_ok() -> None:
    global _db_failed_until
    _db_failed_until = 0.0


def ensure_table() -> bool:
    """确保业务数据表存在；未配置或不可用时立即返回 False，不阻塞请求"""
    global _table_ready
    if _table_ready:
        return True
    if not _db_available():
        return False
    try:
        conn = get_db_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(_DDL)
        finally:
            conn.close()
        _table_ready = True
        _mark_db_ok()
    except Exception as e:
        print(f"[DbStore] 初始化业务数据表失败: {e}")
        _mark_db_failed(str(e))
    return _table_ready


def replace_points(
    data_type: str,
    sub_type: str,
    device: str,
    date: str,
    points: List[Dict],
    source_file: str = "",
) -> int:
    """按 (data_type, sub_type, device, date) 整体替换：先删旧点，再写入新点

    points: [{"time": "00:30", "value": 456.789}, ...]
    返回写入点位数；数据库不可用时抛出异常，由调用方（ingest）捕获后仅保留预览。
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for i, pt in enumerate(points or []):
        t = str(pt.get("time") or "").strip()
        if not t:
            continue
        v = pt.get("value")
        try:
            v = float(v) if v is not None else None
        except (TypeError, ValueError):
            v = None
        rows.append(
            (data_type, sub_type or "", device or "", date, t, v, i, source_file, now)
        )

    if not ensure_table():
        raise RuntimeError(_skip_reason())

    sql = (
        f"INSERT INTO {_TABLE} "
        "(data_type, sub_type, device, `date`, time_label, value, seq, source_file, uploaded_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )
    try:
        conn = get_db_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"DELETE FROM {_TABLE} "
                    "WHERE data_type=%s AND sub_type=%s AND device=%s AND `date`=%s",
                    (data_type, sub_type or "", device or "", date),
                )
                if rows:
                    cursor.executemany(sql, rows)
            _mark_db_ok()
        finally:
            conn.close()
    except Exception as e:
        _mark_db_failed(str(e))
        raise
    return len(rows)


def fetch_items(
    data_type: str,
    sub_type: Optional[str] = None,
    date: Optional[str] = None,
    device: Optional[str] = None,
) -> List[Dict]:
    """读取并分组为与 Excel 解析同构的记录列表

    返回 [{"date","device","kind","points"}]；未配置 / 熔断中 / 无数据时返回空列表。
    sub_type / date / device 传 None 或空串表示该维度不限。
    """
    if not _db_available() or not ensure_table():
        return []

    sql = (
        f"SELECT sub_type, device, `date`, time_label, value FROM {_TABLE} "
        "WHERE data_type=%s"
    )
    args: List = [data_type]
    if sub_type:
        sql += " AND sub_type=%s"
        args.append(sub_type)
    if date:
        sql += " AND `date`=%s"
        args.append(date)
    if device:
        sql += " AND device=%s"
        args.append(device)
    sql += " ORDER BY id"

    try:
        conn = get_db_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, args)
                rows = cursor.fetchall()
        finally:
            conn.close()
        _mark_db_ok()
    except Exception as e:
        print(f"[DbStore] 查询失败（{data_type}/{sub_type}）: {e}")
        _mark_db_failed(str(e))
        return []

    grouped: Dict[tuple, Dict] = {}
    for r in rows:
        key = (r["date"], r["device"], r["sub_type"])
        item = grouped.setdefault(
            key,
            {
                "date": r["date"],
                "device": r["device"],
                "kind": r["sub_type"],
                "points": [],
            },
        )
        item["points"].append({"time": r["time_label"], "value": r["value"]})
    return list(grouped.values())


def rename_node(old_name: str, new_name: str) -> None:
    """节点改名：同步更新已入库的电厂节点数据（day-ahead / spread）"""
    if not _db_available():
        return
    try:
        conn = get_db_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"UPDATE {_TABLE} SET device=%s "
                    "WHERE data_type IN ('day-ahead','spread') "
                    "AND sub_type='plant' AND device=%s",
                    (new_name, old_name),
                )
        finally:
            conn.close()
    except Exception as e:
        print(f"[DbStore] 节点改名同步失败（{old_name} → {new_name}）: {e}")


def delete_node_data(node_name: str) -> None:
    """删除节点时清理其已入库数据（day-ahead / spread 的 plant 记录）"""
    if not _db_available():
        return
    try:
        conn = get_db_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"DELETE FROM {_TABLE} "
                    "WHERE data_type IN ('day-ahead','spread') "
                    "AND sub_type='plant' AND device=%s",
                    (node_name,),
                )
        finally:
            conn.close()
    except Exception as e:
        print(f"[DbStore] 清理节点数据失败（{node_name}）: {e}")
