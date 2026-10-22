# config.py
import os
import sys

"""
统一配置中心 - 整合所有模块的参数
"""


def _get_base_path():
    """打包成 exe 后返回 exe 所在目录；开发时返回源码目录"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


base_path = _get_base_path()
# 历史数据文件路径（请按实际情况修改）
HISTORY_FILE = os.path.join(base_path, "data", "sources.xlsx")
# ==================== 历史数据分析参数 ====================
HALF_LIVES = [3, 5, 7, 10, 14]  # 半衰期列表（天）
WINDOW_DAYS = 45  # 历史回看窗口（天）
D_OFFSET = 2  # 预测日偏移量（D = 最新日期 + D_OFFSET）
EXPECTED_MWH = 10  # 每个时段的预测发电量（MWh）
WINSOR_PROB = 0.0  # 截尾比例（去除两端各1%）
HARD_CAP = 130  # 硬截断阈值（元/MWh）

# 策略族定义
STRATEGY_SPECS = [
    {"strategy_family": "Strategy A", "hard_cap": None},  # 仅Winsorize
    {"strategy_family": "Strategy B", "hard_cap": HARD_CAP},  # Winsorize + 硬截断
]
STRATEGY_FAMILY = "Strategy A"  # 默认策略族
HALF_LIFE = 2.0074801301671816  # 默认半衰期（天）
# ==================== 自适应权重参数 ====================
BASE_HIST_WEIGHT = 0.5
MAX_HIST_WEIGHT = 0.9
MIN_HIST_WEIGHT = 0.3

# ==================== 天气修正参数 ====================
WEATHER_ENABLED = True  # 天气修正总开关（True=启用，False=禁用）
WEATHER_WEIGHT = 0.4  # 天气偏移叠加权重（0~1，值越大天气修正影响越强）
PV_OFFSET_FACTOR = 0.25
TEMP_OFFSET_FACTOR = 0.02  # 默认值0.015
WIND_OFFSET_FACTOR = 0.02
TEMP_BASE = 25
WIND_BASE = 15  # 如果数据是80米高度，建议从5改为15
# ==================== 天气修正非线性参数 ====================
# 修正模式: 'linear' 或 'nonlinear'
WEATHER_CORRECTION_MODE = "nonlinear"  # 'linear' 或 'nonlinear'

# 光伏非线性参数 (Sigmoid)
PV_SIGMOID_SLOPE = 8.0  # 斜率，越大转折越陡
PV_SIGMOID_SHIFT = 0.5  # 偏移，使曲线居中

# 温度非线性参数 (Sigmoid)
TEMP_SIGMOID_SLOPE = 0.4  # 斜率
TEMP_SIGMOID_THRESHOLD = 30.0  # 转折点温度(℃)

# 风速非线性参数 (Tanh)
WIND_TANH_SCALE = 8.0  # 缩放因子，控制饱和速度
WIND_TANH_SHIFT = 15  # 基准偏移
# 湿度参数
HUMIDITY_THRESHOLD = 60
HUMIDITY_AMP = 0.06
HEAT_INDEX_MAX_OFFSET = 5.0
# ==================== 辐射与日照字段使用开关 ====================
# 选择使用哪种辐射数据作为光伏出力估算依据
# 若开启多个，优先级：direct_radiation > diffuse_radiation > dni > shortwave_radiation（默认）
# ==================== 辐射字段使用策略 ====================
# 'single' : 只使用一个主辐射字段（下面的 USE_XXX 决定用哪个）
# 'composite' : 综合使用 direct + diffuse 来估算光伏出力
RADIATION_STRATEGY = "composite"  # 可选 'single' 或 'composite'
# 当 RADIATION_STRATEGY = 'single' 时，指定主辐射字段
USE_DIRECT_RADIATION = True  # 是否使用 direct_radiation (W/m²)
USE_DIFFUSE_RADIATION = True  # 是否使用 diffuse_radiation (W/m²)
USE_DNI = True  # 是否使用 direct_normal_irradiance (W/m²)
# 是否使用日照时长作为额外修正（强日照时段才生效）
USE_SUNSHINE_DURATION = True  # 是否使用 sunshine_duration (s) 进行日照时长修正
# 是否使用云量作为光伏修正（天气数据中有 cloud_cover_low 时建议开启）
USE_CLOUD_COVER = True  # 默认开启

# 综合策略的物理权重（仅 RADIATION_STRATEGY = 'composite' 时生效）
DIRECT_WEIGHT = 0.7  # 直射辐射权重（建议 0.5~0.8）
DIFFUSE_WEIGHT = 0.3  # 散射辐射权重（高散射 = 阴天 → 光伏出力低）（建议 0.2~0.5，与直射权重之和可以≠1）
# 辐射参数
RADIATION_MAX_CLEAR_SKY = 800
RADIATION_WEIGHT = 0.7
SUNSHINE_DURATION_MAX = 3600

# ==================== 发电不稳定修正参数 ====================
GEN_RISK_TEMP_THRESHOLD = 45
GEN_RISK_PENALTY = 0.03
# ==================== 极端天气调整参数 ====================
EXTREME_WEATHER_ENABLED = True  # 是否启用极端天气自动调整
EXTREME_WIND_THRESHOLD = 45  # 风速阈值（km/h），超过此值视为极端大风（约10级）
EXTREME_TEMP_THRESHOLD = 40  # 体感温度阈值（℃），超过此值视为极端高温
EXTREME_WEATHER_OFFSET = -0.25  # 极端天气时强制施加的负偏移量（统一值，可分别设置）
# 可分别设置不同极端天气的偏移
EXTREME_WIND_OFFSET = -0.20
EXTREME_TEMP_OFFSET = -0.15
# ==================== 系数限制 ====================
COEFF_MIN = 0.1
COEFF_MAX = 1.9
# ==================== 进度条显示 ====================
SHOW_PROGRESS_BAR = True  # 是否显示进度条
# ==================== 可视化参数 ====================
VISUALIZATION_ENABLED = True  # 是否生成可视化图表
VISUALIZATION_OUTPUT_DIR = os.path.join(base_path, "visualization")  # 图表输出目录
VISUALIZATION_PREFIX = ""  # 图表文件名前缀（可为空或日期）
# ==================== 市场转向检测参数 ====================
REGIME_DETECTION_ENABLED = True  # 是否启用转向检测
REGIME_ZSCORE_THRESHOLD = 1.5  # Z-score阈值（1.5~2.0）
REGIME_VOL_RATIO_THRESHOLD = 2.0  # 波动率放大倍数阈值
REGIME_WINRATE_THRESHOLD = 0.30  # 近期胜率阈值
REGIME_RECENT_DAYS = 7  # 短期窗口（天）
REGIME_LONG_DAYS = 45  # 长期窗口（天）
REGIME_MIN_HIST_WEIGHT = 0.20  # 转向时最低历史权重
REGIME_DEFAULT_HIST_WEIGHT = 0.70  # 默认历史权重
# ==================== 可由前端覆盖的天气配置白名单 ====================
WEATHER_CONFIG_KEYS = {
    # 总开关
    "WEATHER_ENABLED",
    "WEATHER_WEIGHT",
    # 基础偏移因子
    "PV_OFFSET_FACTOR",
    "TEMP_OFFSET_FACTOR",
    "WIND_OFFSET_FACTOR",
    "TEMP_BASE",
    "WIND_BASE",
    # 非线性模式
    "WEATHER_CORRECTION_MODE",
    "PV_SIGMOID_SLOPE",
    "PV_SIGMOID_SHIFT",
    "TEMP_SIGMOID_SLOPE",
    "TEMP_SIGMOID_THRESHOLD",
    "WIND_TANH_SCALE",
    "WIND_TANH_SHIFT",
    # 湿度
    "HUMIDITY_THRESHOLD",
    "HUMIDITY_AMP",
    "HEAT_INDEX_MAX_OFFSET",
    # 辐射
    "RADIATION_STRATEGY",
    "USE_DIRECT_RADIATION",
    "USE_DIFFUSE_RADIATION",
    "USE_DNI",
    "USE_SUNSHINE_DURATION",
    "USE_CLOUD_COVER",
    "DIRECT_WEIGHT",
    "DIFFUSE_WEIGHT",
    "RADIATION_MAX_CLEAR_SKY",
    "RADIATION_WEIGHT",
    "SUNSHINE_DURATION_MAX",
    # 发电风险
    "GEN_RISK_TEMP_THRESHOLD",
    "GEN_RISK_PENALTY",
    # 极端天气
    "EXTREME_WEATHER_ENABLED",
    "EXTREME_WIND_THRESHOLD",
    "EXTREME_TEMP_THRESHOLD",
    "EXTREME_WEATHER_OFFSET",
    "EXTREME_WIND_OFFSET",
    "EXTREME_TEMP_OFFSET",
}
