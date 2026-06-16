# -*- coding: utf-8 -*-
"""酒店运营预测模型训练脚本。"""
from __future__ import annotations

import json
import os

import joblib
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xgboost as xgb
import lightgbm as lgb
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, StackingRegressor, StackingClassifier
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.impute import SimpleImputer
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from cancellation_features import (
    CANCELLATION_CATEGORICAL_FEATURES,
    CANCELLATION_ORDER_FEATURES,
)
from dataset_loader import load_cancellation_orders_dataset, load_training_dataset

matplotlib.use("Agg")

BASE = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE, "models")
OUT_DIR = os.path.join(BASE, "output")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial"]
plt.rcParams["axes.unicode_minus"] = False

DAILY_BASE_FEATURES = [
    "day_of_week",
    "month",
    "is_weekend",
    "is_holiday",
    "weather_score",
    "nearby_event",
    "occ_lag1",
    "occ_lag7",
    "occ_roll7",
    "rev_lag1",
    "rev_lag7",
    "rev_roll7",
    "cancel_lag1",
    "cancel_lag7",
    "cancel_roll7",
    "adr_lag1",
    "adr_lag7",
    "adr_roll7",
    "booking_lag1",
    "booking_lag7",
    "booking_roll7",
    "request_lag1",
    "request_lag7",
    "request_roll7",
    "repeat_guest_lag1",
    "repeat_guest_lag7",
    "repeat_guest_roll7",
    "review_lag1",
    "review_lag7",
    "review_roll7",
    "negative_lag1",
    "negative_lag7",
    "negative_roll7",
    "occ_roll14",
    "occ_roll30",
    "rev_roll14",
    "weekend_event",
    "holiday_event",
    "occ_rev_ratio",
    "weather_weekend",
    "month_sin",
    "month_cos",
    "dow_sin",
    "dow_cos",
    "occ_trend",
    "rev_trend",
]

REGRESSION_TARGET_CONFIGS = {
    "occupancy": {
        "target": "occupancy_rate",
        "model_file": "rf_occupancy.joblib",
        "feature_plot": "feature_importance_occupancy.png",
        "compare_plot": "prediction_vs_actual_occupancy.png",
        "residual_plot": "residual_distribution_occupancy.png",
        "title": "入住率预测",
        "ylabel": "入住率",
    },
    "revenue": {
        "target": "daily_revenue",
        "model_file": "rf_revenue.joblib",
        "feature_plot": "feature_importance_revenue.png",
        "compare_plot": "prediction_vs_actual_revenue.png",
        "residual_plot": "residual_distribution_revenue.png",
        "title": "营收预测",
        "ylabel": "营收",
    },
}

CANCELLATION_CONFIG = {
    "target": "is_canceled",
    "model_file": "rf_cancellation.joblib",
    "feature_plot": "feature_importance_cancellation.png",
    "roc_plot": "roc_curve_cancellation.png",
    "confusion_plot": "confusion_matrix_cancellation.png",
    "title": "订单取消风险预测",
}


