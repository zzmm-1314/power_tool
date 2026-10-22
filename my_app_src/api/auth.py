from datetime import datetime

from flask import Blueprint, request, g

from constants import (
    ALL_ROLES,
    ROLE_ADMIN,
    ROLE_USER,
    SELF_REGISTER_ROLES,
)
from extensions import db
from models import User
from utils.auth import generate_token, login_required
from utils.response import success, fail

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    nickname = (data.get("nickname") or "").strip()
    role = (data.get("role") or "").strip()

    # ---- 基础校验 ----
    if not username or not password:
        return fail("用户名和密码不能为空")
    if not (3 <= len(username) <= 32):
        return fail("用户名长度需在 3-32 位之间")
    if len(password) < 6:
        return fail("密码长度至少 6 位")

    # ---- 角色校验：只允许自助注册业务角色 ----
    if role not in SELF_REGISTER_ROLES:
        return fail("请选择有效的账号类型")

    if User.query.filter_by(username=username).first():
        return fail("用户名已存在")

    user = User(
        username=username,
        nickname=nickname or username,
        role=role,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = generate_token(user.id, user.username)
    return success({"token": token, "user": user.to_dict()}, msg="注册成功")


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return fail("用户名和密码不能为空")

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return fail("用户名或密码错误")

    user.last_login_at = datetime.utcnow()
    db.session.commit()

    token = generate_token(user.id, user.username)
    return success({"token": token, "user": user.to_dict()}, msg="登录成功")


@auth_bp.get("/me")
@login_required
def me():
    return success(g.current_user.to_dict())


@auth_bp.post("/logout")
@login_required
def logout():
    return success(msg="已退出登录")
