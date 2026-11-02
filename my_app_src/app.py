import io
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from api import register_blueprints
from config import Config

# ==================== 路径 & 环境 ====================
if getattr(sys, "frozen", False):
    APP_ROOT = Path(sys.executable).resolve().parent
else:
    # 开发环境：app.py 在 my_app_src/ 下，static 与 my_app_src 平级
    APP_ROOT = Path(__file__).resolve().parent.parent

STATIC_DIR = APP_ROOT / "static"
# 全局记录最后一次心跳的时间
LAST_HEARTBEAT_TIME = time.time()


def _detect_mode() -> tuple[bool, str]:
    """
    自动识别运行模式，返回 (是否生产模式, 判定依据)：
    1. PyInstaller 打包（exe）→ 强制生产模式
    2. 显式设置 POWER_TOOL_MODE / FLASK_ENV → 尊重环境变量
       （production|prod → 生产；development|dev → 开发）
    3. 未设置 → 自动判断：存在 static/index.html 构建产物则按生产
       模式运行（直接访问 http://127.0.0.1:<port>/ 即可），
       否则按开发模式运行（后端只供 API，前端用 Vite）
    """
    if getattr(sys, "frozen", False):
        return True, "自动识别：打包模式（sys.frozen）"

    for var in ("POWER_TOOL_MODE", "FLASK_ENV"):
        val = os.getenv(var)
        if val:
            v = val.strip().lower()
            if v in ("production", "prod"):
                return True, f"环境变量 {var}={val}"
            if v in ("development", "dev"):
                return False, f"环境变量 {var}={val}"
            print(f"[env] 忽略无法识别的 {var}={val!r}", flush=True)

    if (STATIC_DIR / "index.html").is_file():
        return True, "自动识别：检测到 static/index.html 构建产物 → 生产模式"
    return False, "自动识别：无 static 构建产物 → 开发模式"


IS_PROD, MODE_REASON = _detect_mode()


