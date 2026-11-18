# regime_detector.py
"""
市场转向检测模块
在发生结构突变时，自动降低历史权重，切换到防御/快速适应模式
"""

import numpy as np
import pandas as pd
from datetime import timedelta
from utils.logger import get_logger

logger = get_logger("services.coefficient.regime_detector")


class MarketRegimeDetector:
    def __init__(self, history_df, config):
        """
        参数:
            history_df: 包含 'date' 和 '0'..'47' 列的历史价差DataFrame
            config: 配置字典或模块，包含转向检测阈值
        """
        self.history = history_df
        self.gap_cols = [str(i) for i in range(48)]
        # 阈值配置
        self.z_score_threshold = getattr(config, "REGIME_ZSCORE_THRESHOLD", 1.5)
        self.volatility_ratio_threshold = getattr(
            config, "REGIME_VOL_RATIO_THRESHOLD", 2.0
        )
        self.win_rate_threshold = getattr(config, "REGIME_WINRATE_THRESHOLD", 0.30)
        self.recent_days = getattr(config, "REGIME_RECENT_DAYS", 7)
        self.long_days = getattr(config, "REGIME_LONG_DAYS", 45)

    def detect(self, reference_date):
        logger.info(f"[转向检测] 参考日期: {reference_date.strftime('%Y-%m-%d')}")
        recent_start = reference_date - timedelta(days=self.recent_days)
        long_start = reference_date - timedelta(days=self.long_days)
        logger.info(
            f"  近期窗口: {recent_start.strftime('%Y-%m-%d')} ~ "
            f"{(reference_date - timedelta(days=1)).strftime('%Y-%m-%d')}"
        )
        logger.info(
            f"  长期窗口: {long_start.strftime('%Y-%m-%d')} ~ "
            f"{(reference_date - timedelta(days=1)).strftime('%Y-%m-%d')}"
        )

        recent_data = self.history[
            (self.history["date"] >= recent_start)
            & (self.history["date"] < reference_date)
        ]
        long_data = self.history[
            (self.history["date"] >= long_start)
            & (self.history["date"] < reference_date)
        ]

        # 数据不足：返回默认（无转向），并初始化详细结果
        if len(recent_data) < 3 or len(long_data) < 10:
            self._detection_results = [
                {
                    "hour": i,
                    "z_score": 0.0,
                    "vol_ratio": 1.0,
                    "win_rate": 0.5,
                    "shift_flag": False,
                    "confidence": 0.0,
                    "recommended_weight": 0.7,
                }
                for i in range(48)
            ]
            return [False] * 48, [0.0] * 48, [0.7] * 48

        flags = []
        confidences = []
        recommended_weights = []
        results = []

        for hour_idx, col in enumerate(self.gap_cols):
            recent_vals = recent_data[col].dropna()
            long_vals = long_data[col].dropna()

            if len(recent_vals) < 3:
                flags.append(False)
                confidences.append(0.0)
                recommended_weights.append(0.7)
                results.append(
                    {
                        "hour": hour_idx,
                        "z_score": 0.0,
                        "vol_ratio": 1.0,
                        "win_rate": 0.5,
                        "shift_flag": False,
                        "confidence": 0.0,
                        "recommended_weight": 0.7,
                    }
                )
                continue

            recent_mean = recent_vals.mean()
            long_mean = long_vals.mean()
            long_std = long_vals.std()

            # 统计突变
            z_score = 0.0 if long_std == 0 else (recent_mean - long_mean) / long_std

            # 波动异常
            recent_std = recent_vals.std()
            vol_ratio = recent_std / (long_std + 1e-6)

            # 近 3 天胜率（用长期均值方向作为"历史规律预测方向"）
            last_3_vals = recent_vals.tail(3)
            pred_direction = 1 if long_mean > 0 else -1
            recent_win_rate = float(
                (np.sign(last_3_vals) == pred_direction).sum()
            ) / len(last_3_vals)

            is_regime_shift = False
            confidence = 0.0
            reasons = []

            if abs(z_score) > self.z_score_threshold:
                is_regime_shift = True
                confidence = min(1.0, abs(z_score) / 3.0)
                reasons.append(f"Z-score={z_score:.2f}")

            if vol_ratio > self.volatility_ratio_threshold:
                is_regime_shift = True
                confidence = min(1.0, confidence + 0.3)
                reasons.append(f"Vol_ratio={vol_ratio:.2f}")

            if recent_win_rate < self.win_rate_threshold:
                is_regime_shift = True
                confidence = min(1.0, confidence + 0.4)
                reasons.append(f"Win_rate={recent_win_rate:.2f}")

            recommended_weight = (
                max(0.2, 0.7 - 0.5 * confidence) if is_regime_shift else 0.7
            )

            flags.append(is_regime_shift)
            confidences.append(confidence)
            recommended_weights.append(recommended_weight)

            results.append(
                {
                    "hour": hour_idx,
                    "z_score": z_score,
                    "vol_ratio": vol_ratio,
                    "win_rate": recent_win_rate,
                    "shift_flag": is_regime_shift,
                    "confidence": confidence,
                    "recommended_weight": recommended_weight,
                }
            )

            if is_regime_shift:
                logger.info(
                    f"时段 {col}: 转向检测触发! 原因: {', '.join(reasons)}, "
                    f"置信度: {confidence:.2f}, 历史权重: {recommended_weight:.2f}"
                )

        self._detection_results = results
        return flags, confidences, recommended_weights

    def get_detailed_data(self):
        """
        返回每个时段的详细检测指标
        返回: DataFrame，包含 'hour', 'z_score', 'vol_ratio', 'win_rate', 'shift_flag', 'confidence', 'recommended_weight'
        """
        # 注意：需要存储检测过程中的数据，或者重新计算一次。
        # 我们可以在 detect 方法中存储这些数据到实例变量，然后在这里返回。
        # 为了简单，我们假设 detect 方法已经存储了数据到 self._detection_results。
        # 如果没有存储，我们可以重新计算一次（但会耗时）
        if hasattr(self, "_detection_results"):
            return pd.DataFrame(self._detection_results)
        else:
            # 如果 detect 未被调用，返回空DataFrame
            return pd.DataFrame(
                columns=[
                    "hour",
                    "z_score",
                    "vol_ratio",
                    "win_rate",
                    "shift_flag",
                    "confidence",
                    "recommended_weight",
                ]
            )
