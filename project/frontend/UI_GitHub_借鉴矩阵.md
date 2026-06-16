# 前端 UI GitHub 借鉴矩阵

更新时间：2026-03-15

## 目标

将当前“酒店运营中台”前端继续向成熟开源项目的界面语言靠拢，但只借鉴信息架构、布局模式和交互组织方式，不直接照搬整站代码。

## 模块拆解

### 1. 全局壳层 / 后台导航

- 参考仓库：`vbenjs/vue-vben-admin`
  链接：<https://github.com/vbenjs/vue-vben-admin>
  借鉴点：左侧导航、顶部工作区说明、后台工作流的路由组织方式。
- 参考仓库：`TailAdmin/vue-tailwind-admin-dashboard`
  链接：<https://github.com/TailAdmin/vue-tailwind-admin-dashboard>
  借鉴点：数据中台的卡片层级、状态标签、右侧信息栏节奏。

### 2. 运营总览 / 决策驾驶舱

- 参考仓库：`TailAdmin/free-tailwind-admin-dashboard-template`
  链接：<https://github.com/TailAdmin/free-tailwind-admin-dashboard-template>
  借鉴点：KPI 卡片、图表区块、任务卡和数据密集布局。
- 参考仓库：`vbenjs/vue-vben-admin`
  链接：<https://github.com/vbenjs/vue-vben-admin>
  借鉴点：后台首页的“业务面板 + 行动面板”拆分思路。

### 3. 智能问答页

- 参考仓库：`assistant-ui/assistant-ui`
  链接：<https://github.com/assistant-ui/assistant-ui>
  借鉴点：聊天线程、输入区、来源侧栏、追问结构。
- 参考仓库：`vercel/ai-chatbot`
  链接：<https://github.com/vercel/ai-chatbot>
  借鉴点：AI 问答页的单任务专注布局和消息流组织方式。

### 4. 知识库页

- 参考仓库：`helpyio/helpy`
  链接：<https://github.com/helpyio/helpy>
  借鉴点：知识库目录、搜索、文章预览和帮助中心式信息组织。
- 参考仓库：`vbenjs/vue-vben-admin`
  链接：<https://github.com/vbenjs/vue-vben-admin>
  借鉴点：后台表单页与列表页并置时的工作区结构。

### 5. 登录页

- 参考仓库：`TailAdmin/vue-tailwind-admin-dashboard`
  链接：<https://github.com/TailAdmin/vue-tailwind-admin-dashboard>
  借鉴点：企业后台登录页的品牌说明、功能摘要和表单区分栏。

## 当前落地方式

- `App.vue`
  借鉴“后台壳层 + 工作台摘要 + 快捷工作流”。
- `DashboardView.vue`
  借鉴“指挥台 + 决策矩阵 + 行动卡片 + 趋势图”。
- `AskView.vue`
  借鉴“聊天线程 + 引用侧栏 + 推荐追问”。
- `KnowledgeView.vue`
  借鉴“目录列表 + 文档预览 + 治理面板”。
- `LoginView.vue`
  借鉴“品牌说明 + 模块摘要 + 统一入口表单”。

## 借鉴原则

- 优先借鉴 Vue 项目的布局与交互，减少技术栈错位。
- React/Next 项目主要借鉴信息架构，不直接照搬实现代码。
- 只借鉴模块设计、信息层级和交互结构，不做整站复制。
- 实际复用代码前，必须再次确认目标仓库 license。
