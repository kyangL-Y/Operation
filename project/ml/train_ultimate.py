# -*- coding: utf-8 -*-
"""终极优化：冲刺R²>0.9"""
import os
import json
import numpy as np
import pandas as pd
import joblib
import matplotlib
import matplotlib.pyplot as plt
import xgboost as xgb
import lightgbm as lgb
import catboost as cb
from sklearn.ensemble import RandomForestRegressor, StackingRegressor, ExtraTreesRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from dataset_loader import load_training_dataset
from train_prediction import engineer_daily_features, DAILY_BASE_FEATURES

matplotlib.use("Agg")
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial"]
plt.rcParams["axes.unicode_minus"] = False

BASE = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE, "models")
OUT_DIR = os.path.join(BASE, "output")

np.random.seed(42)


def create_advanced_features(df):
    """Create advanced features"""
    print("Creating advanced features...")

    # 按日期排序
    df = df.sort_values('date').reset_index(drop=True)

    # 超长滚动窗口（30天、60天、90天）
    for col in ['occupancy_rate', 'daily_revenue']:
        df[f'{col}_roll30'] = df[col].rolling(30, min_periods=1).mean()
        df[f'{col}_roll60'] = df[col].rolling(60, min_periods=1).mean()
        df[f'{col}_roll90'] = df[col].rolling(90, min_periods=1).mean()
        df[f'{col}_roll30_std'] = df[col].rolling(30, min_periods=1).std().fillna(0)

    # 深度lag特征
    for col in ['occupancy_rate', 'daily_revenue']:
        for lag in [14, 21, 30]:
            df[f'{col}_lag{lag}'] = df[col].shift(lag).fillna(df[col].mean())

    # 趋势特征
    df['occ_trend_14'] = df['occupancy_rate'] - df['occupancy_rate'].shift(14).fillna(df['occupancy_rate'])
    df['rev_trend_14'] = df['daily_revenue'] - df['daily_revenue'].shift(14).fillna(df['daily_revenue'])

    # 高阶交互特征
    df['weather_weekend_event'] = df['weather_score'] * df['is_weekend'] * df['nearby_event']
    df['holiday_weekend'] = df['is_holiday'] * df['is_weekend']
    df['booking_cancel_ratio'] = df['booking_count'] / (df['cancelled_bookings'] + 1)

    # 时间特征增强
    df['quarter'] = pd.to_datetime(df['date']).dt.quarter
    df['week_of_year'] = pd.to_datetime(df['date']).dt.isocalendar().week
    df['quarter_sin'] = np.sin(2 * np.pi * df['quarter'] / 4)
    df['quarter_cos'] = np.cos(2 * np.pi * df['quarter'] / 4)

    print(f"Total features: {len(df.columns)}")
    return df


def augment_data_sliding_window(df, window_size=7, stride=3):
    """Data augmentation: sliding window"""
    print(f"Data augmentation: sliding window (window={window_size} days, stride={stride} days)...")

    df = df.sort_values('date').reset_index(drop=True)
    augmented_rows = []

    for i in range(0, len(df) - window_size + 1, stride):
        window = df.iloc[i:i+window_size]
        # 聚合窗口内的数据
        agg_row = {
            'date': window['date'].iloc[-1],  # 使用窗口最后一天
            'occupancy_rate': window['occupancy_rate'].mean(),
            'daily_revenue': window['daily_revenue'].mean(),
        }

        # 其他特征取最后一天的值
        for col in df.columns:
            if col not in ['date', 'occupancy_rate', 'daily_revenue', 'source_name']:
                agg_row[col] = window[col].iloc[-1]

        augmented_rows.append(agg_row)

    augmented_df = pd.DataFrame(augmented_rows)
    print(f"Augmented samples: {len(augmented_df)}")
    return augmented_df


