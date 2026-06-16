# 酒店运营支持系统

基于 Spring Boot、Vue 3 和 Python ML/RAG 的酒店运营支持系统。项目面向酒店经营管理场景，覆盖经营看板、知识问答、入住率预测、营收预测、取消风险预测、决策建议、知识库管理、通知与审计等功能，适合作为毕业设计与面试展示项目。

## 项目亮点

- 前后端分离：Spring Boot 3 后端提供统一业务 API，Vue 3 + Vite 前端提供运营工作台。
- RAG 问答闭环：支持知识检索、深度问答、生成式回答兜底和无外部密钥时的模板回答。
- 预测与决策：提供入住率、营收、订单取消风险三类预测，并联动经营建议。
- 演示稳定性：默认不依赖 MySQL 或外部大模型密钥，clone 后可用内存数据和启发式预测跑通核心流程。
- 工程化资料：包含接口清单、测试用例、技术方案、启动脚本和构建验证脚本。

## 目录结构

```text
.
├─ project/              # 可运行工程
│  ├─ backend/           # Spring Boot 后端
│  ├─ frontend/          # Vue 3 前端
│  ├─ ml/                # Python 预测与 RAG 服务
│  ├─ docs/              # 接口、测试、技术方案文档
│  ├─ start_demo.ps1     # 一键启动三端服务
│  ├─ verify_build.ps1   # 构建与测试验证
│  └─ smoke_test.ps1     # 运行态冒烟测试
├─ designs/              # 界面设计稿
├─ materials/            # 答辩与论文相关材料
└─ README.md
```

## 快速启动

```powershell
cd project
./start_demo.ps1
```

启动后访问：

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8080`
- ML/RAG 服务：`http://localhost:5000`

演示账号：

- `admin / admin123`
- `staff / staff123`

## 构建验证

```powershell
cd project
./verify_build.ps1
```

服务启动后可执行冒烟测试：

```powershell
cd project
./smoke_test.ps1
```

## 可选配置

默认配置使用内存数据，便于面试官快速运行。需要连接 MySQL 时，可先执行 `project/docker-compose.yml` 启动数据库，再设置：

```powershell
$env:HOTEL_JDBC_ENABLED='true'
$env:HOTEL_DB_URL='jdbc:mysql://localhost:3306/hotel_ops?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true&useSSL=false'
$env:HOTEL_DB_USER='root'
$env:HOTEL_DB_PASSWORD='root123'
```

需要启用外部生成式问答时，复制 `project/deepseek.env.example` 为 `project/deepseek.env` 并填写真实密钥。真实密钥文件不会提交。

## 模型与数据说明

仓库不提交大型 `joblib` 模型和公开数据集原始 CSV/ZIP，避免超过 GitHub 文件限制并保持仓库轻量。ML 服务在缺少训练产物时会自动使用启发式预测兜底；如需复现实验，可按 `project/ml/train_prediction.py` 重新训练并将模型放入 `project/ml/models/`。

更多工程说明见 [project/README.md](project/README.md)。