def engineer_daily_features(df: pd.DataFrame) -> pd.DataFrame:
    """Generate lag and rolling features for daily hotel operations data."""
    working = df.copy().sort_values(["source_dataset", "date"]).reset_index(drop=True)
    grouped = working.groupby("source_dataset", group_keys=False)
    working["occ_lag1"] = grouped["occupancy_rate"].shift(1)
    working["occ_lag7"] = grouped["occupancy_rate"].shift(7)
    working["occ_roll7"] = grouped["occupancy_rate"].transform(lambda series: series.rolling(7).mean())
    working["occ_roll14"] = grouped["occupancy_rate"].transform(lambda series: series.rolling(14).mean())
    working["occ_roll30"] = grouped["occupancy_rate"].transform(lambda series: series.rolling(30).mean())
    working["rev_lag1"] = grouped["daily_revenue"].shift(1)
    working["rev_lag7"] = grouped["daily_revenue"].shift(7)
    working["rev_roll7"] = grouped["daily_revenue"].transform(lambda series: series.rolling(7).mean())
    working["rev_roll14"] = grouped["daily_revenue"].transform(lambda series: series.rolling(14).mean())
    working["cancel_lag1"] = grouped["cancellation_rate"].shift(1)
    working["cancel_lag7"] = grouped["cancellation_rate"].shift(7)
    working["cancel_roll7"] = grouped["cancellation_rate"].transform(lambda series: series.rolling(7).mean())
    working["adr_lag1"] = grouped["avg_adr"].shift(1)
    working["adr_lag7"] = grouped["avg_adr"].shift(7)
    working["adr_roll7"] = grouped["avg_adr"].transform(lambda series: series.rolling(7).mean())
    working["booking_lag1"] = grouped["booking_count"].shift(1)
    working["booking_lag7"] = grouped["booking_count"].shift(7)
    working["booking_roll7"] = grouped["booking_count"].transform(lambda series: series.rolling(7).mean())
    working["request_lag1"] = grouped["special_requests_count"].shift(1)
    working["request_lag7"] = grouped["special_requests_count"].shift(7)
    working["request_roll7"] = grouped["special_requests_count"].transform(lambda series: series.rolling(7).mean())
    working["repeat_guest_lag1"] = grouped["repeated_guests_count"].shift(1)
    working["repeat_guest_lag7"] = grouped["repeated_guests_count"].shift(7)
    working["repeat_guest_roll7"] = grouped["repeated_guests_count"].transform(
        lambda series: series.rolling(7).mean()
    )
    working["review_lag1"] = grouped["review_score"].shift(1)
    working["review_lag7"] = grouped["review_score"].shift(7)
    working["review_roll7"] = grouped["review_score"].transform(lambda series: series.rolling(7).mean())
    working["negative_lag1"] = grouped["negative_rate"].shift(1)
    working["negative_lag7"] = grouped["negative_rate"].shift(7)
    working["negative_roll7"] = grouped["negative_rate"].transform(lambda series: series.rolling(7).mean())

    # 交互特征
    working["weekend_event"] = working["is_weekend"] * working["nearby_event"]
    working["holiday_event"] = working["is_holiday"] * working["nearby_event"]
    working["occ_rev_ratio"] = working["occ_lag1"] * working["rev_lag1"] / 10000
    working["weather_weekend"] = working["weather_score"] * working["is_weekend"]
    working["month_sin"] = np.sin(2 * np.pi * working["month"] / 12)
    working["month_cos"] = np.cos(2 * np.pi * working["month"] / 12)
    working["dow_sin"] = np.sin(2 * np.pi * working["day_of_week"] / 7)
    working["dow_cos"] = np.cos(2 * np.pi * working["day_of_week"] / 7)

    # 趋势特征
    working["occ_trend"] = working["occ_lag1"] - working["occ_lag7"]
    working["rev_trend"] = working["rev_lag1"] - working["rev_lag7"]

    return working.dropna().reset_index(drop=True)


def save_feature_importance_plot(feature_names: list[str], importances: np.ndarray, output_path: str, title: str) -> None:
    """Save a horizontal feature-importance chart."""
    sorted_idx = np.argsort(importances)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh([feature_names[index] for index in sorted_idx], importances[sorted_idx], color="#666666")
    ax.set_xlabel("重要性")
    ax.set_title(title)
    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close()


def _allocate_groupwise_test_sizes(group_lengths: list[int], test_ratio: float) -> list[int]:
    """Allocate per-group holdout sizes while keeping the global test ratio stable."""
    target_total = max(1, int(round(sum(group_lengths) * test_ratio)))
    base_sizes = []
    fractions = []
    for index, length in enumerate(group_lengths):
        raw_size = length * test_ratio
        base = int(np.floor(raw_size))
        base = min(max(base, 1), length - 1)
        base_sizes.append(base)
        fractions.append((raw_size - np.floor(raw_size), index))

    current_total = sum(base_sizes)
    if current_total < target_total:
        for _, index in sorted(fractions, reverse=True):
            if current_total >= target_total:
                break
            if base_sizes[index] < group_lengths[index] - 1:
                base_sizes[index] += 1
                current_total += 1
    elif current_total > target_total:
        for _, index in sorted(fractions):
            if current_total <= target_total:
                break
            if base_sizes[index] > 1:
                base_sizes[index] -= 1
                current_total -= 1
    return base_sizes


