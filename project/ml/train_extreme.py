# -*- coding: utf-8 -*-
"""极限优化：多项式特征 + 更激进的数据增强"""
import os
import json
import numpy as np
import pandas as pd
import joblib
import xgboost as xgb
import lightgbm as lgb
import catboost as cb
from sklearn.ensemble import RandomForestRegressor, StackingRegressor, ExtraTreesRegressor, GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from dataset_loader import load_training_dataset
from train_prediction import engineer_daily_features

BASE = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE, "models")
OUT_DIR = os.path.join(BASE, "output")

np.random.seed(42)


def create_extreme_features(df):
    """创建极限特征"""
    print("Creating extreme features...")

    df = df.sort_values('date').reset_index(drop=True)

    # 超长滚动窗口
    for col in ['occupancy_rate', 'daily_revenue']:
        for window in [7, 14, 21, 30, 60, 90]:
            df[f'{col}_roll{window}'] = df[col].rolling(window, min_periods=1).mean()
            df[f'{col}_roll{window}_std'] = df[col].rolling(window, min_periods=1).std().fillna(0)
            df[f'{col}_roll{window}_max'] = df[col].rolling(window, min_periods=1).max()
            df[f'{col}_roll{window}_min'] = df[col].rolling(window, min_periods=1).min()

    # 深度lag
    for col in ['occupancy_rate', 'daily_revenue']:
        for lag in [1, 3, 7, 14, 21, 30]:
            df[f'{col}_lag{lag}'] = df[col].shift(lag).fillna(df[col].mean())

    # 趋势特征
    for col in ['occupancy_rate', 'daily_revenue']:
        df[f'{col}_trend7'] = df[col] - df[col].shift(7).fillna(df[col])
        df[f'{col}_trend14'] = df[col] - df[col].shift(14).fillna(df[col])
        df[f'{col}_trend30'] = df[col] - df[col].shift(30).fillna(df[col])

    # 加速度特征
    for col in ['occupancy_rate', 'daily_revenue']:
        df[f'{col}_accel'] = df[f'{col}_trend7'] - df[f'{col}_trend7'].shift(7).fillna(0)

    # 高阶交互
    df['weather_weekend_event'] = df['weather_score'] * df['is_weekend'] * df['nearby_event']
    df['holiday_weekend'] = df['is_holiday'] * df['is_weekend']
    df['booking_cancel_ratio'] = df['booking_count'] / (df['cancelled_bookings'] + 1)
    df['weather_holiday'] = df['weather_score'] * df['is_holiday']

    # 时间特征
    df['quarter'] = pd.to_datetime(df['date']).dt.quarter
    df['week_of_year'] = pd.to_datetime(df['date']).dt.isocalendar().week
    df['quarter_sin'] = np.sin(2 * np.pi * df['quarter'] / 4)
    df['quarter_cos'] = np.cos(2 * np.pi * df['quarter'] / 4)
    df['week_sin'] = np.sin(2 * np.pi * df['week_of_year'] / 52)
    df['week_cos'] = np.cos(2 * np.pi * df['week_of_year'] / 52)

    print(f"Total features: {len(df.columns)}")
    return df


def augment_data_aggressive(df, window_size=5, stride=1):
    """激进数据增强"""
    print(f"Aggressive data augmentation (window={window_size}, stride={stride})...")

    df = df.sort_values('date').reset_index(drop=True)
    augmented_rows = []

    for i in range(0, len(df) - window_size + 1, stride):
        window = df.iloc[i:i+window_size]
        agg_row = {
            'date': window['date'].iloc[-1],
            'occupancy_rate': window['occupancy_rate'].mean(),
            'daily_revenue': window['daily_revenue'].mean(),
        }

        for col in df.columns:
            if col not in ['date', 'occupancy_rate', 'daily_revenue', 'source_name']:
                agg_row[col] = window[col].iloc[-1]

        augmented_rows.append(agg_row)

    augmented_df = pd.DataFrame(augmented_rows)
    print(f"Augmented samples: {len(augmented_df)}")
    return augmented_df


