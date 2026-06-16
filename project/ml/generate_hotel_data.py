# -*- coding: utf-8 -*-
"""酒店运营数据生成脚本
生成365天模拟运营数据 + 2000条酒店评论数据
用于入住率预测模型和情感分类模型训练
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os, random

np.random.seed(42)
random.seed(42)
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# ========== 1. 运营数据 ==========
print("=" * 50)
print("生成酒店运营数据（365天）...")
start_date = datetime(2025, 1, 1)
dates = [start_date + timedelta(days=i) for i in range(365)]

season_base = {1:0.58, 2:0.62, 3:0.68, 4:0.74, 5:0.80, 6:0.78,
               7:0.85, 8:0.83, 9:0.75, 10:0.82, 11:0.65, 12:0.60}

holidays = {(1,1),(2,1),(2,2),(2,3),(2,4),(2,5),(2,6),(2,7),
            (4,4),(4,5),(4,6),(5,1),(5,2),(5,3),(5,4),(5,5),
            (6,1),(6,2),(9,15),(9,16),(9,17),
            (10,1),(10,2),(10,3),(10,4),(10,5),(10,6),(10,7)}

rows = []
for d in dates:
    dow = d.weekday()
    mon = d.month
    is_wknd = 1 if dow >= 5 else 0
    is_hol = 1 if (mon, d.day) in holidays else 0
    weather = np.random.choice([1,2,3,4,5], p=[0.05,0.12,0.33,0.35,0.15])
    event = np.random.binomial(1, 0.12)
    prev_occ = rows[-1]["occupancy_rate"] if rows else 0.70

    occ = (season_base[mon]
           + is_wknd * 0.07
           + is_hol * 0.10
           + event * 0.06
           + (weather - 3) * 0.015
           + (prev_occ - 0.70) * 0.15
           + np.random.normal(0, 0.025))
    occ = np.clip(occ, 0.30, 0.98)

    rooms = 120
    base_price = 260 + is_wknd * 60 + is_hol * 100 + event * 40
    revenue = int(rooms * occ * base_price * (1 + np.random.normal(0, 0.04)))

    score = 4.15 + occ * 0.35 - (weather < 3) * 0.1 + np.random.normal(0, 0.12)
    score = round(np.clip(score, 3.2, 5.0), 2)

    neg = 0.10 - occ * 0.04 + (weather < 3) * 0.02 + np.random.normal(0, 0.015)
    neg = round(np.clip(neg, 0.01, 0.18), 4)

    rows.append({"date": d.strftime("%Y-%m-%d"), "day_of_week": dow, "month": mon,
                 "is_weekend": is_wknd, "is_holiday": is_hol, "weather_score": weather,
                 "nearby_event": event, "occupancy_rate": round(occ, 4),
                 "daily_revenue": revenue, "review_score": score, "negative_rate": neg})

df_ops = pd.DataFrame(rows)
ops_path = os.path.join(DATA_DIR, "hotel_ops_365.csv")
df_ops.to_csv(ops_path, index=False, encoding="utf-8-sig")
print(f"  保存: {ops_path}  ({len(df_ops)} 条)")
print(df_ops[["occupancy_rate","daily_revenue","review_score","negative_rate"]].describe().round(4))

# ========== 2. 酒店评论数据 ==========
print("\n" + "=" * 50)
print("生成酒店评论数据（2000条）...")

pos_templates = [
    "房间很干净，床铺也舒服，下次还会来。",
    "前台小姐姐服务态度特别好，办入住很快。",
    "早餐品种丰富，味道不错，性价比高。",
    "地理位置很方便，离地铁站走路五分钟。",
    "房间隔音不错，睡眠质量很好。",
    "酒店整体装修风格很温馨，拍照很好看。",
    "浴室干净，热水很快，沐浴用品也好用。",
    "空调制冷效果好，夏天住着很舒服。",
    "停车场很大，自驾游很方便。",
    "客房服务响应快，提出的需求都及时处理了。",
    "无线网络信号强，看视频打游戏都没问题。",
    "周围吃饭的地方多，出门就是美食街。",
    "退房很方便，不用等很久。",
    "前台帮忙叫了出租车，服务周到。",
    "房间有免费的矿泉水和茶包，细节做得好。",
    "大堂宽敞明亮，等人也不觉得无聊。",
    "保洁阿姨每天打扫得很仔细。",
    "会员价很划算，办了个会员卡。",
    "商务房有独立办公桌，出差住很合适。",
    "窗外风景不错，能看到城市夜景。",
]

neg_templates = [
    "空调不制冷，大夏天热得睡不着。",
    "隔音太差了，隔壁说话都能听到。",
    "前台排队排了二十分钟才办上入住。",
    "卫生间有异味，下水道堵了也没人修。",
    "房间地毯有污渍，感觉不太干净。",
    "WiFi 信号差，经常断网，影响工作。",
    "早餐太简单了，就几样东西翻来覆去。",
    "窗户关不严，晚上外面的噪音很大。",
    "热水器忽冷忽热，洗澡体验很差。",
    "退房要等半小时查房，效率太低。",
    "房间有蚊子，前台说没有蚊香。",
    "停车场太小，晚到了没有车位。",
    "枕头太硬了，睡一晚上脖子疼。",
    "电梯等了十分钟都没来，高峰期太拥挤。",
    "定的大床房给了双床房，沟通半天才换。",
    "房间电视遥控器没电，打了前台也没来换。",
    "被子有烟味，感觉不像新洗的。",
    "走廊灯光太暗，晚上找房间不方便。",
    "附近在施工，白天噪音特别大。",
    "浴巾上有破洞，看着就不想用。",
]

def augment(text):
    prefixes = ["", "总体来说，", "这次入住感觉", "个人觉得", "说实话，", "客观评价，"]
    suffixes = ["", " 希望能改进。", " 推荐给朋友了。", " 下次再看看吧。", " 总的来说还行。"]
    p = random.choice(prefixes)
    s = random.choice(suffixes) if random.random() > 0.5 else ""
    return p + text + s

reviews = []
for _ in range(1000):
    reviews.append({"text": augment(random.choice(pos_templates)), "label": 1})
for _ in range(1000):
    reviews.append({"text": augment(random.choice(neg_templates)), "label": 0})
random.shuffle(reviews)

df_rev = pd.DataFrame(reviews)
rev_path = os.path.join(DATA_DIR, "hotel_reviews.csv")
df_rev.to_csv(rev_path, index=False, encoding="utf-8-sig")
print(f"  保存: {rev_path}  ({len(df_rev)} 条)")
print(f"  正面: {(df_rev.label==1).sum()}  负面: {(df_rev.label==0).sum()}")
print("\n数据生成完毕。")