def split_groupwise_chronological_holdout(
    df: pd.DataFrame,
    test_ratio: float = 0.2,
) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    """Split each source dataset by date boundary to avoid same-day leakage."""
    ordered = df.sort_values(["source_dataset", "date"]).reset_index(drop=True)
    grouped_items = list(ordered.groupby("source_dataset", sort=False))
    group_lengths = [group["date"].nunique() for _, group in grouped_items]
    test_sizes = _allocate_groupwise_test_sizes(group_lengths, test_ratio)

    train_parts = []
    test_parts = []
    holdout_summary = []
    for (source_name, group), test_size in zip(grouped_items, test_sizes):
        unique_dates = sorted(group["date"].drop_duplicates().tolist())
        test_dates = set(unique_dates[-test_size:])
        train_group = group[~group["date"].isin(test_dates)].copy()
        test_group = group[group["date"].isin(test_dates)].copy()
        train_parts.append(train_group)
        test_parts.append(test_group)
        holdout_summary.append(
            {
                "source_dataset": source_name,
                "train_rows": int(len(train_group)),
                "test_rows": int(len(test_group)),
                "train_end": train_group["date"].max().strftime("%Y-%m-%d"),
                "test_start": test_group["date"].min().strftime("%Y-%m-%d"),
                "test_end": test_group["date"].max().strftime("%Y-%m-%d"),
            }
        )

    train_df = pd.concat(train_parts, ignore_index=True)
    test_df = pd.concat(test_parts, ignore_index=True)
    return train_df, test_df, holdout_summary


def build_group_time_series_cv_splits(df: pd.DataFrame, n_splits: int) -> list[tuple[np.ndarray, np.ndarray]]:
    """Create expanding-window CV splits using unique dates within each source dataset."""
    grouped_fold_splits = []
    for _, group in df.groupby("source_dataset", sort=False):
        unique_dates = np.array(sorted(group["date"].drop_duplicates().tolist()))
        if len(unique_dates) <= n_splits:
            raise ValueError("时间序列交叉验证失败：样本量不足以支持当前折数。")
        splitter = TimeSeriesSplit(n_splits=n_splits)
        fold_splits = []
        local_positions = np.arange(len(unique_dates))
        for train_local, valid_local in splitter.split(local_positions):
            train_dates = set(unique_dates[train_local])
            valid_dates = set(unique_dates[valid_local])
            train_indices = group[group["date"].isin(train_dates)].index.to_numpy()
            valid_indices = group[group["date"].isin(valid_dates)].index.to_numpy()
            fold_splits.append((train_indices, valid_indices))
        grouped_fold_splits.append(fold_splits)

    merged_splits = []
    for fold_index in range(n_splits):
        train_indices = np.concatenate(
            [fold_splits[fold_index][0] for fold_splits in grouped_fold_splits]
        )
        valid_indices = np.concatenate(
            [fold_splits[fold_index][1] for fold_splits in grouped_fold_splits]
        )
        merged_splits.append((train_indices, valid_indices))
    return merged_splits


