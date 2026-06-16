# -*- coding: utf-8 -*-
"""酒店运营数据 EDA 脚本。"""
import json
import os

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from dataset_loader import load_training_dataset

matplotlib.use("Agg")

BASE = os.path.dirname(__file__)
OUT_DIR = os.path.join(BASE, "output")
os.makedirs(OUT_DIR, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial"]
plt.rcParams["axes.unicode_minus"] = False

print("=" * 60)
print("酒店运营数据 EDA")
print("=" * 60)

df, dataset_meta = load_training_dataset(mode="official")
print(f"数据量: {len(df)} 条日级样本")
plot_df = df.groupby("date", as_index=False).agg(
    occupancy_rate=("occupancy_rate", "mean"),
    daily_revenue=("daily_revenue", "sum"),
    review_score=("review_score", "mean"),
    negative_rate=("negative_rate", "mean"),
)
plot_df["date"] = pd.to_datetime(plot_df["date"])
df["date"] = pd.to_datetime(df["date"])

fig, axes = plt.subplots(2, 2, figsize=(14, 9))
axes[0, 0].plot(plot_df["date"], plot_df["occupancy_rate"], color="#3b82f6")
axes[0, 0].set_title("入住率时序变化")
axes[0, 1].plot(plot_df["date"], plot_df["daily_revenue"], color="#10b981")
axes[0, 1].set_title("营收时序变化")
axes[1, 0].plot(plot_df["date"], plot_df["review_score"], color="#f59e0b")
axes[1, 0].set_title("评分时序变化")
axes[1, 1].plot(plot_df["date"], plot_df["negative_rate"], color="#ef4444")
axes[1, 1].set_title("差评率时序变化")
for ax in axes.flat:
    ax.tick_params(axis="x", rotation=30)
plt.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "eda_ops_timeseries.png"), dpi=150)
plt.close()

corr_cols = [
    "day_of_week",
    "month",
    "is_weekend",
    "is_holiday",
    "weather_score",
    "nearby_event",
    "occupancy_rate",
    "daily_revenue",
    "review_score",
    "negative_rate",
]
fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(df[corr_cols].corr(), annot=True, cmap="Blues", fmt=".2f", ax=ax)
ax.set_title("运营指标相关性热力图")
plt.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "eda_correlation_heatmap.png"), dpi=150)
plt.close()

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
sns.boxplot(data=df, x="day_of_week", y="occupancy_rate", ax=axes[0], color="#93c5fd")
axes[0].set_title("入住率按星期分布")
sns.boxplot(data=df, x="month", y="daily_revenue", ax=axes[1], color="#86efac")
axes[1].set_title("营收按月份分布")
plt.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "eda_occupancy_patterns.png"), dpi=150)
plt.close()

report = {
    "dataset": {
        "name": dataset_meta["training_mode"],
        "date_range": [df["date"].min().strftime("%Y-%m-%d"), df["date"].max().strftime("%Y-%m-%d")],
        "sources": dataset_meta["sources"],
        "external_candidates": dataset_meta["external_candidates"],
    },
    "summary": {
        "occupancy_mean": round(float(df["occupancy_rate"].mean()), 4),
        "revenue_mean": round(float(df["daily_revenue"].mean()), 2),
        "review_score_mean": round(float(df["review_score"].mean()), 4),
        "negative_rate_mean": round(float(df["negative_rate"].mean()), 4),
    },
}

report_path = os.path.join(OUT_DIR, "eda_report.json")
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"EDA 报告: {report_path}")
print("运营数据 EDA 完成。")
