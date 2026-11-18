# api/nodes.py
from flask import Blueprint, request
from services.bid_space_service import fetch_unit_names
from services.db_store import fetch_contract_config, save_contract_config
from utils.response import success, fail
import json

nodes_bp = Blueprint("nodes", __name__)


@nodes_bp.get("/plant")
def list_nodes():
    """获取浙江省所有电厂节点（直接读正式库）"""
    units = fetch_unit_names()
    # 构造兼容原有前端的结构
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
    """获取电价对比的默认节点配置"""
    val = fetch_contract_config("price_compare_default_nodes")
    if not val:
        return success([])
    try:
        return success(json.loads(val))
    except Exception:
        return success([])


@nodes_bp.post("/price-compare-defaults")
def save_price_compare_defaults():
    """保存电价对比的默认节点配置"""
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
