import os
import sys
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, Response
from flask_cors import CORS

from api import register_blueprints
from config import Config
from services.cleanup_task import get_cleanup_task

# ==================== 路径 ====================
if getattr(sys, "frozen", False):
    APP_ROOT = Path(sys.executable).resolve().parent
    STATIC_DIR = APP_ROOT / "static"
else:
    # 开发环境：app.py 在 my_app_src/，static 在项目根目录
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    APP_ROOT = PROJECT_ROOT
    STATIC_DIR = PROJECT_ROOT / "static"

print(f"[static] frozen={getattr(sys, 'frozen', False)}", flush=True)
print(f"[static] STATIC_DIR = {STATIC_DIR}", flush=True)


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=None,  # ← 关键：禁用 Flask 内置 static 路由
        template_folder=str(STATIC_DIR),
    )
    app.config.from_object(Config)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    register_blueprints(app)

    index_html = STATIC_DIR / "index.html"
    print(f"[static] STATIC_DIR = {STATIC_DIR}", flush=True)
    print(f"[static] exists = {STATIC_DIR.is_dir()}", flush=True)
    print(f"[static] index.html exists = {index_html.is_file()}", flush=True)
    if STATIC_DIR.is_dir():
        try:
            names = [p.name for p in STATIC_DIR.iterdir()][:8]
            print(f"[static] 目录内容（前 8 项）= {names}", flush=True)
        except Exception as e:
            print(f"[static] 列目录失败: {e}", flush=True)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_spa(path):
        # 1. API 路径不拦截（正常情况下已被蓝图优先命中）
        if path.startswith("api/"):
            return jsonify({"code": 404, "msg": "接口不存在", "data": None}), 404

        # 2. 真实静态文件直接返回（assets、geo、favicon 等）
        if path:
            target = STATIC_DIR / path
            if target.is_file():
                return send_from_directory(STATIC_DIR, path)

        # 3. SPA fallback：返回 index.html 交给 Vue Router
        if index_html.is_file():
            return send_from_directory(STATIC_DIR, "index.html")

        # 4. index.html 缺失 → 返回清晰提示
        hint = (
            "<h2>前端未构建</h2>"
            f"<p>STATIC_DIR：<code>{STATIC_DIR}</code></p>"
            f"<p>index.html exists：<b>{index_html.is_file()}</b></p>"
            "<p>请执行：</p>"
            "<pre>cd frontend\nnpm run build\n"
            "Remove-Item ..\\my_app_src\\static -Recurse -Force\n"
            "New-Item -ItemType Directory ..\\my_app_src\\static\n"
            "Copy-Item .\\dist\\* ..\\my_app_src\\static\\ -Recurse -Force</pre>"
        )
        return hint, 500, {"Content-Type": "text/html; charset=utf-8"}

    # ===== 存储诊断 =====
    try:
        from services.storage_config import debug_storage
        import json

        print(
            "[storage] " + json.dumps(debug_storage(), ensure_ascii=False, default=str),
            flush=True,
        )
    except Exception as e:
        print(f"[storage] 诊断失败: {e}", flush=True)
    try:
        from services.storage_config import debug_storage, deep_scan_storage
        import json

        print(
            "[storage] " + json.dumps(debug_storage(), ensure_ascii=False, default=str),
            flush=True,
        )
        print(
            "[storage-deep] "
            + json.dumps(deep_scan_storage(), ensure_ascii=False, default=str),
            flush=True,
        )
    except Exception as e:
        print(f"[storage] 诊断失败: {e}", flush=True)
    if Config.TEMP_AUTO_CLEAN and (
        not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    ):
        get_cleanup_task().start()

    # 启动云盘同步（只在真正运行时启动一次）
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        try:
            from services.sync_service import get_sync_service

            get_sync_service().start()
        except Exception as e:
            print(f"[sync] 启动失败: {e}", flush=True)
    return app


app = create_app()


# ==================== 启动入口（必须是函数，launcher 需要 import 它） ====================
def main():
    import socket
    import threading
    import time
    import webbrowser

    def pick_free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def open_browser(url: str, delay: float = 1.2):
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"[浏览器] 自动打开失败，请手动访问 {url} ({e})")

    port = pick_free_port()
    url = f"http://127.0.0.1:{port}/"

    print("=" * 60)
    print("  电力工具助手")
    print(f"  访问地址：{url}")
    print("  按 Ctrl+C 停止服务")
    print("=" * 60, flush=True)

    threading.Thread(target=open_browser, args=(url,), daemon=True).start()
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