def train_ultimate_model(df, target_col, model_name):
    """Train ultimate model"""
    print(f"\n{'='*50}")
    print(f"{model_name} Ultimate Model Training")
    print(f"{'='*50}")

    # 创建高级特征
    df_enhanced = create_advanced_features(df.copy())

    # 数据增强
    df_augmented = augment_data_sliding_window(df_enhanced, window_size=7, stride=2)

    # 准备特征
    exclude_cols = ['date', 'occupancy_rate', 'daily_revenue', 'source_name']
    feature_cols = [col for col in df_augmented.columns if col not in exclude_cols]

    # Select only numeric columns
    X = df_augmented[feature_cols].select_dtypes(include=[np.number]).fillna(0)
    feature_cols = X.columns.tolist()  # Update feature_cols to only numeric
    y = df_augmented[target_col]

    print(f"Feature count: {len(feature_cols)}")
    print(f"Sample count: {len(X)}")

    # Split train/test (time series split)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    print(f"Train: {len(X_train)}  Test: {len(X_test)}")

    # Standardization
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Build super Stacking model
    print("Building 5-model Stacking ensemble...")

    base_models = [
        ('xgb', xgb.XGBRegressor(
            n_estimators=2000,
            learning_rate=0.005,
            max_depth=12,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            gamma=0.1,
            random_state=42,
            n_jobs=-1
        )),
        ('lgb', lgb.LGBMRegressor(
            n_estimators=2000,
            learning_rate=0.005,
            max_depth=12,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            random_state=42,
            n_jobs=-1,
            verbose=-1
        )),
        ('cb', cb.CatBoostRegressor(
            iterations=2000,
            learning_rate=0.005,
            depth=12,
            random_state=42,
            verbose=0
        )),
        ('rf', RandomForestRegressor(
            n_estimators=1500,
            max_depth=40,
            min_samples_split=2,
            min_samples_leaf=1,
            random_state=42,
            n_jobs=-1
        )),
        ('et', ExtraTreesRegressor(
            n_estimators=1500,
            max_depth=40,
            min_samples_split=2,
            min_samples_leaf=1,
            random_state=42,
            n_jobs=-1
        ))
    ]

    stacking_model = StackingRegressor(
        estimators=base_models,
        final_estimator=Ridge(alpha=0.5),
        cv=5,
        n_jobs=-1
    )

    print("Training...")
    stacking_model.fit(X_train_scaled, y_train)

    # Predict
    y_pred = stacking_model.predict(X_test_scaled)

    # Evaluate
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    nonzero_mask = y_test.values != 0
    mape = float(np.mean(np.abs((y_test.values[nonzero_mask] - y_pred[nonzero_mask]) / y_test.values[nonzero_mask]))) if nonzero_mask.any() else 0.0

    print(f"RMSE={rmse:.4f}  MAE={mae:.4f}  MAPE={mape:.4f}  R2={r2:.4f}")

    # Save model
    model_path = os.path.join(MODEL_DIR, f"ultimate_{model_name}.joblib")
    joblib.dump(stacking_model, model_path)
    joblib.dump(scaler, os.path.join(MODEL_DIR, f"ultimate_{model_name}_scaler.joblib"))
    joblib.dump(feature_cols, os.path.join(MODEL_DIR, f"ultimate_{model_name}_features.joblib"))
    print(f"Model saved: {model_path}")

    # 绘图
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    ax1.plot(range(len(y_test)), y_test.values, label='Actual', alpha=0.7)
    ax1.plot(range(len(y_pred)), y_pred, label='Predicted', alpha=0.7)
    ax1.set_xlabel('Test samples')
    ax1.set_ylabel('Value')
    ax1.set_title(f'{model_name} - Prediction vs Actual (R2={r2:.4f})')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    residuals = y_test.values - y_pred
    ax2.hist(residuals, bins=30, edgecolor='white', alpha=0.8)
    ax2.axvline(0, color='red', linestyle='--')
    ax2.set_xlabel('Residuals')
    ax2.set_ylabel('Frequency')
    ax2.set_title(f'{model_name} - Residual Distribution')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, f"ultimate_{model_name}.png"), dpi=150)
    plt.close()

    return {
        "model_type": "Ultimate_Stacking_5Models",
        "base_models": "XGBoost+LightGBM+CatBoost+RandomForest+ExtraTrees",
        "train_size": len(X_train),
        "test_size": len(X_test),
        "feature_count": len(feature_cols),
        "metrics": {
            "RMSE": round(float(rmse), 4),
            "MAE": round(float(mae), 4),
            "MAPE": round(float(mape), 4),
            "R2": round(float(r2), 4)
        }
    }


def main():
    print("="*50)
    print("Ultimate Optimization: Target R2 > 0.9")
    print("="*50)

    # Load data
    daily_raw_df, daily_meta = load_training_dataset(mode="official")
    print(f"Raw samples: {len(daily_raw_df)}")
    daily_df = engineer_daily_features(daily_raw_df)
    print(f"After feature engineering: {len(daily_df)}")

    report = {
        "optimization": "ultimate",
        "dataset": daily_meta["training_mode"],
        "models": {}
    }

    # Train occupancy model
    report["models"]["occupancy"] = train_ultimate_model(
        daily_df, "occupancy_rate", "occupancy"
    )

    # Train revenue model
    report["models"]["revenue"] = train_ultimate_model(
        daily_df, "daily_revenue", "revenue"
    )

    # Save report
    report_path = os.path.join(OUT_DIR, "ultimate_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nReport saved: {report_path}")
    print("Ultimate optimization complete!")


if __name__ == "__main__":
    main()
