import os

from flask import Flask, jsonify
from flask_cors import CORS

from api import register_blueprints
from config import Config
from services.cleanup_task import get_cleanup_task


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    register_blueprints(app)

    # 启动后台清理任务（避免 debug 重载时重复启动）
    if Config.TEMP_AUTO_CLEAN and (
        not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    ):
        get_cleanup_task().start()

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"code": 404, "msg": "接口不存在", "data": None}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"code": 500, "msg": str(e), "data": None}), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("FLASK_PORT", 5000)),
        debug=app.config.get("DEBUG", False),
    )
