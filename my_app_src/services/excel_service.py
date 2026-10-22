"""Excel 读取 / 写入服务（骨架）"""

import os
import pandas as pd


class ExcelService:
    @staticmethod
    def read_sheet(file_path: str, sheet_name=0, **kwargs) -> pd.DataFrame:
        """读取 Excel 指定 sheet 为 DataFrame"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        return pd.read_excel(file_path, sheet_name=sheet_name, **kwargs)

    @staticmethod
    def write_sheet(df: pd.DataFrame, file_path: str, sheet_name="Sheet1"):
        """将 DataFrame 写入 Excel（追加/覆盖由调用方控制）"""
        df.to_excel(file_path, sheet_name=sheet_name, index=False)

    @staticmethod
    def append_rows(file_path: str, rows: list[dict], sheet_name="Sheet1"):
        """向已有 Excel 追加行（骨架示例）"""
        if os.path.exists(file_path):
            old = pd.read_excel(file_path, sheet_name=sheet_name)
            new = pd.concat([old, pd.DataFrame(rows)], ignore_index=True)
        else:
            new = pd.DataFrame(rows)
        new.to_excel(file_path, sheet_name=sheet_name, index=False)
        return len(rows)
