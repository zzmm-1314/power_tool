# regime_detector.py
"""
市场转向检测模块
在发生结构突变时，自动降低历史权重，切换到防御/快速适应模式
"""

import numpy as np
import pandas as pd
from datetime import timedelta


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
        """
        对每个时段分别检测转向，返回48点的检测结果
        返回: (regime_shift_flags, confidence_scores, recommended_hist_weight)
        """
        print(f"[转向检测] 参考日期: {reference_date.strftime('%Y-%m-%d')}")
        recent_start = reference_date - timedelta(days=self.recent_days)
        long_start = reference_date - timedelta(days=self.long_days)
        print(
            f"  近期窗口: {recent_start.strftime('%Y-%m-%d')} ~ {(reference_date - timedelta(days=1)).strftime('%Y-%m-%d')}"
        )
        print(
            f"  长期窗口: {long_start.strftime('%Y-%m-%d')} ~ {(reference_date - timedelta(days=1)).strftime('%Y-%m-%d')}"
        )
        # 数据准备
        recent_data = self.history[
            (self.history["date"] >= recent_start)
            & (self.history["date"] < reference_date)
        ]
        long_data = self.history[
            (self.history["date"] >= long_start)
            & (self.history["date"] < reference_date)
        ]

        # 如果数据不足，返回默认（无转向）
        if len(recent_data) < 3 or len(long_data) < 10:
            return [False] * 48, [0.0] * 48, 0.7

        flags = []
        confidences = []
        recommended_weights = []

        for col in self.gap_cols:
            recent_vals = recent_data[col].dropna()
            long_vals = long_data[col].dropna()

            if len(recent_vals) < 3:
                flags.append(False)
                confidences.append(0.0)
                recommended_weights.append(0.7)
                continue

            recent_mean = recent_vals.mean()
            long_mean = long_vals.mean()
            long_std = long_vals.std()

            # ---------- 统计突变检测 ----------
            if long_std == 0:
                z_score = 0.0
            else:
                z_score = (recent_mean - long_mean) / long_std

            # ---------- 波动异常检测 ----------
            recent_std = recent_vals.std()
            vol_ratio = recent_std / (long_std + 1e-6)

            # ---------- 近3天胜率检测 ----------
            # 计算近3天用历史规律判断方向的正确率（简化：用近期均值方向）
            if len(recent_vals) >= 3:
                # 用 long_mean 的方向作为"历史规律预测方向"，与 recent_vals 实际方向对比
                pred_direction = 1 if long_mean > 0 else -1
                # 最近3天的实际方向（取最后3天均值方向）
                last_3_vals = (
                    recent_vals.tail(3) if len(recent_vals) >= 3 else recent_vals
                )
                actual_direction = 1 if last_3_vals.mean() > 0 else -1
                # 如果预测方向与实际方向不一致，算作"预测失败"
                recent_win_rate = 1.0 if pred_direction == actual_direction else 0.0
                # 考虑到只有3个点，胜率只有0或1，过于严格。使用更温和的评估：
                # 计算预测方向与实际价差的相关系数（如果>0说明方向正确）
                if len(last_3_vals) >= 3:
                    pred_series = np.sign(last_3_vals)  # 实际符号
                    pred_consensus = np.sign(long_mean)  # 预测符号
                    # 如果大多数时段方向一致，则判为正确
                    correct_count = (pred_series == pred_consensus).sum()
                    recent_win_rate = correct_count / len(pred_series)
                else:
                    recent_win_rate = (
                        1.0 if (long_mean * last_3_vals.mean() > 0) else 0.0
                    )
            else:
                recent_win_rate = 0.5

            # ---------- 综合判定 ----------
            is_regime_shift = False
            confidence = 0.0
            reasons = []

            # 检测到统计突变
            if abs(z_score) > self.z_score_threshold:
                is_regime_shift = True
                confidence = min(1.0, abs(z_score) / 3.0)  # 最大到1
                reasons.append(f"Z-score={z_score:.2f}")

            # 检测到波动异常
            if vol_ratio > self.volatility_ratio_threshold:
                is_regime_shift = True
                confidence = min(1.0, confidence + 0.3)  # 叠加
                reasons.append(f"Vol_ratio={vol_ratio:.2f}")

            # 检测到胜率崩盘
            if recent_win_rate < self.win_rate_threshold:
                is_regime_shift = True
                confidence = min(1.0, confidence + 0.4)
                reasons.append(f"Win_rate={recent_win_rate:.2f}")

            # 计算推荐的历史权重
            if is_regime_shift:
                # 转向时，历史权重大幅降低，最低降至0.2
                # 权重 = 0.7 - 0.5 * confidence
                recommended_weight = max(0.2, 0.7 - 0.5 * confidence)
            else:
                recommended_weight = 0.7

            flags.append(is_regime_shift)
            confidences.append(confidence)
            recommended_weights.append(recommended_weight)

            # 调试信息（可注释掉）
            if is_regime_shift:
                print(
                    f"时段 {col}: 转向检测触发! 原因: {', '.join(reasons)}, 置信度: {confidence:.2f}, 历史权重: {recommended_weight:.2f}"
                )
        results = []
        for hour_idx, col in enumerate(self.gap_cols):
            # ... 计算各项指标 ...
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
