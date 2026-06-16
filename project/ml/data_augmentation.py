# -*- coding: utf-8 -*-
"""运营数据准备脚本。

保留 1095 条本地原型数据，作为公开数据集缺失时的演示回退样本。
"""
import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

np.random.seed(42)

BASE = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE, "data")
os.makedirs(DATA_DIR, exist_ok=True)

print("=" * 60)
print("本地原型运营数据生成")
print("=" * 60)

season_base = {
    1: 0.58, 2: 0.62, 3: 0.68, 4: 0.74, 5: 0.80, 6: 0.78,
    7: 0.85, 8: 0.83, 9: 0.75, 10: 0.82, 11: 0.65, 12: 0.60,
}
holidays = {
    (1, 1), (2, 1), (2, 2), (2, 3), (2, 4), (2, 5), (2, 6), (2, 7),
    (4, 4), (4, 5), (4, 6), (5, 1), (5, 2), (5, 3), (5, 4), (5, 5),
    (6, 1), (6, 2), (9, 15), (9, 16), (9, 17),
    (10, 1), (10, 2), (10, 3), (10, 4), (10, 5), (10, 6), (10, 7),
}

start_date = datetime(2023, 1, 1)
rows = []

for index in range(1095):
    date_value = start_date + timedelta(days=index)
    day_of_week = date_value.weekday()
    month = date_value.month
    is_weekend = 1 if day_of_week >= 5 else 0
    is_holiday = 1 if (month, date_value.day) in holidays else 0
    weather_score = np.random.choice([1, 2, 3, 4, 5], p=[0.05, 0.12, 0.33, 0.35, 0.15])
    nearby_event = np.random.binomial(1, 0.12)
    prev_occ = rows[-1]["occupancy_rate"] if rows else 0.70

    year_factor = (date_value.year - 2023) * 0.02
    occupancy = (
        season_base[month]
        + year_factor
        + is_weekend * 0.07
        + is_holiday * 0.10
        + nearby_event * 0.06
        + (weather_score - 3) * 0.015
        + (prev_occ - 0.70) * 0.15
        + np.random.normal(0, 0.025)
    )
    occupancy = np.clip(occupancy, 0.30, 0.98)

    rooms = 120
    base_price = 260 + is_weekend * 60 + is_holiday * 100 + nearby_event * 40
    revenue = int(rooms * occupancy * base_price * (1 + np.random.normal(0, 0.04)))

    review_score = 4.15 + occupancy * 0.35 - (weather_score < 3) * 0.1 + np.random.normal(0, 0.12)
    review_score = round(np.clip(review_score, 3.2, 5.0), 2)

    negative_rate = 0.10 - occupancy * 0.04 + (weather_score < 3) * 0.02 + np.random.normal(0, 0.015)
    negative_rate = round(np.clip(negative_rate, 0.01, 0.18), 4)

    rows.append({
        "date": date_value.strftime("%Y-%m-%d"),
        "day_of_week": day_of_week,
        "month": month,
        "is_weekend": is_weekend,
        "is_holiday": is_holiday,
        "weather_score": weather_score,
        "nearby_event": nearby_event,
        "occupancy_rate": round(occupancy, 4),
        "daily_revenue": revenue,
        "review_score": review_score,
        "negative_rate": negative_rate,
    })

df = pd.DataFrame(rows)
output_path = os.path.join(DATA_DIR, "hotel_ops_1095.csv")
df.to_csv(output_path, index=False, encoding="utf-8-sig")

print(f"已生成运营数据: {output_path}")
print(df[["occupancy_rate", "daily_revenue", "review_score", "negative_rate"]].describe().round(4))
print("\n本地原型数据准备完成。")
