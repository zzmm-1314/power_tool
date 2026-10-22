# history_analyzer.py
import numpy as np
import pandas as pd
from .coefficient_config import (
    WINDOW_DAYS,
    WINSOR_PROB,
    STRATEGY_SPECS,
    HALF_LIVES,
    COEFF_MIN,
    COEFF_MAX,
)
from .utils import progress_iterator


def clamp(values, lower, upper):
    return np.clip(values, lower, upper)


def winsorize_values(values: np.ndarray, prob: float) -> np.ndarray:
    """截尾处理：去除两端极端值"""
    if len(values) <= 1 or prob <= 0:
        return values.copy()
    lower = np.quantile(values, prob, method="median_unbiased")
    upper = np.quantile(values, 1 - prob, method="median_unbiased")
    return clamp(values, lower, upper)


def apply_gap_processing(
    values: np.ndarray, hard_cap: float | None = None
) -> np.ndarray:
    """价差预处理：Winsorize + 可选硬截断"""
    adjusted = winsorize_values(values, WINSOR_PROB)
    if hard_cap is not None:
        adjusted = clamp(adjusted, -hard_cap, hard_cap)
    return adjusted


def compute_expectation_coefficient(
    values: np.ndarray | pd.Series,
    dates: np.ndarray | pd.Series,
    reference_date: pd.Timestamp,
    half_life: float,
    hard_cap: float | None = None,
) -> dict:
    """
    【核心算法】基于期望值（盈亏比）计算申报系数
    替代原有的"胜率映射"逻辑

    公式：coefficient = 2 × 正收益 / (正收益 + 负风险)
    其中 正收益 = 加权平均正向价差，负风险 = 加权平均负向价差绝对值
    """
    values = pd.to_numeric(pd.Series(values), errors="coerce")
    dates = pd.to_datetime(pd.Series(dates), errors="coerce")
    valid_mask = values.notna() & dates.notna()

    values = values.loc[valid_mask].to_numpy(dtype=float)
    dates = dates.loc[valid_mask]
    if pd.isna(reference_date):
        return {
            "sample_days": 0,
            "effective_sample_size": 0.0,
            "positive_rate": 0.5,
            "weighted_mean_gap": 0.0,
            "positive_gain": 0.0,
            "negative_risk": 0.0,
            "coefficient": 1.0,
        }

    if len(values) == 0:
        return {
            "sample_days": 0,
            "effective_sample_size": 0.0,
            "positive_rate": 0.5,
            "weighted_mean_gap": 0.0,
            "positive_gain": 0.0,
            "negative_risk": 0.0,
            "coefficient": 1.0,
        }

    # ========== 新增：计算天数差时处理可能的 NaT ==========
    age_series = (reference_date - dates).dt.days
    # 将任何无效值（如 NaT）替换为 0
    ages = age_series.fillna(0).to_numpy(dtype=float)
    ages = np.maximum(ages, 0)

    weights = np.power(0.5, ages / half_life)

    # ========== 新增：检查 weights 是否全为 nan 或 0 ==========
    if np.all(np.isnan(weights)) or np.sum(weights) == 0:
        return {
            "sample_days": int(len(values)),
            "effective_sample_size": 0.0,
            "positive_rate": 0.5,
            "weighted_mean_gap": 0.0,
            "positive_gain": 0.0,
            "negative_risk": 0.0,
            "coefficient": 1.0,
        }

    weights = weights / weights.sum()
    if len(values) == 0:
        return {
            "sample_days": 0,
            "effective_sample_size": 0.0,
            "positive_rate": 0.5,
            "weighted_mean_gap": 0.0,
            "positive_gain": 0.0,
            "negative_risk": 0.0,
            "coefficient": 1.0,
        }

    # 指数衰减权重（越近权重越大）
    ages = np.maximum((reference_date - dates).dt.days.to_numpy(dtype=float), 0)
    weights = np.power(0.5, ages / half_life)
    weights = weights / weights.sum()

    # 预处理价差
    adjusted_values = apply_gap_processing(values, hard_cap=hard_cap)

    # 正收益 = 所有正价差的加权和（也就是加权平均正向价差）
    positive_gain = float(np.sum(weights * np.maximum(adjusted_values, 0)))
    # 负风险 = 所有负价差绝对值的加权和
    negative_risk = float(np.sum(weights * np.maximum(-adjusted_values, 0)))

    # ===================================
    # 计算系数 = 2 * 正收益 / (正收益 + 负风险)
    total_signal = positive_gain + negative_risk
    coefficient = 2 * positive_gain / total_signal if total_signal > 0 else 1.0
    if abs(positive_gain) < 1e-6 and abs(negative_risk) < 1e-6:
        print(f"警告: 正收益和负风险均为0，系数设为1.0")
    # 额外指标
    non_zero_mask = adjusted_values != 0
    non_zero_weight = float(np.sum(weights[non_zero_mask]))
    positive_rate = (
        float(np.sum(weights[adjusted_values > 0]) / non_zero_weight)
        if non_zero_weight > 0
        else 0.5
    )

    return {
        "sample_days": int(len(values)),
        "effective_sample_size": float(1 / np.sum(np.square(weights))),
        "positive_rate": positive_rate,
        "weighted_mean_gap": float(np.sum(weights * adjusted_values)),
        "positive_gain": positive_gain,
        "negative_risk": negative_risk,
        "coefficient": float(clamp(coefficient, COEFF_MIN, COEFF_MAX)),
    }