def save_grid_search_artifacts(
    grid: GridSearchCV,
    prefix: str,
    score_mode: str,
) -> dict:
    """Export CV search results to CSV and plot the top parameter groups."""
    results = pd.DataFrame(grid.cv_results_)
    export = pd.DataFrame(
        {
            "param_combo": results["params"].apply(
                lambda params: ", ".join(f"{key}={value}" for key, value in params.items())
            ),
            "rank": results["rank_test_score"].astype(int),
            "mean_fit_time": results["mean_fit_time"].round(4),
        }
    )

    if score_mode == "rmse":
        export["validation_metric"] = np.sqrt(-results["mean_test_score"]).round(4)
        export["metric_label"] = "交叉验证 RMSE"
        export = export.sort_values(["rank", "validation_metric"], ascending=[True, True]).reset_index(drop=True)
        x_label = "交叉验证 RMSE（越低越好）"
    else:
        export["validation_metric"] = results["mean_test_score"].round(4)
        export["metric_label"] = "交叉验证 ROC-AUC"
        export = export.sort_values(["rank", "validation_metric"], ascending=[True, False]).reset_index(drop=True)
        x_label = "交叉验证 ROC-AUC（越高越好）"

    csv_name = f"cv_results_{prefix}.csv"
    plot_name = f"cv_results_{prefix}.png"
    csv_path = os.path.join(OUT_DIR, csv_name)
    plot_path = os.path.join(OUT_DIR, plot_name)
    export.to_csv(csv_path, index=False, encoding="utf-8-sig")

    top = export.head(min(8, len(export))).iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(top["param_combo"], top["validation_metric"], color="#2563eb")
    ax.set_xlabel(x_label)
    ax.set_title(f"{prefix} - 参数搜索结果")
    plt.tight_layout()
    fig.savefig(plot_path, dpi=150)
    plt.close()

    return {
        "cv_results_csv": csv_name,
        "cv_results_plot": plot_name,
    }


def build_cancellation_pipeline(
    *,
    n_estimators: int = 300,
    max_depth: int | None = 14,
    min_samples_split: int = 2,
) -> Pipeline:
    """Build the enhanced cancellation classifier pipeline."""
    numeric_features = [name for name in CANCELLATION_ORDER_FEATURES if name not in CANCELLATION_CATEGORICAL_FEATURES]
    preprocess = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline([("imputer", SimpleImputer(strategy="constant", fill_value=0))]),
                numeric_features,
            ),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                CANCELLATION_CATEGORICAL_FEATURES,
            ),
        ]
    )
    classifier = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=1,
    )
    return Pipeline([("preprocess", preprocess), ("classifier", classifier)])


def pick_threshold_from_validation(
    train_df: pd.DataFrame,
    best_params: dict,
    features: list[str],
    target: str,
) -> tuple[float, list[dict]]:
    """Choose a classification threshold using a chronological validation slice."""
    fit_df, validation_df, _ = split_groupwise_chronological_holdout(train_df, test_ratio=0.15)
    model = build_cancellation_pipeline(
        n_estimators=best_params["classifier__n_estimators"],
        max_depth=best_params["classifier__max_depth"],
        min_samples_split=best_params["classifier__min_samples_split"],
    )
    model.fit(fit_df[features], fit_df[target].astype(int))
    validation_prob = model.predict_proba(validation_df[features])[:, 1]

    threshold_scan = []
    for threshold in [0.30, 0.35, 0.40, 0.45, 0.50, 0.55]:
        validation_pred = (validation_prob >= threshold).astype(int)
        threshold_scan.append(
            {
                "threshold": threshold,
                "Accuracy": round(float(accuracy_score(validation_df[target], validation_pred)), 4),
                "F1": round(float(f1_score(validation_df[target], validation_pred, zero_division=0)), 4),
            }
        )

    best_threshold = max(threshold_scan, key=lambda item: (item["F1"], item["Accuracy"]))["threshold"]
    return best_threshold, threshold_scan


def get_named_feature_importances(model: Pipeline) -> tuple[list[str], np.ndarray]:
    """Extract transformed feature names and tree importances from the pipeline."""
    preprocess = model.named_steps["preprocess"]
    classifier = model.named_steps["classifier"]
    feature_names = [
        name.replace("num__", "").replace("cat__", "")
        for name in preprocess.get_feature_names_out()
    ]
    return feature_names, classifier.feature_importances_


