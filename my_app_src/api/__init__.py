from .load import load_bp
from .price import price_bp
from .spread import spread_bp
from .settlement import settlement_bp  # ← 新增
from .monthly import monthly_bp
from .temp_data import temp_bp
from .nodes import nodes_bp
from .unified_plants import unified_plants_bp
from .coefficient import coefficient_bp
from .rolling import rolling_bp


def register_blueprints(app):
    app.register_blueprint(load_bp, url_prefix="/api/load")
    app.register_blueprint(price_bp, url_prefix="/api/price")
    app.register_blueprint(spread_bp, url_prefix="/api/spread")
    app.register_blueprint(settlement_bp, url_prefix="/api/settlement")  # ← 新增
    app.register_blueprint(monthly_bp, url_prefix="/api/monthly")
    app.register_blueprint(temp_bp, url_prefix="/api/temp-data")
    app.register_blueprint(nodes_bp, url_prefix="/api/nodes")
    app.register_blueprint(unified_plants_bp, url_prefix="/api/unified-plants")
    app.register_blueprint(coefficient_bp, url_prefix="/api/coefficient")
    app.register_blueprint(rolling_bp, url_prefix="/api/rolling")
