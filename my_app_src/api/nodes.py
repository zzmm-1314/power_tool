# api/nodes.py
from flask import Blueprint, request
from services.bid_space_service import fetch_unit_names
from services.db_store import fetch_contract_config, save_contract_config
from utils.response import success, fail  # ← 补 fail 导入（原先会 NameError）
import json

nodes_bp = Blueprint("nodes", __name__)


@nodes_bp.get("/plant")
def list_nodes():
    units = fetch_unit_names()
    result = [
        {
            "id": idx + 1,
            "name": name,
            "description": "正式库节点",
            "createdAt": "",
            "updatedAt": "",
        }
        for idx, name in enumerate(units)
    ]
    return success(result)


@nodes_bp.get("/price-compare-defaults")
def get_price_compare_defaults():
    val = fetch_contract_config("price_compare_default_nodes")
    if not val:
        return success([])
    try:
        return success(json.loads(val))
    except Exception:
        return success([])


@nodes_bp.post("/price-compare-defaults")
def save_price_compare_defaults():
    data = request.get_json(silent=True) or {}
    nodes = data.get("nodes", [])
    if not isinstance(nodes, list):
        return fail("无效的节点列表")
    try:
        save_contract_config(
            "price_compare_default_nodes", json.dumps(nodes, ensure_ascii=False)
        )
        return success(msg="默认节点配置已保存")
    except Exception as e:
        return fail(f"保存失败: {e}")


# ==================== 全局默认节点（单节点） ====================


@nodes_bp.get("/global-node")
def get_global_node():
    """读取用户选择的全局默认节点（价格 / 合约 / 申报系数 / 结算单等页面均默认展示该节点）"""
    val = fetch_contract_config("global_default_node")
    return success(val or "")


@nodes_bp.post("/global-node")
def save_global_node():
    data = request.get_json(silent=True) or {}
    node = (data.get("node") or "").strip()
    try:
        save_contract_config("global_default_node", node)
        return success(msg="全局默认节点已保存")
    except Exception as e:
        return fail(f"保存失败: {e}")