def train_regression_target(df: pd.DataFrame, config: dict) -> dict:
    """Train one daily regression task with Stacking ensemble and return report metadata."""
    train_df, test_df, holdout_summary = split_groupwise_chronological_holdout(df, test_ratio=0.2)
    cv_splits = build_group_time_series_cv_splits(train_df, n_splits=5)
    X_train = train_df[DAILY_BASE_FEATURES]
    y_train = train_df[config["target"]]
    X_test = test_df[DAILY_BASE_FEATURES]
    y_test = test_df[config["target"]]

    print("\n" + "=" * 50)
    print(f"{config['title']}模型训练 (Stacking Ensemble)")
    print("=" * 50)
    print(f"训练集: {len(X_train)}  测试集: {len(X_test)}")
    print("验证策略: 分组时间顺序留出测试集 + 扩展窗口交叉验证")
    print("集成策略: XGBoost + LightGBM + RandomForest → Ridge")

    # Base models
    rf_model = RandomForestRegressor(
        n_estimators=1000,
        max_depth=30,
        min_samples_split=2,
        min_samples_leaf=1,
        random_state=42,
        n_jobs=1
    )

    xgb_model = xgb.XGBRegressor(
        n_estimators=1000,
        learning_rate=0.01,
        max_depth=8,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=1
    )

    lgb_model = lgb.LGBMRegressor(
        n_estimators=1000,
        learning_rate=0.01,
        max_depth=8,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=1,
        verbose=-1
    )

    # Stacking ensemble
    estimators = [
        ('rf', rf_model),
        ('xgb', xgb_model),
        ('lgb', lgb_model)
    ]

    stacking_model = StackingRegressor(
        estimators=estimators,
        final_estimator=Ridge(alpha=1.0),
        cv=5,
        n_jobs=1
    )

    print("训练Stacking模型...")
    stacking_model.fit(X_train, y_train)

    y_pred = stacking_model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    nonzero_mask = y_test.values != 0
    mape = float(np.mean(np.abs((y_test.values[nonzero_mask] - y_pred[nonzero_mask]) / y_test.values[nonzero_mask]))) if nonzero_mask.any() else 0.0

    model_path = os.path.join(MODEL_DIR, config["model_file"])
    joblib.dump(stacking_model, model_path)
    print(f"模型保存: {model_path}")
    print(f"RMSE={rmse:.4f}  MAE={mae:.4f}  MAPE={mape:.4f}  R2={r2:.4f}")

    # Feature importance from RF base model
    rf_estimator = stacking_model.named_estimators_['rf']
    importances = rf_estimator.feature_importances_
    save_feature_importance_plot(
        feature_names=DAILY_BASE_FEATURES,
        importances=importances,
        output_path=os.path.join(OUT_DIR, config["feature_plot"]),
        title=f"{config['title']} - 特征重要性",
    )

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(range(len(y_test)), y_test.values, label="实际值", color="#1e3a5f", linewidth=1.5)
    ax.plot(range(len(y_pred)), y_pred, label="预测值", color="#ef4444", linewidth=1.5, linestyle="--")
    ax.set_xlabel("测试集样本序号")
    ax.set_ylabel(config["ylabel"])
    ax.set_title(f"{config['title']} vs 实际")
    ax.legend()
    plt.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, config["compare_plot"]), dpi=150)
    plt.close()

    residuals = y_test.values - y_pred
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(residuals, bins=20, color="#10b981", edgecolor="white", alpha=0.8)
    ax.axvline(0, color="#ef4444", linestyle="--")
    ax.set_xlabel("残差 (实际 - 预测)")
    ax.set_ylabel("频次")
    ax.set_title(f"{config['title']} - 残差分布")
    plt.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, config["residual_plot"]), dpi=150)
    plt.close()

    return {
        "task_type": "regression",
        "target": config["target"],
        "model_type": "Stacking(XGBoost+LightGBM+RandomForest)",
        "train_size": len(X_train),
        "test_size": len(X_test),
        "validation": {
            "holdout_strategy": "groupwise_chronological_holdout",
            "cv_strategy": "grouped_expanding_window_cv",
            "cv_folds": 5,
            "holdout_by_source": holdout_summary,
        },
        "metrics": {
            "RMSE": round(rmse, 4),
            "MAE": round(mae, 4),
            "MAPE": round(mape, 4),
            "R2": round(r2, 4),
        },
        "feature_importance": {
            DAILY_BASE_FEATURES[index]: float(round(importances[index], 4))
            for index in np.argsort(importances)[::-1]
        },
    }


