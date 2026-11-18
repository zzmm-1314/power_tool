"""业务数据库存储：上传即解析，解析结果按点位写入浙江临时库"""

from datetime import datetime
from typing import Dict, List, Optional
import time
import pymysql
import os
from config import Config
from utils.logger import get_logger

logger = get_logger("services.db_store")

_table_ready = {}
_CONNECT_TIMEOUT = 3
_READ_TIMEOUT = 10
_WRITE_TIMEOUT = 10

_DB_COOLDOWN_SECONDS = 30
_UNCONFIGURED_COOLDOWN_SECONDS = 300
_db_failed_until = 0.0
_warned_unconfigured = False

_DDL_TEMPLATES = {
    "tmp_price": """
        CREATE TABLE IF NOT EXISTS `tmp_price` (
        `id` bigint unsigned NOT NULL AUTO_INCREMENT,
        `date` date NOT NULL,
        `point_type` varchar(16) NOT NULL DEFAULT 'unified',
        `unit_name` varchar(128) NOT NULL DEFAULT '',
        `price_type` varchar(16) NOT NULL DEFAULT 'day_ahead',
        `seq` tinyint unsigned NOT NULL DEFAULT 0 COMMENT '0=00:30, 1=01:00 ... 47=24:00',
        `value` float NULL,
        `uploaded_at` datetime NOT NULL,
        PRIMARY KEY (`id`),
        KEY `idx_query` (`date`, `point_type`, `price_type`, `unit_name`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    "tmp_load_pv": """
        CREATE TABLE IF NOT EXISTS `tmp_load_pv` (
            `id` bigint unsigned NOT NULL AUTO_INCREMENT,
            `date` varchar(20) NOT NULL,
            `unit_name` varchar(128) NOT NULL DEFAULT '浙江电网',
            `data_type` varchar(16) NOT NULL DEFAULT 'load' COMMENT 'load / pv',
            `kind` varchar(16) NOT NULL DEFAULT 'actual' COMMENT 'actual / forecast',
            `time_label` varchar(16) NOT NULL,
            `seq` int NOT NULL DEFAULT 0,
            `value` double NULL,
            `uploaded_at` datetime NOT NULL,
            PRIMARY KEY (`id`),
            KEY `idx_query` (`date`, `data_type`, `kind`, `unit_name`),
            KEY `idx_date` (`date`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='负荷光伏临时表'
    """,
    "tmp_contract": """
        CREATE TABLE IF NOT EXISTS `tmp_contract` (
            `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
            `date` varchar(20) NOT NULL COMMENT '日期',
            `unit_name` varchar(128) NOT NULL DEFAULT '' COMMENT '交易单元',
            `time_label` varchar(16) NOT NULL COMMENT '时间标签',
            `value` decimal(18,4) NULL COMMENT '数值',
            `data_type` varchar(32) NOT NULL DEFAULT '' COMMENT '数据类型',
            `seq` int NOT NULL DEFAULT 0 COMMENT '序号',
            `uploaded_at` datetime NOT NULL COMMENT '上传时间',
            PRIMARY KEY (`id`),
            KEY `idx_query` (`date`, `unit_name`, `data_type`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='合约数据临时表';
    """,
    "tmp_rolling_spot": """
        CREATE TABLE IF NOT EXISTS `tmp_rolling_spot` (
            `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
            `op_date` varchar(20) NOT NULL COMMENT '操作日期',
            `trade_date` varchar(20) NOT NULL COMMENT '标的日',
            `time_type` varchar(32) NOT NULL COMMENT '时段(如 00:00-01:00)',
            `unit_name` varchar(128) NOT NULL COMMENT '交易单元',
            `direction` varchar(16) NOT NULL COMMENT '购电/售电',
            `qty` decimal(18,4) NOT NULL COMMENT '成交数量',
            `price` decimal(18,6) NOT NULL COMMENT '成交均价',
            `uploaded_at` datetime NOT NULL COMMENT '上传时间',
            PRIMARY KEY (`id`),
            KEY `idx_query` (`op_date`, `trade_date`, `unit_name`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='滚动现货临时表'
    """,
    "tmp_cross_province_spot": """
        CREATE TABLE IF NOT EXISTS `tmp_cross_province_spot` (
            `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
            `op_date` varchar(20) NOT NULL COMMENT '操作日期',
            `trade_date` varchar(20) NOT NULL COMMENT '标的日',
            `time_type` varchar(32) NOT NULL COMMENT '时段(如 00:00-01:00)',
            `unit_name` varchar(128) NOT NULL COMMENT '交易单元',
            `direction` varchar(16) NOT NULL COMMENT '购电/售电',
            `qty` decimal(18,4) NOT NULL COMMENT '成交数量',
            `price` decimal(18,6) NOT NULL COMMENT '成交均价',
            `trade_path` varchar(64) NOT NULL DEFAULT '' COMMENT '交易路径',
            `uploaded_at` datetime NOT NULL COMMENT '上传时间',
            PRIMARY KEY (`id`),
            KEY `idx_query` (`op_date`, `unit_name`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='跨省现货临时表'
    """,
    "tmp_contract_config": """
        CREATE TABLE IF NOT EXISTS `tmp_contract_config` (
            config_key VARCHAR(64) NOT NULL PRIMARY KEY,
            config_value LONGTEXT NOT NULL,
            updated_at DATETIME NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "tmp_unified_plants": """
        CREATE TABLE IF NOT EXISTS `tmp_unified_plants` (
            `id` bigint NOT NULL AUTO_INCREMENT,
            `plant` varchar(128) NOT NULL DEFAULT '' COMMENT '调度命名',
            `unit` varchar(128) NOT NULL DEFAULT '' COMMENT '机组序号',
            `capacity` double DEFAULT NULL COMMENT '铭牌出力',
            `city` varchar(64) NOT NULL DEFAULT '' COMMENT '所在城市',
            `uploaded_at` datetime NOT NULL COMMENT '上传时间',
            PRIMARY KEY (`id`),
            KEY `idx_city` (`city`),
            KEY `idx_plant` (`plant`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    "tmp_settlement_actual": """
        CREATE TABLE IF NOT EXISTS `tmp_settlement_actual` (
            `id` bigint NOT NULL AUTO_INCREMENT,
            `node_name` varchar(128) NOT NULL DEFAULT '',
            `date` varchar(20) NOT NULL,
            `online_qty` double DEFAULT NULL,
            `da_qty` double DEFAULT NULL, `da_price` double DEFAULT NULL, `da_fee` double DEFAULT NULL,
            `rt_qty` double DEFAULT NULL, `rt_price` double DEFAULT NULL, `rt_fee` double DEFAULT NULL,
            `cs_qty` double DEFAULT NULL, `cs_price` double DEFAULT NULL, `cs_fee` double DEFAULT NULL,
            `year_qty` double DEFAULT NULL, `year_price` double DEFAULT NULL, `year_fee` double DEFAULT NULL,
            `month_qty` double DEFAULT NULL, `month_price` double DEFAULT NULL, `month_fee` double DEFAULT NULL,
            `intraday_qty` double DEFAULT NULL, `intraday_price` double DEFAULT NULL, `intraday_fee` double DEFAULT NULL,
            `total_fee` double DEFAULT NULL,
            `uploaded_at` datetime NOT NULL,
            PRIMARY KEY (`id`),
            KEY `idx_query` (`node_name`, `date`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "tmp_settlement_query": """
        CREATE TABLE IF NOT EXISTS `tmp_settlement_query` (
            `id` bigint NOT NULL AUTO_INCREMENT,
            `node_name` varchar(128) NOT NULL DEFAULT '',
            `month` varchar(20) NOT NULL,
            `official_price` decimal(18, 6) DEFAULT NULL,
            `diff_amount` decimal(18, 6) DEFAULT NULL,
            `uploaded_at` datetime NOT NULL,
            PRIMARY KEY (`id`),
            UNIQUE KEY `idx_node_month` (`node_name`, `month`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "tmp_market_rolling": """
        CREATE TABLE IF NOT EXISTS `tmp_market_rolling` (
            `id` bigint unsigned NOT NULL AUTO_INCREMENT,
            `op_date` varchar(20) NOT NULL COMMENT '操作日期（A列标的日开始日期）',
            `trade_date_start` varchar(20) NOT NULL DEFAULT '' COMMENT '标的日开始日期',
            `trade_date_end` varchar(20) NOT NULL DEFAULT '' COMMENT '标的日结束日期',
            `time_type` varchar(32) NOT NULL COMMENT '分时段类型 如 00:00-01:00',
            `total_qty` double DEFAULT NULL COMMENT '总交易量',
            `max_price` double DEFAULT NULL COMMENT '最高价',
            `min_price` double DEFAULT NULL COMMENT '最低价',
            `avg_price` double DEFAULT NULL COMMENT '加权价格',
            `median_price` double DEFAULT NULL COMMENT '中位数价格',
            `seq` int NOT NULL DEFAULT 0 COMMENT '时段序号 0~23',
            `source_file` varchar(255) NOT NULL DEFAULT '',
            `uploaded_at` datetime NOT NULL,
            PRIMARY KEY (`id`),
            KEY `idx_query` (`op_date`, `seq`),
            KEY `idx_trade` (`trade_date_start`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='市场滚撮汇总表'
    """,
}


def _get_table_name(data_type: str, sub_type: str) -> str:
    key = f"{data_type}/{sub_type}" if sub_type else data_type
    return _TABLE_MAP.get(key, "tmp_load")


def _is_placeholder(value: str) -> bool:
    if not value:
        return True
    return any(ord(ch) > 127 for ch in value)


def db_configured() -> bool:
    return not any(
        _is_placeholder(v)
        for v in (Config.ZJ_DB_HOST, Config.ZJ_DB_USER, Config.ZJ_DB_NAME)
    )


def get_db_conn():
    # 改为连接浙江临时库
    return pymysql.connect(
        host=Config.ZJ_DB_HOST,
        port=Config.ZJ_DB_PORT,
        user=Config.ZJ_DB_USER,
        password=Config.ZJ_DB_PASS,
        database=Config.ZJ_DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        connect_timeout=_CONNECT_TIMEOUT,
        read_timeout=_READ_TIMEOUT,
        write_timeout=_WRITE_TIMEOUT,
    )


def _db_available() -> bool:
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
    logger.info(
        "[DbStore] 浙江库未配置：.env 里 ZJ_DB_HOST / ZJ_DB_USER / ZJ_DB_NAME 仍是占位值。\n"
        "          曲线数据仅保留在内存预览，重启后需重新上传。"
    )


def _mark_db_failed(reason: str = "") -> None:
    global _db_failed_until
    if not db_configured():
        _db_failed_until = time.time() + _UNCONFIGURED_COOLDOWN_SECONDS
        _warn_unconfigured_once()
        return
    _db_failed_until = time.time() + _DB_COOLDOWN_SECONDS
    logger.info(
        f"[DbStore] 浙江库不可用（{reason}），{_DB_COOLDOWN_SECONDS} 秒内跳过读写"
    )


def _mark_db_ok() -> None:
    global _db_failed_until
    _db_failed_until = 0.0


def ensure_table(table_name: str) -> bool:
    global _table_ready
    if _table_ready.get(table_name):
        return True
    if not _db_available():
        return False
    ddl = _DDL_TEMPLATES.get(table_name)
    if not ddl:
        return False
    try:
        conn = get_db_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(ddl)
        finally:
            conn.close()
        _table_ready[table_name] = True
        _mark_db_ok()
    except Exception as e:
        logger.warning(f"[DbStore] 初始化表 {table_name} 失败: {e}")
        _mark_db_failed(str(e))
    return _table_ready.get(table_name, False)


def replace_points(
    data_type: str,
    sub_type: str,
    device: str,
    date: str,
    points: List[Dict],
    source_file: str = "",
) -> int:
    table_name = _get_table_name(data_type, sub_type)
    if not ensure_table(table_name):
        raise RuntimeError(_skip_reason())

    has_unit = table_name in ("tmp_day_ahead_plant", "tmp_spread_plant")
    has_kind = table_name in ("tmp_load", "tmp_pv")

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

        if has_unit and has_kind:
            rows.append((date, device or "", t, v, sub_type or "", i, source_file, now))
        elif has_unit:
            rows.append((date, device or "", t, v, i, source_file, now))
        elif has_kind:
            rows.append((date, t, v, sub_type or "", i, source_file, now))
        else:
            rows.append((date, t, v, i, source_file, now))

    del_sql = f"DELETE FROM {table_name} WHERE `date`=%s"
    del_params = [date]
    if has_unit:
        del_sql += " AND unit_name=%s"
        del_params.append(device or "")
    if has_kind:
        del_sql += " AND kind=%s"
        del_params.append(sub_type or "")

    if has_unit and has_kind:
        ins_sql = f"INSERT INTO {table_name} (`date`, unit_name, time_label, value, kind, seq, source_file, uploaded_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
    elif has_unit:
        ins_sql = f"INSERT INTO {table_name} (`date`, unit_name, time_label, value, seq, source_file, uploaded_at) VALUES (%s,%s,%s,%s,%s,%s,%s)"
    elif has_kind:
        ins_sql = f"INSERT INTO {table_name} (`date`, time_label, value, kind, seq, source_file, uploaded_at) VALUES (%s,%s,%s,%s,%s,%s,%s)"
    else:
        ins_sql = f"INSERT INTO {table_name} (`date`, time_label, value, seq, source_file, uploaded_at) VALUES (%s,%s,%s,%s,%s,%s)"

    try:
        conn = get_db_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(del_sql, del_params)
                if rows:
                    cursor.executemany(ins_sql, rows)
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
    if not _db_available():
        return []

    table_name = _get_table_name(data_type, sub_type or "")
    if not ensure_table(table_name):
        return []

    has_unit = table_name in ("tmp_day_ahead_plant", "tmp_spread_plant")
    has_kind = table_name in ("tmp_load", "tmp_pv")

    sql = f"SELECT `date`, time_label, value"
    if has_unit:
        sql += ", unit_name"
    if has_kind:
        sql += ", kind"
    sql += f" FROM {table_name} WHERE 1=1"
    args = []

    if date:
        sql += " AND `date`=%s"
        args.append(date)
    if has_unit and device:
        sql += " AND unit_name=%s"
        args.append(device)
    if has_kind and sub_type:
        sql += " AND kind=%s"
        args.append(sub_type)
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
        logger.warning(f"[DbStore] 查询失败（{table_name}）: {e}")
        _mark_db_failed(str(e))
        return []

    grouped: Dict[tuple, Dict] = {}
    for r in rows:
        d = r["date"]
        dev = r.get("unit_name", device or "")
        k = r.get("kind", sub_type or "")
        key = (d, dev, k)
        item = grouped.setdefault(
            key,
            {"date": d, "device": dev, "kind": k, "points": []},
        )
        item["points"].append({"time": r["time_label"], "value": r["value"]})
    return list(grouped.values())


# ================= 新增写入函数 =================
def save_rolling_spot(records: List[Dict], source_file: str = "") -> int:
    if not ensure_table("tmp_rolling_spot"):
        raise RuntimeError(_skip_reason())

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for r in records:
        rows.append(
            (
                r["op_date"],
                r["trade_date"],
                r["time_type"],
                r["unit_name"],
                r["direction"],
                r["qty"],
                r["price"],
                now,
            )
        )

    sql = (
        "INSERT INTO tmp_rolling_spot "
        "(op_date, trade_date, time_type, unit_name, direction, qty, price, uploaded_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            # 按操作日期和交易单元清理旧数据
            del_keys = set(
                (r["op_date"], r["trade_date"], r["unit_name"]) for r in records
            )
            for op_date, trade_date, unit_name in del_keys:
                cursor.execute(
                    "DELETE FROM tmp_rolling_spot WHERE op_date=%s AND trade_date=%s AND unit_name=%s",
                    (op_date, trade_date, unit_name),
                )
            cursor.executemany(sql, rows)
        conn.close()
        _mark_db_ok()
    except Exception as e:
        _mark_db_failed(str(e))
        raise
    return len(rows)


# ================= 新增读取函数 =================
def fetch_rolling_spot(unit_name: str, start_date: str, end_date: str) -> List[Dict]:
    """读取某节点某时间段的滚撮数据（按操作日期过滤）"""
    if not ensure_table("tmp_rolling_spot"):
        return []

    sql = (
        "SELECT op_date, trade_date, time_type, unit_name, direction, qty, price "
        "FROM tmp_rolling_spot "
        "WHERE unit_name LIKE %s AND op_date >= %s AND op_date <= %s "
        "ORDER BY op_date, trade_date, time_type"
    )
    like_name = f"%{unit_name}%"

    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql, (like_name, start_date, end_date))
            rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.warning(f"[DbStore] 查询滚撮数据失败: {e}")
        return []


# 2. 在文件末尾新增两个函数：
def save_cross_province_spot(records: List[Dict], source_file: str = "") -> int:
    """保存长三角省间滚撮数据"""
    if not ensure_table("tmp_cross_province_spot"):
        raise RuntimeError(_skip_reason())

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for r in records:
        rows.append(
            (
                r["op_date"],
                r["trade_date"],
                r["time_type"],
                r["unit_name"],
                r["direction"],
                r["qty"],
                r["price"],
                r["trade_path"],
                now,
            )
        )

    sql = (
        "INSERT INTO tmp_cross_province_spot "
        "(op_date, trade_date, time_type, unit_name, direction, qty, price, trade_path, uploaded_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            del_keys = set(
                (r["op_date"], r["trade_date"], r["unit_name"]) for r in records
            )
            for op_date, trade_date, unit_name in del_keys:
                cursor.execute(
                    "DELETE FROM tmp_cross_province_spot WHERE op_date=%s AND trade_date=%s AND unit_name=%s",
                    (op_date, trade_date, unit_name),
                )
            cursor.executemany(sql, rows)
        conn.close()
        _mark_db_ok()
    except Exception as e:
        _mark_db_failed(str(e))
        raise
    return len(rows)


def fetch_cross_province_spot(
    unit_name: str, start_date: str, end_date: str
) -> List[Dict]:
    """读取省间滚撮数据"""
    if not ensure_table("tmp_cross_province_spot"):
        return []

    sql = (
        "SELECT op_date, trade_date, time_type, unit_name, direction, qty, price, trade_path "
        "FROM tmp_cross_province_spot "
        "WHERE unit_name LIKE %s AND op_date >= %s AND op_date <= %s "
        "ORDER BY op_date, trade_date, time_type"
    )
    like_name = f"%{unit_name}%"

    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql, (like_name, start_date, end_date))
            rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.warning(f"[DbStore] 查询省间数据失败: {e}")
        return []


def save_contract_data(records: List[Dict], data_type: str) -> int:
    """保存合约数据（年/月/旬/实际）—— 相同 (date, unit, time_label) 自动累加"""
    if not ensure_table("tmp_contract"):
        raise RuntimeError(_skip_reason())

    # ⭐ 合并相同 (date, unit_name, time_label) 的记录，value 相加
    merged: Dict[tuple, Dict] = {}
    for r in records:
        key = (r["date"], r["unit_name"], r["time_label"])
        if key in merged:
            merged[key]["value"] += float(r["value"] or 0)
            # seq 取最后一次的（同一时段 seq 应一致，保险起见）
            merged[key]["seq"] = r["seq"]
        else:
            merged[key] = {
                "date": r["date"],
                "unit_name": r["unit_name"],
                "time_label": r["time_label"],
                "value": float(r["value"] or 0),
                "seq": r["seq"],
            }

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for r in merged.values():
        rows.append(
            (
                r["date"],
                r["unit_name"],
                r["time_label"],
                r["value"],
                data_type,
                r["seq"],
                now,
            )
        )

    sql = (
        "INSERT INTO tmp_contract "
        "(date, unit_name, time_label, value, data_type, seq, uploaded_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s)"
    )

    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            del_keys = set((r["date"], r["unit_name"]) for r in merged.values())
            for date, unit_name in del_keys:
                cursor.execute(
                    "DELETE FROM tmp_contract WHERE `date`=%s AND unit_name=%s AND data_type=%s",
                    (date, unit_name, data_type),
                )
            cursor.executemany(sql, rows)
        conn.close()
        _mark_db_ok()
    except Exception as e:
        _mark_db_failed(str(e))
        raise
    return len(rows)


def fetch_contract_data(unit_name: str, start_date: str, end_date: str) -> List[Dict]:
    """读取合约数据"""
    if not ensure_table("tmp_contract"):
        return []

    sql = (
        "SELECT `date`, unit_name, time_label, value, data_type, seq "
        "FROM tmp_contract "
        "WHERE unit_name LIKE %s AND `date` >= %s AND `date` <= %s "
        "ORDER BY `date`, data_type, seq"
    )
    like_name = f"%{unit_name}%"

    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql, (like_name, start_date, end_date))
            rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.warning(f"[DbStore] 查询合约数据失败: {e}")
        return []


# 2. 在文件末尾补充两个函数：
def save_contract_config(key: str, value: str) -> None:
    """保存合约基础配置（典型曲线/节假日）"""
    if not ensure_table("tmp_contract_config"):
        raise RuntimeError("数据库不可用")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            sql = (
                "INSERT INTO tmp_contract_config (config_key, config_value, updated_at) "
                "VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE config_value=VALUES(config_value), updated_at=VALUES(updated_at)"
            )
            cursor.execute(sql, (key, value, now))
        conn.close()
        _mark_db_ok()
    except Exception as e:
        _mark_db_failed(str(e))
        raise


def fetch_contract_config(key: str) -> str:
    """读取合约基础配置"""
    if not ensure_table("tmp_contract_config"):
        return ""
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT config_value FROM tmp_contract_config WHERE config_key=%s",
                (key,),
            )
            row = cursor.fetchone()
        conn.close()
        return row["config_value"] if row else ""
    except Exception as e:
        logger.warning(f"[DbStore] 读取配置 {key} 失败: {e}")
        return ""


def replace_unified_plants(records: List[Dict]) -> int:
    """覆盖式写入统调电厂数据"""
    if not ensure_table("tmp_unified_plants"):
        raise RuntimeError(_skip_reason())

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for r in records:
        rows.append(
            (
                r.get("plant", ""),
                r.get("unit", ""),
                r.get("capacity"),
                r.get("city", ""),
                now,
            )
        )

    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            # 先清空整张表
            cursor.execute("TRUNCATE TABLE tmp_unified_plants")
            if rows:
                sql = "INSERT INTO tmp_unified_plants (plant, unit, capacity, city, uploaded_at) VALUES (%s,%s,%s,%s,%s)"
                cursor.executemany(sql, rows)
        conn.close()
        _mark_db_ok()
    except Exception as e:
        _mark_db_failed(str(e))
        raise
    return len(rows)


def fetch_unified_plants_count() -> int:
    """获取总记录数"""
    if not ensure_table("tmp_unified_plants"):
        return 0
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as c FROM tmp_unified_plants")
            res = cursor.fetchone()
        conn.close()
        return res["c"] if res else 0
    except Exception:
        return 0


def fetch_unified_plants(
    page: int = 1, page_size: int = 20, keyword: str = "", city: str = ""
) -> Dict:
    """分页查询"""
    if not ensure_table("tmp_unified_plants"):
        return {"total": 0, "items": []}

    where_clauses = []
    args = []
    if keyword:
        where_clauses.append("(plant LIKE %s OR unit LIKE %s OR city LIKE %s)")
        kw = f"%{keyword}%"
        args.extend([kw, kw, kw])
    if city:
        where_clauses.append("city = %s")
        args.append(city)

    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            # 查总数
            cursor.execute(
                f"SELECT COUNT(*) as c FROM tmp_unified_plants{where_sql}", args
            )
            total = cursor.fetchone()["c"]

            # 查分页
            offset = (page - 1) * page_size
            sql = f"SELECT id, plant, unit, capacity, city FROM tmp_unified_plants{where_sql} ORDER BY city, plant, unit LIMIT %s OFFSET %s"
            cursor.execute(sql, args + [page_size, offset])
            items = cursor.fetchall()
        conn.close()
        return {"total": total, "items": items}
    except Exception as e:
        logger.warning(f"[DbStore] 查询统调电厂失败: {e}")
        return {"total": 0, "items": []}


def fetch_unified_plants_map() -> List[Dict]:
    """地图聚合（按城市）"""
    if not ensure_table("tmp_unified_plants"):
        return []
    sql = """
        SELECT 
            city, 
            COUNT(DISTINCT plant) as plantCount, 
            COUNT(*) as unitCount, 
            SUM(capacity) as totalCapacity 
        FROM tmp_unified_plants 
        WHERE city IS NOT NULL AND city != ''
        GROUP BY city 
        ORDER BY totalCapacity DESC
    """
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.warning(f"[DbStore] 查询统调电厂地图失败: {e}")
        return []


def fetch_unified_plant_cities() -> List[str]:
    """获取去重后的城市列表"""
    if not ensure_table("tmp_unified_plants"):
        return []
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT city FROM tmp_unified_plants WHERE city != '' ORDER BY city"
            )
            rows = cursor.fetchall()
        conn.close()
        return [r["city"] for r in rows]
    except Exception:
        return []


def clear_unified_plants() -> None:
    """清空统调电厂数据"""
    if not ensure_table("tmp_unified_plants"):
        return
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE tmp_unified_plants")
        conn.close()
    except Exception as e:
        logger.warning(f"[DbStore] 清空统调电厂失败: {e}")


def add_unified_plant(record: Dict) -> int:
    """新增单条统调电厂记录"""
    if not ensure_table("tmp_unified_plants"):
        raise RuntimeError(_skip_reason())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            sql = "INSERT INTO tmp_unified_plants (plant, unit, capacity, city, uploaded_at) VALUES (%s,%s,%s,%s,%s)"
            cursor.execute(
                sql,
                (
                    record.get("plant", ""),
                    record.get("unit", ""),
                    record.get("capacity"),
                    record.get("city", ""),
                    now,
                ),
            )
            new_id = cursor.lastrowid
        conn.close()
        _mark_db_ok()
        return new_id
    except Exception as e:
        _mark_db_failed(str(e))
        raise


def update_unified_plant(record_id: int, record: Dict) -> int:
    """修改单条统调电厂记录"""
    if not ensure_table("tmp_unified_plants"):
        raise RuntimeError(_skip_reason())
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            sql = "UPDATE tmp_unified_plants SET plant=%s, unit=%s, capacity=%s, city=%s WHERE id=%s"
            cursor.execute(
                sql,
                (
                    record.get("plant", ""),
                    record.get("unit", ""),
                    record.get("capacity"),
                    record.get("city", ""),
                    record_id,
                ),
            )
        conn.close()
        _mark_db_ok()
        return record_id
    except Exception as e:
        _mark_db_failed(str(e))
        raise


def delete_unified_plants_batch(ids: List[int]) -> int:
    """批量删除统调电厂记录"""
    if not ids:
        return 0
    if not ensure_table("tmp_unified_plants"):
        raise RuntimeError(_skip_reason())
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            format_strings = ",".join(["%s"] * len(ids))
            sql = f"DELETE FROM tmp_unified_plants WHERE id IN ({format_strings})"
            cursor.execute(sql, tuple(ids))
            deleted = cursor.rowcount
        conn.close()
        _mark_db_ok()
        return deleted
    except Exception as e:
        _mark_db_failed(str(e))
        raise


def save_settlement_actual(records: List[Dict]) -> int:
    if not ensure_table("tmp_settlement_actual"):
        raise RuntimeError(_skip_reason())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for r in records:
        rows.append(
            (
                r["node_name"],
                r["date"],
                r.get("online_qty"),
                r.get("da_qty"),
                r.get("da_price"),
                r.get("da_fee"),
                r.get("rt_qty"),
                r.get("rt_price"),
                r.get("rt_fee"),
                r.get("cs_qty"),
                r.get("cs_price"),
                r.get("cs_fee"),
                r.get("year_qty"),
                r.get("year_price"),
                r.get("year_fee"),
                r.get("month_qty"),
                r.get("month_price"),
                r.get("month_fee"),
                r.get("intraday_qty"),
                r.get("intraday_price"),
                r.get("intraday_fee"),
                r.get("total_fee"),
                now,
            )
        )
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            for r in records:
                cursor.execute(
                    "DELETE FROM tmp_settlement_actual WHERE node_name=%s AND `date`=%s",
                    (r["node_name"], r["date"]),
                )
            if rows:
                sql = "INSERT INTO tmp_settlement_actual (node_name, `date`, online_qty, da_qty, da_price, da_fee, rt_qty, rt_price, rt_fee, cs_qty, cs_price, cs_fee, year_qty, year_price, year_fee, month_qty, month_price, month_fee, intraday_qty, intraday_price, intraday_fee, total_fee, uploaded_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                cursor.executemany(sql, rows)
        conn.close()
        _mark_db_ok()
    except Exception as e:
        _mark_db_failed(str(e))
        raise
    return len(rows)


def fetch_settlement_actual(node_name: str) -> List[Dict]:
    if not ensure_table("tmp_settlement_actual"):
        return []
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM tmp_settlement_actual WHERE node_name=%s ORDER BY `date`",
                (node_name,),
            )
            rows = cursor.fetchall()
        conn.close()
        for r in rows:
            if "uploaded_at" in r and r["uploaded_at"]:
                r["uploaded_at"] = str(r["uploaded_at"])
        return rows
    except Exception as e:
        logger.warning(f"[DbStore] 查询实际结算单失败: {e}")
        return []


def save_official_price(
    node_name: str,
    month: str,
    official_price: float = None,
    diff_amount: float = None,
    simulated_fee: float = None,
) -> None:
    if not ensure_table("tmp_settlement_query"):
        raise RuntimeError(_skip_reason())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO tmp_settlement_query (node_name, month, official_price, diff_amount, simulated_fee, uploaded_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    official_price=COALESCE(VALUES(official_price), official_price), 
                    diff_amount=COALESCE(VALUES(diff_amount), diff_amount), 
                    simulated_fee=COALESCE(VALUES(simulated_fee), simulated_fee), 
                    uploaded_at=VALUES(uploaded_at)
            """
            cursor.execute(
                sql, (node_name, month, official_price, diff_amount, simulated_fee, now)
            )
        conn.close()
        _mark_db_ok()
    except Exception as e:
        _mark_db_failed(str(e))
        raise


def fetch_official_prices(month: str) -> Dict[str, Dict]:
    """获取某月所有节点的配置（包括官方均价、差额、模拟电费）"""
    if not ensure_table("tmp_settlement_query"):
        return {}
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT node_name, official_price, diff_amount, simulated_fee FROM tmp_settlement_query WHERE month=%s",
                (month,),
            )
            rows = cursor.fetchall()
        conn.close()

        # 把结果转成字典，方便前端直接通过节点名取
        result = {}
        for r in rows:
            result[r["node_name"]] = {
                "official_price": (
                    float(r["official_price"])
                    if r["official_price"] is not None
                    else None
                ),
                "diff_amount": (
                    float(r["diff_amount"]) if r["diff_amount"] is not None else None
                ),
                "simulated_fee": (
                    float(r["simulated_fee"])
                    if r["simulated_fee"] is not None
                    else None
                ),
            }
        return result
    except Exception as e:
        logger.warning(f"[DbStore] 查询配置失败: {e}")
        return {}


# ================= 市场滚撮（市场级汇总） =================
def save_market_rolling(records: List[Dict], source_file: str = "") -> int:
    """保存市场滚撮数据。按 (op_date, seq) 覆盖：同日期同时段只保留一份"""
    if not ensure_table("tmp_market_rolling"):
        raise RuntimeError(_skip_reason())

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    op_dates = set()
    for r in records:
        rows.append(
            (
                r["op_date"],
                r.get("trade_date_start", r["op_date"]),
                r.get("trade_date_end", r["op_date"]),
                r["time_type"],
                r.get("total_qty"),
                r.get("max_price"),
                r.get("min_price"),
                r.get("avg_price"),
                r.get("median_price"),
                r.get("seq", 0),
                source_file,
                now,
            )
        )
        op_dates.add(r["op_date"])

    sql = (
        "INSERT INTO tmp_market_rolling "
        "(op_date, trade_date_start, trade_date_end, time_type, "
        "total_qty, max_price, min_price, avg_price, median_price, seq, source_file, uploaded_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            # 清空本次涉及的操作日期（整体覆盖）
            for d in op_dates:
                cursor.execute("DELETE FROM tmp_market_rolling WHERE op_date=%s", (d,))
            if rows:
                cursor.executemany(sql, rows)
        conn.close()
        _mark_db_ok()
    except Exception as e:
        _mark_db_failed(str(e))
        raise
    return len(rows)


def fetch_market_rolling(op_date: str) -> Dict[int, Dict]:
    """查某操作日的市场滚撮，返回 {seq: {time_type, avg_price, total_qty, ...}}"""
    if not ensure_table("tmp_market_rolling"):
        return {}

    sql = (
        "SELECT op_date, trade_date_start, trade_date_end, time_type, "
        "total_qty, max_price, min_price, avg_price, median_price, seq "
        "FROM tmp_market_rolling WHERE op_date=%s ORDER BY seq"
    )
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql, (op_date,))
            rows = cursor.fetchall()
        conn.close()
    except Exception as e:
        logger.warning(f"[DbStore] 查询市场滚撮失败: {e}")
        return {}

    return {
        int(r["seq"]): {
            "time_type": r["time_type"],
            "total_qty": float(r["total_qty"] or 0),
            "max_price": float(r["max_price"] or 0),
            "min_price": float(r["min_price"] or 0),
            "avg_price": float(r["avg_price"] or 0),
            "median_price": float(r["median_price"] or 0),
        }
        for r in rows
    }


def fetch_market_rolling_dates() -> List[str]:
    """查已有数据的操作日期列表（供前端日期选择器提示）"""
    if not ensure_table("tmp_market_rolling"):
        return []
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT op_date FROM tmp_market_rolling ORDER BY op_date DESC"
            )
            rows = cursor.fetchall()
        conn.close()
        return [r["op_date"] for r in rows]
    except Exception:
        return []


# ================= 价格临时表（统一结算点/节点 × 日前/实时） =================
def save_price(records: List[Dict], point_type: str, price_type: str) -> int:
    """按 (date, point_type, unit_name, price_type) 覆盖写入"""
    if not ensure_table("tmp_price"):
        raise RuntimeError(_skip_reason())

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    keys = set()
    for r in records:
        rows.append(
            (
                r["date"],
                point_type,
                r.get("unit_name", "") or "",
                price_type,
                r["time_label"],
                int(r.get("seq", 0)),
                r.get("value"),
                now,
            )
        )
        keys.add((r["date"], r.get("unit_name", "") or ""))

    sql = (
        "INSERT INTO tmp_price "
        "(date, point_type, unit_name, price_type, time_label, seq, value, uploaded_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            for date, unit_name in keys:
                cursor.execute(
                    "DELETE FROM tmp_price WHERE `date`=%s AND point_type=%s AND price_type=%s AND unit_name=%s",
                    (date, point_type, price_type, unit_name),
                )
            if rows:
                cursor.executemany(sql, rows)
        conn.close()
        _mark_db_ok()
    except Exception as e:
        _mark_db_failed(str(e))
        raise
    return len(rows)


def fetch_price(
    date: str,
    point_type: str,
    price_type: str,
    unit_name: Optional[str] = None,
) -> List[Dict]:
    """读浙江库。unit_name=None 时返回该 point_type 下全部节点"""
    if not ensure_table("tmp_price"):
        return []
    sql = (
        "SELECT `date`, point_type, unit_name, price_type, time_label, seq, value "
        "FROM tmp_price WHERE `date`=%s AND point_type=%s AND price_type=%s"
    )
    args = [date, point_type, price_type]
    if unit_name is not None:
        sql += " AND unit_name=%s"
        args.append(unit_name)
    sql += " ORDER BY seq"
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql, args)
            rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.warning(f"[DbStore] 查询价格失败: {e}")
        return []


def clear_price(
    date: str,
    point_type: str,
    price_type: str,
    unit_name: Optional[str] = None,
) -> int:
    if not ensure_table("tmp_price"):
        return 0
    sql = "DELETE FROM tmp_price WHERE `date`=%s AND point_type=%s AND price_type=%s"
    args = [date, point_type, price_type]
    if unit_name is not None:
        sql += " AND unit_name=%s"
        args.append(unit_name)
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql, args)
            count = cursor.rowcount
        conn.close()

        # ⭐ 新增日志输出
        if count > 0:
            logger.info(
                f"[DbStore] 江苏库命中，清理浙江库：{date} | {point_type} | {price_type} | {unit_name}，共删除 {count} 条"
            )
        return count
    except Exception as e:
        logger.warning(f"[DbStore] 清理价格数据失败: {e}")
        return 0


# ================= 负荷光伏临时表（实际/预测 × 负荷/光伏） =================
def save_load_pv(records: List[Dict], data_type: str, kind: str) -> int:
    """按 (date, unit_name, data_type, kind) 覆盖写入"""
    if not ensure_table("tmp_load_pv"):
        raise RuntimeError(_skip_reason())

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    keys = set()
    for r in records:
        rows.append(
            (
                r["date"],
                r.get("unit_name", "") or "浙江电网",
                data_type,
                kind,
                r["time_label"],
                int(r.get("seq", 0)),
                r.get("value"),
                now,
            )
        )
        keys.add((r["date"], r.get("unit_name", "") or "浙江电网"))

    sql = (
        "INSERT INTO tmp_load_pv "
        "(date, unit_name, data_type, kind, time_label, seq, value, uploaded_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
    )

    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            for date, unit_name in keys:
                cursor.execute(
                    "DELETE FROM tmp_load_pv WHERE `date`=%s AND unit_name=%s AND data_type=%s AND kind=%s",
                    (date, unit_name, data_type, kind),
                )
            if rows:
                cursor.executemany(sql, rows)
        conn.close()
        _mark_db_ok()
    except Exception as e:
        _mark_db_failed(str(e))
        raise
    return len(rows)


def fetch_load_pv(
    date: str,
    data_type: str,
    kind: str,
    unit_name: Optional[str] = None,
) -> List[Dict]:
    """读浙江库"""
    if not ensure_table("tmp_load_pv"):
        return []
    sql = (
        "SELECT `date`, unit_name, data_type, kind, time_label, seq, value "
        "FROM tmp_load_pv WHERE `date`=%s AND data_type=%s AND kind=%s"
    )
    args = [date, data_type, kind]
    if unit_name is not None:
        sql += " AND unit_name=%s"
        args.append(unit_name)
    sql += " ORDER BY seq"
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql, args)
            rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.warning(f"[DbStore] 查询负荷光伏失败: {e}")
        return []


def clear_load_pv(
    date: str,
    data_type: str,
    kind: str,
    unit_name: Optional[str] = None,
) -> int:
    """江苏库命中时清理浙江库对应数据"""
    if not ensure_table("tmp_load_pv"):
        return 0
    sql = "DELETE FROM tmp_load_pv WHERE `date`=%s AND data_type=%s AND kind=%s"
    args = [date, data_type, kind]
    if unit_name is not None:
        sql += " AND unit_name=%s"
        args.append(unit_name)
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql, args)
            count = cursor.rowcount
        conn.close()
        return count
    except Exception:
        return 0


def fetch_price_range(
    start_date: str,
    end_date: str,
    point_type: str,
    price_type: str,
    unit_name: Optional[str] = None,
) -> List[Dict]:
    """浙江库价格范围查询（一次拿整段）"""
    if not ensure_table("tmp_price"):
        return []
    sql = (
        "SELECT `date`, unit_name, time_label, seq, value "
        "FROM tmp_price WHERE `date`>=%s AND `date`<=%s "
        "AND point_type=%s AND price_type=%s"
    )
    args = [start_date, end_date, point_type, price_type]
    if unit_name is not None:
        sql += " AND unit_name=%s"
        args.append(unit_name)
    sql += " ORDER BY `date`, seq"
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql, args)
            rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.warning(f"[DbStore] 范围查询价格失败: {e}")
        return []


def fetch_load_pv_range(
    start_date: str,
    end_date: str,
    data_type: str,
    kind: str,
    unit_name: Optional[str] = None,
) -> List[Dict]:
    if not ensure_table("tmp_load_pv"):
        return []
    sql = (
        "SELECT `date`, unit_name, time_label, seq, value "
        "FROM tmp_load_pv WHERE `date`>=%s AND `date`<=%s "
        "AND data_type=%s AND kind=%s"
    )
    args = [start_date, end_date, data_type, kind]
    if unit_name is not None:
        sql += " AND unit_name=%s"
        args.append(unit_name)
    sql += " ORDER BY `date`, seq"
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql, args)
            rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception:
        return []
