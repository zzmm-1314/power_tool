# ml_enhancer.py
"""
轻量级Ridge回归增强模块
用小样本预测价差偏离，作为系数微调偏移量
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
import warnings

warnings.filterwarnings("ignore")


class RidgeGapPredictor:
    def __init__(self, alpha=1.0):
        """
        alpha: 正则化强度，越大越保守（防过拟合）
        """
        self.alpha = alpha
        self.models = {}  # 每个时段一个模型
        self.scalers = {}  # 每个时段一个标准化器
        self.is_trained = False

    def _create_features(
        self, series, weather_row=None, ext_ratio=None, load_ratio=None
    ):
        """
        针对单个时段（48点中的某一点）构建特征矩阵
        series: 该时段的历史价差序列（长度=天数）
        """
        n = len(series)
        # 初始化特征矩阵
        features = []

        # 滞后特征
        for lag in [1, 2, 7, 14]:
            if n > lag:
                # 用pad方式对齐：前面补0
                lagged = np.roll(series, lag)
                lagged[:lag] = np.nan
                features.append(lagged)
            else:
                features.append(np.full(n, np.nan))

        # 滚动统计（7天均值）
        if n > 7:
            roll_mean = pd.Series(series).rolling(7, min_periods=1).mean().values
            features.append(roll_mean)
        else:
            features.append(np.full(n, np.nan))

        # 滚动标准差
        if n > 7:
            roll_std = (
                pd.Series(series).rolling(7, min_periods=1).std().fillna(0).values
            )
            features.append(roll_std)
        else:
            features.append(np.full(n, np.nan))

        # 拼成矩阵 (n_samples, n_features)
        X = np.column_stack(features)
        # 用该样本的均值填充NaN（简单处理）
        for col in range(X.shape[1]):
            col_mean = np.nanmean(X[:, col])
            if np.isnan(col_mean):
                col_mean = 0
            X[np.isnan(X[:, col]), col] = col_mean

        return X

    def train(
        self, history_df, weather_df=None, external_series=None, load_series=None
    ):
        """
        对每个时段独立训练Ridge模型
        history_df: 包含 'date' 和 '0'..'47' 列
        """
        gap_cols = [str(i) for i in range(48)]
        dates = history_df["date"].values

        for col in gap_cols:
            series = history_df[col].values
            if len(series) < 30:  # 少于30天不训练
                continue

            # 构建特征矩阵 (T, F)
            X = self._create_features(series)
            # 目标：预测下一天的价差（用滞后一期的价差作为目标）
            y = series[1:]  # 从第2天开始
            X = X[:-1]  # 去掉最后一天（无目标）

            # 移除前几天的无效数据（因为lag导致nan较多）
            valid_mask = ~np.isnan(y)
            X = X[valid_mask]
            y = y[valid_mask]

            if len(y) < 20:
                continue

            # 标准化
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            # 训练Ridge（使用时间序列交叉验证选alpha，但小样本下直接用固定alpha）
            model = Ridge(alpha=self.alpha)
            model.fit(X_scaled, y)

            # 保存模型和标准化器
            self.models[col] = model
            self.scalers[col] = scaler

        self.is_trained = True
        print(f"ML增强模块训练完成，成功建模时段: {len(self.models)}/48")

    def predict_offset(
        self, hour, recent_series, weather_row=None, ext_ratio=None, load_ratio=None
    ):
        """
        预测某个时段的价差偏离，并转换为系数偏移量
        返回: float，范围 [-0.05, 0.05]
        """
        col = str(hour)
        if col not in self.models:
            return 0.0

        # 构建当前时刻的特征（用最新数据）
        # 这里简化处理：用最近14天的数据构造特征向量
        # 但实际上我们只需要当前时刻的滞后值
        if len(recent_series) < 14:
            return 0.0

        # 提取最新的滞后特征
        latest = recent_series[-1]
        lag1 = recent_series[-2] if len(recent_series) >= 2 else latest
        lag2 = recent_series[-3] if len(recent_series) >= 3 else latest
        lag7 = recent_series[-8] if len(recent_series) >= 8 else latest
        lag14 = recent_series[-15] if len(recent_series) >= 15 else latest
        roll_mean = np.mean(recent_series[-7:])
        roll_std = np.std(recent_series[-7:]) if len(recent_series) >= 7 else 0

        # 特征向量（必须与训练时的顺序一致）
        X_pred = np.array([[lag1, lag2, lag7, lag14, roll_mean, roll_std]])

        # 标准化
        scaler = self.scalers[col]
        X_pred_scaled = scaler.transform(X_pred)

        # 预测价差
        pred_gap = self.models[col].predict(X_pred_scaled)[0]

        # 将预测价差映射为系数偏移量
        # 规则：价差每偏离0元10元，系数偏移0.03（这个系数可配置）
        offset = np.clip(pred_gap / 10 * 0.03, -0.05, 0.05)

        return offset
