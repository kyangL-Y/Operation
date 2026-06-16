# 公开数据集放置说明

将公开数据集的 CSV 文件放到本目录后，`train_prediction.py` 和 `eda_analysis.py` 会自动优先接入它们，作为正式训练链路的数据来源。

建议文件名：

- `hotel_bookings.csv`
  - 对应 `Hotel Booking Demand`
  - 参考来源：<https://www.sciencedirect.com/science/article/pii/S2352340918315191>
- `hotel_reservations.csv`
  - 对应 `Hotel Reservations`
  - 参考来源：<https://www.kaggle.com/datasets/ahsan81/hotel-reservations-classification-dataset>

说明：

- 本目录下只需要放原始 CSV，不需要手工改字段名。
- 训练脚本会自动做字段标准化、日期聚合、入住率/营收代理指标构造和特征工程。
- 正式训练与 EDA 在检测到公开数据集后，只使用公开数据，不混入开发联调数据。
- 如果本目录没有公开数据集，系统会启用内部离线演示机制，保证本地联调不被阻塞。
