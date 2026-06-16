# -*- coding: utf-8 -*-
"""LSTM深度学习模型训练脚本"""
import os
import json
import numpy as np
import pandas as pd
import joblib
import matplotlib
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, callbacks

from dataset_loader import load_training_dataset
from train_prediction import engineer_daily_features, DAILY_BASE_FEATURES

matplotlib.use("Agg")
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial"]
plt.rcParams["axes.unicode_minus"] = False

BASE = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE, "models")
OUT_DIR = os.path.join(BASE, "output")

# 设置随机种子
np.random.seed(42)
tf.random.set_seed(42)


def create_sequences(data, target, lookback=14):
    """将时序数据转换为LSTM输入格式 (samples, timesteps, features)"""
    X, y = [], []
    for i in range(lookback, len(data)):
        X.append(data[i-lookback:i])
        y.append(target[i])
    return np.array(X), np.array(y)


def build_lstm_model(input_shape, model_name="occupancy"):
    """构建LSTM模型"""
    model = keras.Sequential([
        layers.LSTM(128, return_sequences=True, input_shape=input_shape),
        layers.Dropout(0.3),
        layers.LSTM(64),
        layers.Dropout(0.3),
        layers.Dense(32, activation='relu'),
        layers.Dense(1)
    ], name=f"lstm_{model_name}")

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss='mse',
        metrics=['mae']
    )
    return model


def train_lstm_target(df, target_col, model_name, lookback=14):
    """训练单个LSTM模型"""
    print(f"\n{'='*50}")
    print(f"{model_name} LSTM模型训练")
    print(f"{'='*50}")

    # 按日期排序，确保时序连续性
    df_sorted = df.sort_values('date').reset_index(drop=True)

    # 特征和目标
    feature_cols = DAILY_BASE_FEATURES
    X_raw = df_sorted[feature_cols].values
    y_raw = df_sorted[target_col].values

    # 标准化
    scaler_X = StandardScaler()
    scaler_y = StandardScaler()
    X_scaled = scaler_X.fit_transform(X_raw)
    y_scaled = scaler_y.fit_transform(y_raw.reshape(-1, 1)).flatten()

    # 创建时序序列
    X_seq, y_seq = create_sequences(X_scaled, y_scaled, lookback=lookback)

    # 划分训练集和测试集（时序划分，最后20%作为测试集）
    split_idx = int(len(X_seq) * 0.8)
    X_train, X_test = X_seq[:split_idx], X_seq[split_idx:]
    y_train, y_test = y_seq[:split_idx], y_seq[split_idx:]

    print(f"训练集: {len(X_train)}  测试集: {len(X_test)}")
    print(f"输入形状: {X_train.shape}")

    # 构建模型
    model = build_lstm_model((lookback, len(feature_cols)), model_name)

    # 回调函数
    early_stop = callbacks.EarlyStopping(
        monitor='val_loss',
        patience=20,
        restore_best_weights=True
    )

    reduce_lr = callbacks.ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=10,
        min_lr=1e-6
    )

    # 训练
    print("开始训练LSTM...")
    history = model.fit(
        X_train, y_train,
        validation_split=0.2,
        epochs=200,
        batch_size=32,
        callbacks=[early_stop, reduce_lr],
        verbose=1
    )

    # 预测
    y_pred_scaled = model.predict(X_test).flatten()
    y_pred = scaler_y.inverse_transform(y_pred_scaled.reshape(-1, 1)).flatten()
    y_test_original = scaler_y.inverse_transform(y_test.reshape(-1, 1)).flatten()

    # 评估
    rmse = np.sqrt(mean_squared_error(y_test_original, y_pred))
    mae = mean_absolute_error(y_test_original, y_pred)
    r2 = r2_score(y_test_original, y_pred)
    nonzero_mask = y_test_original != 0
    mape = float(np.mean(np.abs((y_test_original[nonzero_mask] - y_pred[nonzero_mask]) / y_test_original[nonzero_mask]))) if nonzero_mask.any() else 0.0

    print(f"RMSE={rmse:.4f}  MAE={mae:.4f}  MAPE={mape:.4f}  R2={r2:.4f}")

    # 保存模型和scaler
    model_path = os.path.join(MODEL_DIR, f"lstm_{model_name}.h5")
    model.save(model_path)
    joblib.dump(scaler_X, os.path.join(MODEL_DIR, f"lstm_{model_name}_scaler_X.joblib"))
    joblib.dump(scaler_y, os.path.join(MODEL_DIR, f"lstm_{model_name}_scaler_y.joblib"))
    print(f"模型保存: {model_path}")

    # 绘制训练曲线
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    ax1.plot(history.history['loss'], label='训练损失')
    ax1.plot(history.history['val_loss'], label='验证损失')
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Loss (MSE)')
    ax1.set_title(f'{model_name} - 训练曲线')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2.plot(range(len(y_test_original)), y_test_original, label='实际值', alpha=0.7)
    ax2.plot(range(len(y_pred)), y_pred, label='预测值', alpha=0.7)
    ax2.set_xlabel('测试集样本')
    ax2.set_ylabel('值')
    ax2.set_title(f'{model_name} - 预测对比')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, f"lstm_{model_name}_training.png"), dpi=150)
    plt.close()

    return {
        "model_type": "LSTM",
        "lookback": lookback,
        "train_size": len(X_train),
        "test_size": len(X_test),
        "epochs_trained": len(history.history['loss']),
        "metrics": {
            "RMSE": round(float(rmse), 4),
            "MAE": round(float(mae), 4),
            "MAPE": round(float(mape), 4),
            "R2": round(float(r2), 4)
        }
    }


def main():
    print("="*50)
    print("LSTM深度学习模型训练")
    print("="*50)

    # 加载数据
    daily_raw_df, daily_meta = load_training_dataset(mode="official")
    print(f"日级样本总量: {len(daily_raw_df)} 条记录")
    daily_df = engineer_daily_features(daily_raw_df)
    print(f"特征工程后: {len(daily_df)} 条记录")

    report = {
        "model_family": "LSTM",
        "dataset": daily_meta["training_mode"],
        "models": {}
    }

    # 训练入住率模型
    report["models"]["occupancy"] = train_lstm_target(
        daily_df, "occupancy_rate", "occupancy", lookback=14
    )

    # 训练营收模型
    report["models"]["revenue"] = train_lstm_target(
        daily_df, "daily_revenue", "revenue", lookback=14
    )

    # 保存报告
    report_path = os.path.join(OUT_DIR, "lstm_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n报告保存: {report_path}")
    print("LSTM模型训练完成。")


if __name__ == "__main__":
    main()