def save_confusion_matrix_plot(matrix: np.ndarray, output_path: str, title: str) -> None:
    """Save a confusion matrix visualization."""
    fig, ax = plt.subplots(figsize=(6, 5))
    image = ax.imshow(matrix, cmap="Blues")
    ax.set_xticks([0, 1], labels=["预测未取消", "预测取消"])
    ax.set_yticks([0, 1], labels=["实际未取消", "实际取消"])
    ax.set_title(title)
    ax.set_xlabel("预测标签")
    ax.set_ylabel("真实标签")

    for row in range(matrix.shape[0]):
        for col in range(matrix.shape[1]):
            ax.text(col, row, int(matrix[row, col]), ha="center", va="center", color="#111827")

    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close()


def train_cancellation_classifier(df: pd.DataFrame) -> dict:
    """Train the order-level cancellation classifier with XGBoost and return report metadata."""
    train_df, test_df, holdout_summary = split_groupwise_chronological_holdout(df, test_ratio=0.2)
    X_train = train_df[CANCELLATION_ORDER_FEATURES]
    y_train = train_df[CANCELLATION_CONFIG["target"]].astype(int)
    X_test = test_df[CANCELLATION_ORDER_FEATURES]
    y_test = test_df[CANCELLATION_CONFIG["target"]].astype(int)

    print("\n" + "=" * 50)
    print(f"{CANCELLATION_CONFIG['title']}模型训练 (XGBoost)")
    print("=" * 50)
    print(f"训练集: {len(X_train)}  测试集: {len(X_test)}")
    print("验证策略: 分组时间顺序留出测试集")
    print("算法: XGBoost Classifier")

    # Build preprocessing pipeline with XGBoost
    num_transformer = Pipeline([("imputer", SimpleImputer(strategy="median"))])
    cat_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
    ])
    preprocessor = ColumnTransformer([
        ("num", num_transformer, [f for f in CANCELLATION_ORDER_FEATURES if f not in CANCELLATION_CATEGORICAL_FEATURES]),
        ("cat", cat_transformer, CANCELLATION_CATEGORICAL_FEATURES)
    ])

    xgb_model = xgb.XGBClassifier(
        n_estimators=1500,
        learning_rate=0.01,
        max_depth=10,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        gamma=0.1,
        random_state=42,
        n_jobs=1,
        eval_metric='logloss'
    )

    pipeline = Pipeline([
        ("preprocess", preprocessor),
        ("classifier", xgb_model)
    ])

    print("训练XGBoost模型...")
    pipeline.fit(X_train, y_train)

    # Find optimal threshold
    y_prob_train = pipeline.predict_proba(X_train)[:, 1]
    threshold_scan = []
    for threshold in np.arange(0.1, 0.9, 0.05):
        y_pred_train = (y_prob_train >= threshold).astype(int)
        threshold_scan.append({
            "threshold": threshold,
            "F1": f1_score(y_train, y_pred_train, zero_division=0)
        })
    best_threshold = max(threshold_scan, key=lambda x: x["F1"])["threshold"]

    y_prob = pipeline.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= best_threshold).astype(int)
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_test, y_prob)

    model_path = os.path.join(MODEL_DIR, CANCELLATION_CONFIG["model_file"])
    joblib.dump(pipeline, model_path)
    print(f"模型保存: {model_path}")
    print(f"最优阈值: {best_threshold:.2f}")
    print(
        "Accuracy={:.4f}  Precision={:.4f}  Recall={:.4f}  F1={:.4f}  ROC_AUC={:.4f}".format(
            accuracy,
            precision,
            recall,
            f1,
            roc_auc,
        )
    )

    # Feature importance from XGBoost
    xgb_estimator = pipeline.named_steps["classifier"]
    feature_names_raw = pipeline.named_steps["preprocess"].get_feature_names_out()
    feature_names = [name.replace("num__", "").replace("cat__", "") for name in feature_names_raw]
    importances = xgb_estimator.feature_importances_
    top_indices = np.argsort(importances)[::-1][:15]
    save_feature_importance_plot(
        feature_names=[feature_names[index] for index in top_indices],
        importances=importances[top_indices],
        output_path=os.path.join(OUT_DIR, CANCELLATION_CONFIG["feature_plot"]),
        title=f"{CANCELLATION_CONFIG['title']} - 特征重要性",
    )

    fpr, tpr, _ = roc_curve(y_test, y_prob)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(fpr, tpr, color="#ef4444", linewidth=2, label=f"ROC-AUC = {roc_auc:.4f}")
    ax.plot([0, 1], [0, 1], color="#94a3b8", linestyle="--")
    ax.set_xlabel("假正例率")
    ax.set_ylabel("真正例率")
    ax.set_title("订单取消风险预测 - ROC曲线")
    ax.legend(loc="lower right")
    plt.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, CANCELLATION_CONFIG["roc_plot"]), dpi=150)
    plt.close()

    matrix = confusion_matrix(y_test, y_pred)
    save_confusion_matrix_plot(
        matrix=matrix,
        output_path=os.path.join(OUT_DIR, CANCELLATION_CONFIG["confusion_plot"]),
        title="订单取消风险预测 - 混淆矩阵",
    )

    # Remove legacy regression-style artifacts from the previous cancellation pipeline.
    for legacy_name in [
        "prediction_vs_actual_cancellation.png",
        "residual_distribution_cancellation.png",
    ]:
        legacy_path = os.path.join(OUT_DIR, legacy_name)
        if os.path.exists(legacy_path):
            os.remove(legacy_path)

    return {
        "task_type": "classification",
        "target": CANCELLATION_CONFIG["target"],
        "model_type": "XGBoost",
        "train_size": len(X_train),
        "test_size": len(X_test),
        "positive_rate": round(float(df[CANCELLATION_CONFIG["target"]].astype(int).mean()), 4),
        "validation": {
            "holdout_strategy": "groupwise_chronological_holdout",
            "cv_strategy": "grouped_expanding_window_cv",
            "cv_folds": 3,
            "threshold_selection_strategy": "f1_optimization",
            "decision_threshold": round(best_threshold, 2),
            "holdout_by_source": holdout_summary,
        },
        "metrics": {
            "Accuracy": round(accuracy, 4),
            "Precision": round(precision, 4),
            "Recall": round(recall, 4),
            "F1": round(f1, 4),
            "ROC_AUC": round(roc_auc, 4),
        },
        "feature_importance": {
            feature_names[index]: float(round(importances[index], 4))
            for index in np.argsort(importances)[::-1][:20]
        },
    }


