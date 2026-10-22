# backtest_engine.py
import pandas as pd
import numpy as np
from datetime import timedelta
from .coefficient_config import (
    STRATEGY_SPECS,
    HALF_LIVES,
    D_OFFSET,
    WINDOW_DAYS,
    EXPECTED_MWH,
    WINSOR_PROB,
    HARD_CAP,
)
from .history_analyzer import compute_expectation_coefficient
from .utils import progress_iterator

print(f"回测使用: WINSOR_PROB={WINSOR_PROB}, HARD_CAP={HARD_CAP}")


def compute_incremental_pnl(coefficient: float, actual_gap: float) -> float:
    """计算单点单时段的增量PnL"""
    if pd.isna(coefficient) or pd.isna(actual_gap):
        return np.nan
    return EXPECTED_MWH * (coefficient - 1) * actual_gap


def run_recent_backtest(
    history_df, d_offset=D_OFFSET, window_days=WINDOW_DAYS, progress_callback=None
):
    """
    运行最近1个月的回测，评估各策略组合的累计PnL
    """
    if history_df is None or len(history_df) < window_days + 30:
        return None

    gap_cols = [str(i) for i in range(48)]

    history_df["is_all_zero"] = history_df[gap_cols].apply(
        lambda row: np.all(np.abs(row) < 1e-6), axis=1
    )
    clean_df = history_df[~history_df["is_all_zero"]].copy()
    clean_df.drop(columns=["is_all_zero"], inplace=True)
    print(f"过滤掉全0日期后剩余 {len(clean_df)} 天")

    dates = clean_df["date"].sort_values().unique()
    latest_date = dates[-1]
    start_date = latest_date - timedelta(days=30)

    rows = []
    target_indices = []
    for target_idx in range(len(dates)):
        target_date = dates[target_idx]
        if target_date < start_date or target_date > latest_date:
            continue
        usable_idx = target_idx - d_offset
        if usable_idx < window_days - 1:
            continue
        target_indices.append(target_idx)

    if len(target_indices) < 5:
        print(f"回测日不足：仅 {len(target_indices)} 天")
        return None

    total_targets = len(target_indices)
    for i, target_idx in enumerate(target_indices):
        if progress_callback:
            try:
                progress_callback(
                    "回测评估",
                    i + 1,
                    total_targets,
                    dates[target_idx].strftime("%Y-%m-%d"),
                )
            except Exception:
                pass

        target_date = dates[target_idx]
        usable_idx = target_idx - d_offset
        window_start = usable_idx - window_days + 1
        window_dates = dates[window_start : usable_idx + 1]
        window_data = clean_df[clean_df["date"].isin(window_dates)].sort_values("date")

        zero_mask = window_data[gap_cols].apply(
            lambda row: np.all(np.abs(row) < 1e-6), axis=1
        )
        window_data = window_data[~zero_mask].copy()

        if len(window_data) < max(10, window_days * 0.3):
            continue

        reference_date = dates[usable_idx]

        actual_gaps = (
            clean_df[clean_df["date"] == target_date][gap_cols]
            .iloc[0]
            .to_numpy(dtype=float)
        )

        for spec in STRATEGY_SPECS:
            for half_life in HALF_LIVES:
                daily_pnl = 0.0
                for point_idx, col in enumerate(gap_cols):
                    coeff_data = compute_expectation_coefficient(
                        values=window_data[col],
                        dates=window_data["date"],
                        reference_date=reference_date,
                        half_life=half_life,
                        hard_cap=spec["hard_cap"],
                    )
                    coeff = coeff_data["coefficient"]
                    pnl = compute_incremental_pnl(coeff, actual_gaps[point_idx])
                    if not np.isnan(pnl):
                        daily_pnl += pnl

                rows.append(
                    {
                        "date": target_date.strftime("%Y-%m-%d"),
                        "strategy_family": spec["strategy_family"],
                        "half_life": half_life,
                        "daily_pnl": daily_pnl,
                    }
                )

    if not rows:
        return None

    backtest_df = pd.DataFrame(rows)
    backtest_df["cumulative_pnl"] = backtest_df.groupby(
        ["strategy_family", "half_life"]
    )["daily_pnl"].cumsum()
    return backtest_df
