"""导入落数：解析结果先进内存预览，再尽力写入数据库

- 预览一定成功：只要解析出数据，页面就能立即显示
- 入库是尽力而为：数据库不可用（未配置 / 无权限 / 连接失败）时只打印日志，
  不影响本次预览，也不让上传接口报错
"""

from typing import Dict, List, Optional

from services import preview_store


def store_points(
    data_type: str,
    sub_type: str,
    device: str,
    date: str,
    points: List[Dict],
    source_file: str = "",
) -> Dict:
    """写入一个维度的数据，返回 {"preview": int, "saved": bool, "dbError": str}"""
    preview_count = preview_store.replace_points(
        data_type, sub_type, device, date, points, source_file=source_file
    )

    saved = False
    db_error = ""
    try:
        from services.db_store import replace_points as db_replace

        db_replace(
            data_type, sub_type, device, date, points, source_file=source_file
        )
        saved = True
    except Exception as e:
        db_error = str(e)
        print(
            f"[Ingest] 预览已生效，但写入数据库失败"
            f"（{data_type}/{sub_type}/{device}/{date}）: {e}"
        )

    return {"preview": preview_count, "saved": saved, "dbError": db_error}