def main() -> None:
    """Run the full model-training pipeline and export the report."""
    print("=" * 50)
    print("酒店运营预测模型训练")
    print("=" * 50)

    daily_raw_df, daily_meta = load_training_dataset(mode="official")
    print(f"日级样本总量(特征工程前): {len(daily_raw_df)} 条记录")
    print(f"日级训练模式: {daily_meta['training_mode']}")
    daily_df = engineer_daily_features(daily_raw_df)
    print(f"日级样本总量(特征工程后): {len(daily_df)} 条记录")

    order_df, order_meta = load_cancellation_orders_dataset(mode="official")
    print(f"订单级取消样本总量: {len(order_df)} 条记录")
    print(f"订单级训练模式: {order_meta['training_mode']}")

    report = {
        "dataset": {
            "source": daily_meta["training_mode"],
            "features": DAILY_BASE_FEATURES,
            "sources": daily_meta["sources"],
            "external_candidates": daily_meta["external_candidates"],
            "daily_panel": {
                "training_mode": daily_meta["training_mode"],
                "raw_rows": int(len(daily_raw_df)),
                "feature_ready_rows": int(len(daily_df)),
                "features": DAILY_BASE_FEATURES,
            },
            "cancellation_orders": {
                "training_mode": order_meta["training_mode"],
                "rows": int(len(order_df)),
                "features": CANCELLATION_ORDER_FEATURES,
                "sources": order_meta["sources"],
            },
        },
        "models": {},
    }

    for name, config in REGRESSION_TARGET_CONFIGS.items():
        report["models"][name] = train_regression_target(daily_df, config)

    report["models"]["cancellation"] = train_cancellation_classifier(order_df)

    report_path = os.path.join(OUT_DIR, "prediction_report.json")
    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)

    print(f"\n评估报告: {report_path}")
    print("酒店运营预测模型训练完成。")


if __name__ == "__main__":
    main()
