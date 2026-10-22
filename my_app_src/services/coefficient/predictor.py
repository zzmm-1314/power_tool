# type: ignore
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .regime_detector import MarketRegimeDetector
from .ml_enhancer import RidgeGapPredictor
from services.coefficient import coefficient_config as config
from .coefficient_config import (
    WINDOW_DAYS,
    D_OFFSET,
    STRATEGY_FAMILY,
    HALF_LIFE,
    COEFF_MIN,
    COEFF_MAX,
    WEATHER_ENABLED,
    WEATHER_WEIGHT,
    REGIME_DETECTION_ENABLED,
    TEMP_BASE,
    WIND_BASE,
    RADIATION_MAX_CLEAR_SKY,
)
from .data_loader import load_history_data
from .history_analyzer import (
    compute_all_strategies_coefficients,
    select_best_strategy,
)
from .weather_processor import calculate_weather_components, calculate_gen_risk_offset
from .backtest_engine import run_recent_backtest


class CoefficientPredictor:
    def __init__(self, history_file_path=None, history_df=None):
        if history_df is not None:
            self.history = history_df
        elif history_file_path is not None:
            self.history = load_history_data(history_file_path)
        else:
            raise ValueError("必须提供历史数据文件或DataFrame")

        required_cols = ["date"] + [str(i) for i in range(48)]
        missing = [c for c in required_cols if c not in self.history.columns]
        if missing:
            raise ValueError(f"历史数据缺少列：{missing}")

        self.ml_predictor = RidgeGapPredictor(alpha=2.0)
        if not self.ml_predictor.is_trained:
            self.ml_predictor.train(self.history)

    def predict(
        self,
        target_date,
        weather_df,
        strategy_family: str = None,
        half_life: float = None,
        window_days: int = WINDOW_DAYS,
        apply_weather: bool = WEATHER_ENABLED,
        detection_offset_days: int = 3,
        progress_callback=None,
        coeff_min: float = None,  # ★ 新增
        coeff_max: float = None,  # ★ 新增
    ):
        """
        预测 D+2 日的48点申报系数。
        返回 dict：
            {
                "coefficients": [...48个系数...],
                "strategy": 策略名,
                "half_life": 半衰期,
                "all_coeffs": 所有策略组合的系数 DataFrame（长表）,
                "correction_log": 修正明细列表,
            }
        """
        # 顶部决定实际裁剪范围
        clip_min = float(coeff_min) if coeff_min is not None else float(COEFF_MIN)
        clip_max = float(coeff_max) if coeff_max is not None else float(COEFF_MAX)
        if clip_max <= clip_min:
            clip_min, clip_max = float(COEFF_MIN), float(COEFF_MAX)

        def report(stage, current, total, message=""):
            if progress_callback:
                try:
                    progress_callback(stage, current, total, message)
                except Exception:
                    pass

        report("初始化", 0, 1, "准备历史数据窗口")

        target = pd.to_datetime(target_date)
        latest_usable = target - timedelta(days=D_OFFSET)
        window_start = latest_usable - timedelta(days=window_days)

        window_mask = (self.history["date"] >= window_start) & (
            self.history["date"] <= latest_usable
        )
        window_data = self.history.loc[window_mask].sort_values("date")

        if len(window_data) < window_days * 0.5:
            raise ValueError(
                f"历史数据不足，仅 {len(window_data)} 天，需要至少 {window_days} 天"
            )

        gap_cols = [str(i) for i in range(48)]
        gap_matrix = window_data[gap_cols]

        # ---- 市场转向检测 ----
        report("市场转向检测", 0, 1, "检测市场结构变化")
        if REGIME_DETECTION_ENABLED:
            detection_reference = target - timedelta(days=detection_offset_days)
            detector = MarketRegimeDetector(self.history, config)
            shift_flags, shift_confidences, recommended_hist_weights = detector.detect(
                detection_reference
            )
        else:
            shift_flags = [False] * 48
            recommended_hist_weights = [0.7] * 48

        # ---- 计算所有策略组合的系数 ----
        report("系数计算", 0, 1, "准备计算各策略系数")
        all_coeffs = compute_all_strategies_coefficients(
            gap_matrix=gap_matrix,
            dates=window_data["date"],
            reference_date=latest_usable,
            progress_callback=report,
        )

        # ---- 策略选择 ----
        backtest_df = None
        if strategy_family is None or half_life is None:
            report("回测评估", 0, 1, "运行历史回测")
            backtest_df = run_recent_backtest(
                self.history, D_OFFSET, window_days, progress_callback=report
            )
            if backtest_df is not None:
                best = select_best_strategy(backtest_df)
                strategy_family = best["strategy_family"]
                half_life = best["half_life"]
                print(
                    f"自动选择策略: {strategy_family}, 半衰期: {half_life}天, 回测累计PnL: {best['cumulative_pnl']:.2f}元"
                )
            else:
                strategy_family = strategy_family or "Strategy A"
                half_life = half_life or 7
                print("回测无数据，使用默认策略: Strategy A, 半衰期7天")

        self.backtest_df = backtest_df

        # ---- 提取选中策略的系数 ----
        try:
            half_life = float(half_life)
        except (TypeError, ValueError):
            pass

        available = all_coeffs[["strategy_family", "half_life"]].drop_duplicates()
        mask = (all_coeffs["strategy_family"] == strategy_family) & (
            np.abs(all_coeffs["half_life"] - half_life) < 1e-6
        )

        if not mask.any():
            avail_hls = available[available["strategy_family"] == strategy_family][
                "half_life"
            ].unique()
            if len(avail_hls) > 0:
                closest = min(avail_hls, key=lambda x: abs(x - half_life))
                half_life = closest
                mask = (all_coeffs["strategy_family"] == strategy_family) & (
                    np.abs(all_coeffs["half_life"] - half_life) < 1e-6
                )
            else:
                strategy_family = None

        if not mask.any():
            if backtest_df is None:
                backtest_df = run_recent_backtest(
                    self.history, D_OFFSET, WINDOW_DAYS, progress_callback=report
                )
            if backtest_df is not None:
                best = select_best_strategy(backtest_df)
                strategy_family = best["strategy_family"]
                half_life = best["half_life"]
                mask = (all_coeffs["strategy_family"] == strategy_family) & (
                    np.abs(all_coeffs["half_life"] - half_life) < 1e-6
                )

        if not mask.any():
            raise ValueError("无法确定有效的策略和半衰期组合，请检查 all_coeffs 内容。")

        coeff_df = all_coeffs.loc[mask].sort_values("point")
        base_coeffs = coeff_df["coefficient"].tolist()
        if not base_coeffs:
            raise ValueError(
                f"提取系数失败。策略: {strategy_family}, 半衰期: {half_life}"
            )

        # ---- 天气修正 ----
        correction_log = []
        weather_48 = None  # ★ 提到外层
        has_weather = weather_df is not None and len(weather_df) > 0  # ★

        if apply_weather and has_weather:  # ★ 双条件
            report("天气修正", 0, 48, "应用天气修正")
            weather_48 = self._prepare_weather_data(weather_df, target)
            final_coeffs = []
            for hour in range(48):
                temp_coeff = base_coeffs[hour]
                row = weather_48.iloc[hour]

                weather_comp = calculate_weather_components(row, hour)
                pv_offset = weather_comp["pv_offset"]
                temp_offset = weather_comp["temp_offset"]
                humidity_offset = weather_comp["humidity_offset"]
                wind_offset = weather_comp["wind_offset"]
                extreme_offset = weather_comp["extreme_offset"]
                effective_temp = weather_comp["effective_temp"]
                humidity_contribution = weather_comp["humidity_contribution"]

                weather_offset = (
                    pv_offset + temp_offset + humidity_offset + wind_offset
                ) * WEATHER_WEIGHT

                gen_offset = calculate_gen_risk_offset(
                    row.get("apparent_temperature (°C)", 25)
                )

                recent_series = window_data[str(hour)].values[-30:]
                ml_offset = self.ml_predictor.predict_offset(hour, recent_series)

                final = (
                    temp_coeff
                    + weather_offset
                    + gen_offset
                    + extreme_offset
                    + ml_offset
                )
                clip_min = coeff_min if coeff_min is not None else COEFF_MIN
                clip_max = coeff_max if coeff_max is not None else COEFF_MAX
                final = np.clip(final, clip_min, clip_max)

                correction_log.append(
                    {
                        "period": hour,
                        "time_label": f"{hour//2:02d}:{30 if hour%2 else 0:02d}",
                        "base_coefficient": float(temp_coeff),
                        "pv_offset": float(pv_offset),
                        "temp_offset": float(temp_offset),
                        "humidity_offset": float(humidity_offset),
                        "wind_offset": float(wind_offset),
                        "extreme_offset": float(extreme_offset),
                        "gen_risk_offset": float(gen_offset),
                        "ml_offset": float(ml_offset),
                        "weather_offset_total": float(weather_offset),
                        "final_coefficient": float(final),
                        "effective_temp": float(effective_temp),
                        "humidity_contribution": float(humidity_contribution),
                    }
                )
                final_coeffs.append(float(round(float(final), 4)))

                if hour % 6 == 0 or hour == 47:
                    report("天气修正", hour + 1, 48, f"时段 {hour+1}/48")
        else:
            final_coeffs = [float(round(float(c), 4)) for c in base_coeffs]
            for hour in range(48):
                correction_log.append(
                    {
                        "period": hour,
                        "time_label": f"{hour//2:02d}:{30 if hour%2 else 0:02d}",
                        "base_coefficient": float(base_coeffs[hour]),
                        "pv_offset": 0.0,
                        "temp_offset": 0.0,
                        "humidity_offset": 0.0,
                        "wind_offset": 0.0,
                        "extreme_offset": 0.0,
                        "gen_risk_offset": 0.0,
                        "ml_offset": 0.0,
                        "weather_offset_total": 0.0,
                        "final_coefficient": float(base_coeffs[hour]),
                        "effective_temp": 25.0,
                        "humidity_contribution": 0.0,
                    }
                )

        report("完成", 1, 1, "预测完成")

        return {
            "coefficients": final_coeffs,
            "strategy": strategy_family,
            "half_life": float(half_life) if half_life is not None else None,
            "all_coeffs": all_coeffs,
            "correction_log": correction_log,
            "weather_48": weather_48,  # ★ DataFrame 或 None，交给 app.py 序列化
            "weather_meta": {  # ★ 前端画基准线用
                "temp_base": float(TEMP_BASE),
                "wind_base": float(WIND_BASE),
                "radiation_max": float(RADIATION_MAX_CLEAR_SKY),
            },
            "coeff_min_used": clip_min,  # ★ 新增
            "coeff_max_used": clip_max,  # ★ 新增
        }

    def _prepare_weather_data(self, weather_df, target_date):
        target = pd.to_datetime(target_date).date()
        day_df = weather_df[weather_df["time"].dt.date == target].copy()
        if len(day_df) != 24:
            raise ValueError(f"目标日期 {target} 天气数据行数 {len(day_df)}，期望24行")
        day_df = day_df.sort_values("time").reset_index(drop=True)
        df_48 = pd.DataFrame()
        for col in day_df.columns:
            if col == "time":
                times = pd.date_range(start=f"{target} 00:00", periods=48, freq="30min")
                df_48["time"] = times
            else:
                df_48[col] = np.repeat(day_df[col].values, 2)
        return df_48
