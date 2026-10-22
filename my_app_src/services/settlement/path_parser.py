"""路径识别：从选择的文件/文件夹中自动匹配各类型 Excel"""

import os
from typing import Dict, List


def parse_paths_from_files(paths: List[str]) -> Dict:
    excel_files = []
    for p in paths:
        p = (p or "").strip()
        if not p:
            continue
        if os.path.isdir(p):
            for f in os.listdir(p):
                full = os.path.join(p, f)
                if (
                    os.path.isfile(full)
                    and f.endswith(".xlsx")
                    and not f.startswith("~$")
                ):
                    excel_files.append(full)
        elif (
            os.path.isfile(p)
            and p.endswith(".xlsx")
            and not os.path.basename(p).startswith("~$")
        ):
            excel_files.append(p)

    if not excel_files:
        return {"error": "未找到有效的 Excel 文件"}

    found: Dict[str, str] = {}
    unmatched = list(excel_files)

    def take(key, keywords):
        for f in list(unmatched):
            b = os.path.basename(f)
            if any(kw in b for kw in keywords):
                found[key] = f
                unmatched.remove(f)
                return True
        return False

    info_refs = []
    for f in list(unmatched):
        b = os.path.basename(f)
        if any(k in b for k in ["信息参考", "价格参考", "分时价格"]):
            info_refs.append(f)
            unmatched.remove(f)
    if info_refs:
        found["info_file"] = info_refs[0]
        found["info_spot_file"] = info_refs[0]
        found["info_contract_file"] = info_refs[0]

    take("spot_file", ["现货申报"])
    take("fixed_file", ["固定申报功率"])
    take("strategy_file_v2", ["年月分解", "旬度分解"])
    take("strategy_file", ["月度策略"])
    take("stat_file_v2", ["电厂数据统计"])
    take("stat_file", ["数据统计"])
    take("target_file_v2", ["模拟结算单"])
    take("target_file", ["模拟结算"])

    if "strategy_file" in found and "strategy_file_v2" not in found:
        found["strategy_file_v2"] = found["strategy_file"]
    if "strategy_file_v2" in found and "strategy_file" not in found:
        found["strategy_file"] = found["strategy_file_v2"]
    if "stat_file" in found and "stat_file_v2" not in found:
        found["stat_file_v2"] = found["stat_file"]
    if "stat_file_v2" in found and "stat_file" not in found:
        found["stat_file"] = found["stat_file_v2"]
    if "target_file" in found and "target_file_v2" not in found:
        found["target_file_v2"] = found["target_file"]
    if "target_file_v2" in found and "target_file" not in found:
        found["target_file"] = found["target_file_v2"]

    detail_folder = None
    for p in paths:
        if os.path.isdir(p) and "明细" in p:
            detail_folder = p
            break

    return {
        "detail_folder": detail_folder or "",
        "spot_file": found.get("spot_file", ""),
        "fixed_file": found.get("fixed_file", ""),
        "strategy_file": found.get("strategy_file", ""),
        "strategy_file_v2": found.get("strategy_file_v2", ""),
        "stat_file": found.get("stat_file", ""),
        "stat_file_v2": found.get("stat_file_v2", ""),
        "info_file": found.get("info_file", ""),
        "info_spot_file": found.get("info_spot_file", ""),
        "info_contract_file": found.get("info_contract_file", ""),
        "target_file": found.get("target_file", ""),
        "target_file_v2": found.get("target_file_v2", ""),
    }