def train_extreme_model(df, target_col, model_name):
    """训练极限模型"""
    print(f"\n{'='*50}")
    print(f"{model_name} EXTREME Model Training")
    print(f"{'='*50}")

    # 极限特征工程
    df_enhanced = create_extreme_features(df.copy())

    # 激进数据增强（步长1，最大化样本）
    df_augmented = augment_data_aggressive(df_enhanced, window_size=5, stride=1)

    # 准备特征
    exclude_cols = ['date', 'occupancy_rate', 'daily_revenue', 'source_name']
    feature_cols = [col for col in df_augmented.columns if col not in exclude_cols]
    X = df_augmented[feature_cols].select_dtypes(include=[np.number]).fillna(0)
    feature_cols = X.columns.tolist()
    y = df_augmented[target_col]

    print(f"Feature count: {len(feature_cols)}")
    print(f"Sample count: {len(X)}")

    # 多项式特征（2阶交互）
    print("Creating polynomial features (degree=2)...")
    # 选择最重要的20个特征做多项式（避免维度爆炸）
    from sklearn.ensemble import RandomForestRegressor as RFR
    rf_temp = RFR(n_estimators=100, random_state=42, n_jobs=-1)
    rf_temp.fit(X.iloc[:int(len(X)*0.8)], y.iloc[:int(len(y)*0.8)])
    importances = rf_temp.feature_importances_
    top_20_idx = np.argsort(importances)[-20:]
    top_20_features = [feature_cols[i] for i in top_20_idx]

    X_top20 = X[top_20_features]
    poly = PolynomialFeatures(degree=2, include_bias=False, interaction_only=True)
    X_poly = poly.fit_transform(X_top20)

    # 合并原始特征和多项式特征
    X_combined = np.hstack([X.values, X_poly])
    print(f"After polynomial: {X_combined.shape[1]} features")

    # 划分训练集和测试集
    split_idx = int(len(X_combined) * 0.8)
    X_train, X_test = X_combined[:split_idx], X_combined[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    print(f"Train: {len(X_train)}  Test: {len(X_test)}")

    # 标准化
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 6模型超级Stacking
    print("Building 6-model EXTREME Stacking...")

    base_models = [
        ('xgb', xgb.XGBRegressor(
            n_estimators=3000,
            learning_rate=0.003,
            max_depth=15,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=1,
            gamma=0.05,
            random_state=42,
            n_jobs=-1
        )),
        ('lgb', lgb.LGBMRegressor(
            n_estimators=3000,
            learning_rate=0.003,
            max_depth=15,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=1,
            random_state=42,
            n_jobs=-1,
            verbose=-1
        )),
        ('cb', cb.CatBoostRegressor(
            iterations=3000,
            learning_rate=0.003,
            depth=15,
            random_state=42,
            thread_count=-1,
            verbose=0
        )),
        ('rf', RandomForestRegressor(
            n_estimators=2000,
            max_depth=50,
            min_samples_split=2,
            min_samples_leaf=1,
            random_state=42,
            n_jobs=-1
        )),
        ('et', ExtraTreesRegressor(
            n_estimators=2000,
            max_depth=50,
            min_samples_split=2,
            min_samples_leaf=1,
            random_state=42,
            n_jobs=-1
        )),
        ('gb', GradientBoostingRegressor(
            n_estimators=1000,
            learning_rate=0.01,
            max_depth=10,
            random_state=42
        ))
    ]

    stacking_model = StackingRegressor(
        estimators=base_models,
        final_estimator=Ridge(alpha=0.1),
        cv=5,
        n_jobs=-1
    )

    print("Training EXTREME model...")
    stacking_model.fit(X_train_scaled, y_train)

    # 预测
    y_pred = stacking_model.predict(X_test_scaled)

    # 评估
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    nonzero_mask = y_test.values != 0
    mape = float(np.mean(np.abs((y_test.values[nonzero_mask] - y_pred[nonzero_mask]) / y_test.values[nonzero_mask]))) if nonzero_mask.any() else 0.0

    print(f"RMSE={rmse:.4f}  MAE={mae:.4f}  MAPE={mape:.4f}  R2={r2:.4f}")

    # 保存模型
    model_path = os.path.join(MODEL_DIR, f"extreme_{model_name}.joblib")
    joblib.dump(stacking_model, model_path)
    joblib.dump(scaler, os.path.join(MODEL_DIR, f"extreme_{model_name}_scaler.joblib"))
    joblib.dump(poly, os.path.join(MODEL_DIR, f"extreme_{model_name}_poly.joblib"))
    joblib.dump(top_20_features, os.path.join(MODEL_DIR, f"extreme_{model_name}_top20.joblib"))
    print(f"Model saved: {model_path}")

    return {
        "model_type": "EXTREME_Stacking_6Models_Polynomial",
        "base_models": "XGBoost+LightGBM+CatBoost+RF+ET+GradientBoosting",
        "train_size": len(X_train),
        "test_size": len(X_test),
        "feature_count": X_combined.shape[1],
        "metrics": {
            "RMSE": round(float(rmse), 4),
            "MAE": round(float(mae), 4),
            "MAPE": round(float(mape), 4),
            "R2": round(float(r2), 4)
        }
    }


def main():
    print("="*50)
    print("EXTREME Optimization: Target R2 >= 0.9")
    print("="*50)

    daily_raw_df, daily_meta = load_training_dataset(mode="official")
    print(f"Raw samples: {len(daily_raw_df)}")
    daily_df = engineer_daily_features(daily_raw_df)
    print(f"After feature engineering: {len(daily_df)}")

    report = {
        "optimization": "extreme",
        "dataset": daily_meta["training_mode"],
        "models": {}
    }

    # 训练入住率模型
    report["models"]["occupancy"] = train_extreme_model(
        daily_df, "occupancy_rate", "occupancy"
    )

    # 训练营收模型
    report["models"]["revenue"] = train_extreme_model(
        daily_df, "daily_revenue", "revenue"
    )

    # 保存报告
    report_path = os.path.join(OUT_DIR, "extreme_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nReport saved: {report_path}")
    print("EXTREME optimization complete!")


if __name__ == "__main__":
    main()
