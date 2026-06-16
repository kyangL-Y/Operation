# SpringBoot + Vue + RAG 酒店运营支持系统

本目录为毕业设计可直接继续开发的基础工程骨架，不包含正式业务数据。

## 目录结构

```text
项目代码骨架/
├─ backend/        # SpringBoot 后端
├─ frontend/       # Vue3 + Vite 前端
└─ docs/           # 开发与接口说明
```

## 源码提交说明

本项目提交源码时保留后端、前端、ML 服务、数据库脚本、文档和启动脚本。以下内容属于本地环境、公开数据集原始文件或可重建产物，不应随源码提交：

- `frontend/node_modules/`、`frontend/dist/`
- `backend/target/`
- `.venv_ml/`、`ml/.venv/`、`ml/__pycache__/`
- `logs/`、`ml/output/`
- `deepseek.env` 等本地密钥文件
- `ml/models/*.joblib`、`ml/data/external/*.csv`、`ml/data/external/*.zip`

生成式问答密钥仅通过本地环境变量或 `deepseek.env` 配置；提交时只保留 `deepseek.env.example`。
预测模型文件未提交时，ML 服务会自动降级为启发式预测，确保面试展示环境可直接启动。

## 快速启动

### ML 服务

```bash
cd ml
python api_server.py
```

默认端口：`5000`

如需启用生成式问答，可在启动 ML 服务前设置兼容 OpenAI Chat Completions 的环境变量：

```powershell
$env:OPENAI_API_KEY='你的密钥'
$env:OPENAI_BASE_URL='https://你的网关/v1'
$env:OPENAI_MODEL='gpt-5.4'
```

也兼容等价别名：`CHAT_API_KEY`、`CHAT_BASE_URL`、`CHAT_MODEL`。

### 后端

```bash
cd backend
mvn -q -DskipTests package
java -jar target/hotel-ops-0.0.1-SNAPSHOT.jar
```

默认端口：`8080`

默认本地演示配置不强制依赖 MySQL；未显式开启 JDBC 时，登录账号、知识库和运营指标会自动走内存 / CSV 降级。

当前演示脚本 `start_demo.ps1` 默认使用内存数据，便于无数据库环境快速展示。如需启用 MySQL，请先启动数据库并设置以下环境变量。

如需启用 MySQL，请先启动数据库，并设置：

```powershell
$env:HOTEL_JDBC_ENABLED='true'
$env:HOTEL_DB_URL='jdbc:mysql://localhost:3306/hotel_ops?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true&useSSL=false'
$env:HOTEL_DB_USER='root'
$env:HOTEL_DB_PASSWORD='root'
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

默认端口：`5173`

### 一键演示启动

```powershell
./start_demo.ps1
```

脚本会同时拉起 `ml`、`backend`、`frontend` 三个服务。

## 当前能力

- 登录鉴权：`POST /api/auth/login`（header: `X-Auth-Token`）
- 健康检查：`GET /api/health`
- 问答接口：`POST /api/rag/ask`
- 看板接口：`GET /api/ops/dashboard`
- 决策支持：`GET /api/ops/decision-support`
- 知识管理：`POST/GET /api/kb/docs`
- 入住率预测：`POST /api/ml/predict-occupancy`
- 营收预测：`POST /api/ml/predict-revenue`
- 订单取消风险预测：`POST /api/ml/predict-cancellation`
- 决策分析：`POST /api/ml/decision/analyze`

## 当前技术主线

- RAG 问答：text2vec 语义检索 + 兼容 OpenAI Chat Completions 的生成接口，未配置生成接口时降级到模板回答；ML 服务不可用时降级到关键词检索
- 运营预测：入住率预测、营收预测与订单取消风险预测
- 决策支持：基于预测结果、异常指标和知识库联动生成运营建议
- 可视化：Vue 3 + ECharts 看板展示当前指标、趋势和决策建议

## 训练数据方案

- 公开主训练集：训练脚本已支持自动接入 `Hotel Booking Demand`（约 `119,390` 条预订记录）
- 辅助训练集：训练脚本已支持自动接入 `Hotel Reservations`（约 `36,275` 条记录）
- 数据放置目录：将原始 CSV 放入 `ml/data/external/`，脚本会自动完成字段标准化、日期聚合、入住率/营收代理指标构造与特征工程
- 双粒度训练：入住率与营收预测使用日级经营样本，公开数据经处理后形成 `2126` 条日级记录、`2105` 条特征就绪样本；订单取消风险预测使用订单级样本，共 `155,665` 条预订记录
- 训练逻辑：入住率/营收使用 `RandomForestRegressor`，订单取消风险预测使用 `RandomForestClassifier` 输出取消概率；决策支持采用“预测结果 + 规则引擎 + RAG”，不额外依赖单独监督训练集
- 验证策略：按数据源分组的时间顺序留出测试集，并使用扩展窗口交叉验证，避免随机切分高估模型效果
- 训练产物：`prediction_report.json`、`cv_results_*.csv/.png`、预测对比图、残差图、ROC 曲线、混淆矩阵和特征重要性图均输出到 `ml/output/`
- 工程说明：系统保留离线演示机制用于本地联调；一旦检测到公开数据集文件，正式训练与 EDA 只使用公开数据，不混入开发联调数据

## 公开数据集参考

- `Hotel Booking Demand`：<https://www.sciencedirect.com/science/article/pii/S2352340918315191>
- `Hotel Reservations`：<https://www.kaggle.com/datasets/ahsan81/hotel-reservations-classification-dataset>
- `Inside Airbnb`：<https://insideairbnb.com/get-the-data/>

## 后续开发建议

- 接入 MySQL 与向量库（Milvus/FAISS）
- 实现知识导入、切块、重排与向量化流水线
- 接入真实 PMS 数据与报表导出能力
- 增加登录、权限、日志审计和测试

## 演示账号

- `admin / admin123`
- `staff / staff123`

## 自动化脚本

- `start_demo.ps1`：启动 ML 服务、后端与前端
- `verify_build.ps1`：ML Python 语法检查 + 后端测试/编译 + 前端构建
- `smoke_test.ps1`：对运行中的系统执行闭环冒烟验证

## 闭环验证顺序

1. 运行 `./start_demo.ps1`，确认 `5000/8080/5173` 三个端口对应服务已启动。
2. 如首次启动前端，先在 `frontend/` 下执行一次 `npm install`。
3. 运行 `./smoke_test.ps1`，验证登录、RAG 问答、运营看板、决策支持、入住率预测、营收预测、订单取消风险预测。
4. 前端打开 `http://localhost:5173`，使用 `admin / admin123` 登录后查看 Dashboard 和 Ask 页面。
5. 若 `smoke_test.ps1` 通过，即可证明当前正式版本已经完成“RAG + 三预测 + 决策支持”的核心闭环。
