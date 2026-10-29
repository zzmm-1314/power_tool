"""临时数据管理：本地文件与数据库双支持"""

import os
import re
import shutil
from datetime import datetime
from typing import Optional, List, Dict, Tuple
import pandas as pd
from io import BytesIO
import pymysql
from config import Config

_INVALID_CHARS = re.compile(r'[\\/:*?"<>|]+')


def _safe(name: str) -> str:
    if not name:
        return ""
    return _INVALID_CHARS.sub("_", str(name).strip()).strip("._") or "unnamed"


def get_db_conn():
    return pymysql.connect(
        host=getattr(Config, "DB_HOST", "localhost"),
        user=getattr(Config, "DB_USER", "root"),
        password=getattr(Config, "DB_PASS", ""),
        database=getattr(Config, "DB_NAME", "power_tool"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def init_temp_table():
    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS temp_data (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    data_type VARCHAR(50) NOT NULL,
                    sub_type VARCHAR(50) DEFAULT '',
                    node_name VARCHAR(100) DEFAULT '',
                    date VARCHAR(20) DEFAULT '',
                    filename VARCHAR(255) NOT NULL,
                    file_content LONGBLOB NOT NULL,
                    uploaded_at DATETIME NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending'
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
        conn.close()
    except Exception as e:
        print(f"[Temp] 初始化临时表失败: {e}")


init_temp_table()


class TempManager:
    """兼容本地文件系统和数据库的临时数据管理"""

    @staticmethod
    def base_dir() -> str:
        """本地读取根目录（供旧代码扫描文件用）"""
        d = os.path.join(os.path.dirname(__file__), "..", "data", "temp")
        os.makedirs(d, exist_ok=True)
        return d

    @staticmethod
    def write_dir() -> str:
        """本地写入根目录"""
        return TempManager.base_dir()

    @staticmethod
    def mirror_to_local(cloud_path: str) -> None:
        pass

    @staticmethod
    def mirror_path_to_local(relpath: str) -> None:
        pass

    @staticmethod
    def resolve_path(
        data_type: str, sub_type: str, date: str, node_name: Optional[str] = None
    ) -> str:
        parts = [TempManager.write_dir(), _safe(data_type)]
        if sub_type:
            parts.append(_safe(sub_type))
        if node_name:
            parts.append(_safe(node_name))
        parts.append(f"{_safe(date)}.xlsx")
        return os.path.join(*parts)

    @staticmethod
    def save(
        file_storage,
        data_type: str,
        sub_type: str,
        date: str,
        node_name: Optional[str] = None,
    ) -> str:
        # 1. 写入数据库
        filename = os.path.basename(file_storage.filename or "upload.xlsx")
        file_content = file_storage.read()

        conn = get_db_conn()
        try:
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO temp_data (data_type, sub_type, node_name, date, filename, file_content, uploaded_at) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(
                    sql,
                    (
                        data_type,
                        sub_type,
                        node_name or "",
                        date,
                        filename,
                        file_content,
                        datetime.now(),
                    ),
                )
                new_id = cursor.lastrowid
        finally:
            conn.close()

        # 2. 同时保存到本地文件，供 day_ahead 等旧逻辑扫描
        path = TempManager.resolve_path(data_type, sub_type, date, node_name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(file_content)

        return f"id:{new_id}"

    @staticmethod
    def save_raw(file_storage, data_type: str, sub_type: str = "") -> str:
        filename = os.path.basename(file_storage.filename or "upload.xlsx")
        ext = os.path.splitext(filename)[1].lower()
        if ext not in (".xlsx", ".xls"):
            filename += ".xlsx"

        file_content = file_storage.read()

        # 1. 写数据库
        conn = get_db_conn()
        try:
            with conn.cursor() as cursor:
                sql = "INSERT INTO temp_data (data_type, sub_type, filename, file_content, uploaded_at) VALUES (%s, %s, %s, %s, %s)"
                cursor.execute(
                    sql, (data_type, sub_type, filename, file_content, datetime.now())
                )
                new_id = cursor.lastrowid
        finally:
            conn.close()

        # 2. 写本地
        parts = [TempManager.base_dir(), _safe(data_type)]
        if sub_type:
            for seg in sub_type.split("/"):
                if seg.strip():
                    parts.append(_safe(seg.strip()))
        base = os.path.join(*parts)
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, filename)
        with open(path, "wb") as f:
            f.write(file_content)

        return f"id:{new_id}"

    @staticmethod
    def load(
        data_type: str, sub_type: str, date: str, node_name: Optional[str] = None
    ) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        # 先从本地文件系统找（为了兼容已有的按列读取逻辑）
        rel_parts = [_safe(data_type)]
        if sub_type:
            rel_parts.append(_safe(sub_type))
        if node_name:
            rel_parts.append(_safe(node_name))
        rel_parts.append(f"{_safe(date)}.xlsx")

        local_path = os.path.join(TempManager.base_dir(), *rel_parts)
        if os.path.exists(local_path):
            try:
                return pd.read_excel(local_path), local_path
            except Exception as e:
                print(f"[Temp] 读取本地失败 {local_path}: {e}")

        # 兜底从数据库找
        conn = get_db_conn()
        try:
            with conn.cursor() as cursor:
                sql = "SELECT file_content FROM temp_data WHERE data_type=%s"
                params = [data_type]
                if sub_type:
                    sql += " AND sub_type=%s"
                    params.append(sub_type)
                if date:
                    sql += " AND date=%s"
                    params.append(date)
                if node_name:
                    sql += " AND node_name=%s"
                    params.append(node_name)
                cursor.execute(sql, params)
                row = cursor.fetchone()
                if row:
                    return pd.read_excel(BytesIO(row["file_content"])), None
                return None, None
        finally:
            conn.close()

    @staticmethod
    def list_all() -> List[Dict]:
        conn = get_db_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, data_type, sub_type, node_name, date, 
                           filename, uploaded_at, LENGTH(file_content) as size
                    FROM temp_data ORDER BY uploaded_at DESC
                """)
                rows = cursor.fetchall()
                items = []
                for r in rows:
                    items.append(
                        {
                            "path": f"id:{r['id']}",
                            "dataType": r["data_type"],
                            "subType": r["sub_type"],
                            "nodeName": r["node_name"],
                            "date": r["date"],
                            "fileName": r["filename"],
                            "size": r["size"],
                            "uploadedAt": r["uploaded_at"].strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
                        }
                    )
                return items
        finally:
            conn.close()

    @staticmethod
    def delete_by_relpath(relpath: str) -> bool:
        if relpath.startswith("id:"):
            file_id = relpath.replace("id:", "")
            conn = get_db_conn()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM temp_data WHERE id=%s", (file_id,))
                    return cursor.rowcount > 0
            finally:
                conn.close()

        # 兼容本地路径删除
        full = os.path.join(TempManager.base_dir(), relpath)
        if os.path.exists(full):
            try:
                os.remove(full)
                return True
            except Exception:
                pass
        return False
