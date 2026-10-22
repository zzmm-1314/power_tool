from flask import Blueprint, request

from services.node_manager import NodeManager
from utils.response import success, fail

nodes_bp = Blueprint("nodes", __name__)


@nodes_bp.get("/plant")
def list_nodes():
    return success(NodeManager.list_all())


@nodes_bp.post("/plant")
def add_node():
    data = request.get_json(silent=True) or {}
    res = NodeManager.add(data.get("name", ""), data.get("description", ""))
    if not res["ok"]:
        return fail(res["error"])
    return success(res["node"], msg="已新增")


@nodes_bp.put("/plant/<int:node_id>")
def update_node(node_id: int):
    data = request.get_json(silent=True) or {}
    res = NodeManager.update(node_id, data.get("name", ""), data.get("description", ""))
    if not res["ok"]:
        return fail(res["error"])
    return success(res["node"], msg="已修改")


@nodes_bp.delete("/plant/<int:node_id>")
def delete_node(node_id: int):
    res = NodeManager.delete(node_id, purge=True)
    if not res["ok"]:
        return fail(res["error"])
    return success(msg="已删除节点及其临时数据")


@nodes_bp.post("/plant/batch")
def add_nodes_batch():
    """批量新增节点
    body: { names: string[], description?: string }
    """
    data = request.get_json(silent=True) or {}
    names = data.get("names") or []
    if not isinstance(names, list) or not names:
        return fail("请提供节点名列表")

    res = NodeManager.add_batch(names, data.get("description", ""))
    if not res.get("ok", True):
        return fail(res.get("error", "批量新增失败"))

    return success(
        res,
        msg=f"新增 {len(res['added'])} 个，跳过 {len(res['skipped'])} 个",
    )


@nodes_bp.delete("/plant/batch")
def delete_nodes_batch():
    """批量删除节点
    body: { ids: number[] }
    """
    data = request.get_json(silent=True) or {}
    ids = data.get("ids") or []
    if not isinstance(ids, list) or not ids:
        return fail("请提供要删除的节点 ID 列表")

    res = NodeManager.delete_batch(ids, purge=True)
    if not res["ok"]:
        return fail(res["error"])

    return success(res, msg=f"已删除 {res['count']} 个节点")