def compute_all_strategies_coefficients(
    gap_matrix: pd.DataFrame,
    dates: pd.Series,
    reference_date: pd.Timestamp,
    progress_callback=None,
) -> pd.DataFrame:
    """
    计算所有策略族 × 所有半衰期的48点系数
    返回长格式DataFrame
    """
    rows = []
    combinations = [
        (spec, half_life) for spec in STRATEGY_SPECS for half_life in HALF_LIVES
    ]
    total_combos = len(combinations)

    for i, (spec, half_life) in enumerate(combinations):
        if progress_callback:
            try:
                progress_callback(
                    "系数计算",
                    i,
                    total_combos,
                    f"{spec['strategy_family']} HL={half_life}",
                )
            except Exception:
                pass

        for point_index, column_name in enumerate(gap_matrix.columns):
            metrics = compute_expectation_coefficient(
                values=gap_matrix[column_name],
                dates=dates,
                reference_date=reference_date,
                half_life=half_life,
                hard_cap=spec["hard_cap"],
            )
            rows.append(
                {
                    "strategy_family": spec["strategy_family"],
                    "half_life": half_life,
                    "point": point_index,
                    **metrics,
                }
            )

    if progress_callback:
        try:
            progress_callback("系数计算", total_combos, total_combos, "完成")
        except Exception:
            pass

    return pd.DataFrame(rows)


def select_best_strategy(backtest_df: pd.DataFrame) -> dict:
    """
    根据回测结果选择最优策略组合（累计PnL最高）
    """
    if backtest_df is None or backtest_df.empty:
        return {
            "strategy_family": "Strategy A",
            "half_life": 7,
            "cumulative_pnl": 0.0,
        }

    # 计算每个策略组合的最后累计PnL
    latest_pnl = (
        backtest_df.groupby(["strategy_family", "half_life"])["cumulative_pnl"]
        .last()
        .reset_index()
    )
    # 找到最高累计PnL的行索引（整数位置）
    best_idx = latest_pnl["cumulative_pnl"].idxmax()
    best_row = latest_pnl.iloc[best_idx]  # pyright: ignore[reportCallIssue]

    return {
        "strategy_family": best_row["strategy_family"],
        "half_life": best_row["half_life"],
        "cumulative_pnl": best_row["cumulative_pnl"],
    }


def get_dynamic_hist_weight(win_rate, shift_flag, config):
    """
    根据胜率和转向标志计算历史权重
    正常：胜率偏离50%越远，历史权重越高（范围0.3~0.9）
    转向：历史权重降低（乘以0.5，最低0.2）
    """
    # 基础权重：偏离50%越远，权重越高
    deviation = abs(win_rate - 0.5) / 0.5  # 0~1
    base_weight = 0.5 + 0.4 * deviation  # 0.5~0.9
    # 限制范围
    hist_weight = max(0.3, min(0.9, base_weight))

    # 转向时降低历史权重
    if shift_flag:
        hist_weight = max(0.2, hist_weight * 0.5)  # 减半，最低0.2

    return hist_weight