# ==================== 开发提示页 ====================
DEV_HINT_HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>电力工具助手 · 开发模式</title>
<style>
body{font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
     background:#f5f7fa;color:#303133;margin:0;padding:60px 20px;}
.card{max-width:640px;margin:0 auto;background:#fff;border-radius:8px;
      padding:32px 36px;box-shadow:0 4px 20px rgba(0,0,0,.06);}
h1{margin:0 0 8px;font-size:22px;color:#1f2d3d;}
p{margin:8px 0;line-height:1.7;font-size:14px;color:#606266;}
code{background:#f4f4f5;padding:2px 6px;border-radius:3px;
     font-size:13px;color:#d63384;}
.step{background:#fafbfc;border-left:3px solid #2d6cdf;
      padding:10px 14px;margin:14px 0;border-radius:4px;font-size:14px;}
a{color:#2d6cdf;text-decoration:none;}
a:hover{text-decoration:underline;}
.badge{display:inline-block;padding:2px 8px;background:#fff7e6;
       color:#d48806;border-radius:3px;font-size:12px;
       margin-left:6px;vertical-align:middle;}
</style></head><body>
<div class="card">
  <h1>电力工具助手 · 开发模式 <span class="badge">DEV</span></h1>
  <p>当前后端 API 已启动，但前端尚未通过本后端托管。</p>

  <div class="step">
    <strong>1.</strong> 另开一个终端，进入前端目录并启动 Vite：
    <div><code>cd frontend</code></div>
    <div><code>npm run dev</code></div>
  </div>

  <div class="step">
    <strong>2.</strong> 浏览器访问前端地址：
    <div><a href="http://localhost:5173" target="_blank">http://localhost:5173</a></div>
    <p style="margin:6px 0 0;font-size:12px;color:#909399;">
      Vite 会把 <code>/api</code> 自动代理到 <code>http://127.0.0.1:5000</code>。
    </p>
  </div>

  <p style="margin-top:24px;font-size:12px;color:#909399;">
    如果只是测试 API，可直接访问
    <a href="/api/load/devices" target="_blank">/api/load/devices</a> 等接口。
  </p>
</div>
</body></html>"""


def register_heartbeat(app):
    @app.route("/api/heartbeat", methods=["GET", "POST"])
    def heartbeat():
        global LAST_HEARTBEAT_TIME
        LAST_HEARTBEAT_TIME = time.time()
        return jsonify({"code": 0, "msg": "ok"})


def start_watchdog(grace_period=15, timeout=30):
    """
    启动看门狗线程，超时未收到心跳则强制退出进程
    grace_period: 初始宽限期（防止启动时前端还未加载）
    timeout: 无心跳超时时间
    """
    global LAST_HEARTBEAT_TIME
    LAST_HEARTBEAT_TIME = time.time() + grace_period

    def _watchdog_loop():
        global LAST_HEARTBEAT_TIME
        while True:
            time.sleep(5)
            if time.time() - LAST_HEARTBEAT_TIME > timeout:
                print(
                    f"\n[Watchdog] 超过 {timeout} 秒未收到前端心跳，页面可能已关闭。自动退出进程...",
                    flush=True,
                )
                # 必须用 os._exit 强制终止，因为 Flask 主线程还在阻塞中
                os._exit(0)

    t = threading.Thread(target=_watchdog_loop, daemon=True, name="HeartbeatWatchdog")
    t.start()


# ==================== create_app ====================
def create_app() -> Flask:
    app = Flask(
        __name__,
        # 生产模式：交给 serve_spa 处理静态文件
        static_folder=None,
        template_folder=str(STATIC_DIR) if IS_PROD else None,
    )
    app.config.from_object(Config)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    register_blueprints(app)
    register_heartbeat(app)
    index_html = STATIC_DIR / "index.html"
    static_ready = index_html.is_file()

    # ===== 启动诊断 =====
    print("=" * 60, flush=True)
    print(f"[env] IS_PROD       = {IS_PROD}", flush=True)
    print(f"[env] MODE_REASON   = {MODE_REASON}", flush=True)
    print(f"[env] APP_ROOT      = {APP_ROOT}", flush=True)
    print(f"[env] STATIC_DIR    = {STATIC_DIR}", flush=True)
    print(f"[env] static_ready  = {static_ready}", flush=True)
    print("=" * 60, flush=True)

    if not IS_PROD:
        print(
            "[dev] 开发模式：不检查 static，仅提供 /api/* 接口",
            flush=True,
        )
        if static_ready:
            print(
                f"[dev] 提示：检测到 {STATIC_DIR}，如仍想调试前端请用 Vite",
                flush=True,
            )
    else:
        if not static_ready:
            print(
                f"[prod] 警告：static 目录缺少 index.html，"
                f"请把前端 dist 复制到 {STATIC_DIR}",
                flush=True,
            )
        else:
            print(f"[prod] 静态资源就绪：{STATIC_DIR}", flush=True)

    # ===== SPA / 开发提示兜底 =====
    # 注意：这里必须接受所有方法。若只声明 GET，未注册的 API 请求（如 POST）
    # 会被 Werkzeug 判成 405 Method Not Allowed（Allow: GET, HEAD, OPTIONS），
    # 排查时极易误判成"接口方法不对"，实际是路由不存在 / 前后端版本不一致。
    @app.route(
        "/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
    )
    @app.route("/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def serve_spa(path):
        # API 路径不拦截，直接给出可读的 404 提示
        if path.startswith("api/"):
            return (
                jsonify(
                    {
                        "code": 404,
                        "msg": (
                            f"接口 /{path} 不存在。若为上传请求，请确认后端已重启、"
                            "且前端已重新构建（旧构建产物仍在请求已下线的 /api/temp-data）"
                        ),
                        "data": None,
                    }
                ),
                404,
            )

        # 真实静态文件直接返回（生产模式或开发模式都允许）
        if path and static_ready:
            target = STATIC_DIR / path
            if target.is_file():
                return send_from_directory(STATIC_DIR, path)

        # index.html 存在则交给前端路由
        if static_ready:
            return send_from_directory(STATIC_DIR, "index.html")

        # 无前端资源
        if IS_PROD:
            # 生产模式缺 static：返回可读提示
            return (
                "<h2>前端未构建</h2>"
                f"<p>请把前端构建产物复制到 <code>{STATIC_DIR}</code></p>"
                "<pre>cd frontend\nnpm run build\n"
                "xcopy /E /I /Y dist ..\\static</pre>",
                500,
                {"Content-Type": "text/html; charset=utf-8"},
            )
        # 开发模式：返回开发提示页
        return DEV_HINT_HTML, 200, {"Content-Type": "text/html; charset=utf-8"}

    # ===== 后台任务（已移除 WPS 云盘同步与文件清理） =====
    # 由于后续将使用数据库，不再需要 watchdog 云盘同步和后台本地临时文件清理

    return app


app = create_app()


# ==================== 启动入口 ====================
def _pick_free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _open_browser_later(url: str, delay: float = 1.2):
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"[launcher] 自动打开浏览器失败：{e}", flush=True)


def main():
    # 端口：环境变量优先，否则自动分配
    env_port = os.getenv("FLASK_PORT")
    if env_port and env_port.isdigit():
        port = int(env_port)
    else:
        port = _pick_free_port()

    url = f"http://127.0.0.1:{port}/"

    print("=" * 60, flush=True)
    print("  电力工具助手", flush=True)
    print(f"  模式：{'生产' if IS_PROD else '开发'}", flush=True)
    print(f"  后端端口：{port}", flush=True)
    if IS_PROD:
        print(f"  访问地址：{url}", flush=True)
    else:
        print(f"  API 地址：http://127.0.0.1:{port}/api/", flush=True)
        print(f"  前端请另开终端启动：cd frontend && npm run dev", flush=True)
        print(f"  前端地址：http://localhost:5173", flush=True)
    print("  按 Ctrl+C 停止服务", flush=True)
    print("=" * 60, flush=True)

    # 只在生产模式自动打开浏览器
    if IS_PROD:
        threading.Thread(target=_open_browser_later, args=(url,), daemon=True).start()

    # 开发环境强制开启 debug 和热重载
    is_debug = not IS_PROD

    app.run(
        host="127.0.0.1",
        port=port,
        debug=is_debug,
        use_reloader=is_debug,
    )


if __name__ == "__main__":
    main()
