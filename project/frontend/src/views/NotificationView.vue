<template>
  <div class="page-stack">
    <section class="workspace-card">
      <div class="section-header">
        <div class="section-header__copy">
          <p class="workspace-label">通知中心</p>
          <h3 class="section-title">消息通知</h3>
          <p class="muted">共 {{ total }} 条，未读 {{ unreadCount }} 条</p>
        </div>
        <div class="action-row">
          <select v-model="filterType" class="filter-select">
            <option value="">全部类型</option>
            <option value="INFO">信息</option>
            <option value="WARNING">警告</option>
            <option value="ALERT">告警</option>
            <option value="SUCCESS">成功</option>
          </select>
          <button type="button" class="ghost-btn" @click="markAllRead" :disabled="unreadCount === 0">
            全部已读
          </button>
          <button type="button" @click="loadNotifications">刷新</button>
        </div>
      </div>

      <div class="notification-fact-strip">
        <article class="notification-fact-card">
          <span>通知来源</span>
          <strong>预测状态 + 经营预警线 + 系统事件</strong>
        </article>
        <article class="notification-fact-card">
          <span>预警范围</span>
          <strong>优先关注核心经营指标</strong>
        </article>
        <article class="notification-fact-card">
          <span>阅读动作</span>
          <strong>支持筛选与已读回写</strong>
        </article>
      </div>

      <div v-if="loading" class="empty-state">加载中...</div>

      <div v-else-if="filteredList.length === 0" class="empty-state">
        暂无通知消息。
      </div>

      <div v-else class="notification-list">
        <div
          v-for="item in filteredList"
          :key="item.id"
          class="notification-item"
          :class="{ 'notification-item--unread': !item.isRead }"
        >
          <div class="notification-dot" :class="typeClass(item.type)"></div>
          <div class="notification-content">
            <div class="notification-head">
              <strong>{{ item.title }}</strong>
              <div class="notification-meta">
                <span class="badge" :class="typeClass(item.type)">{{ typeLabel(item.type) }}</span>
                <span class="notification-time">{{ formatTime(item.createdAt) }}</span>
                <span v-if="!item.isRead" class="unread-dot">未读</span>
              </div>
            </div>
            <p class="notification-body">{{ item.content }}</p>
          </div>
          <button
            v-if="!item.isRead"
            type="button"
            class="ghost-btn ghost-btn--compact"
            @click="markRead(item.id)"
          >
            标为已读
          </button>
        </div>
      </div>

      <p v-if="message" class="notice notice--danger">{{ message }}</p>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import http from "../api/http";

const notifications = ref([]);
const loading = ref(false);
const message = ref("");
const filterType = ref("");

const filteredList = computed(() =>
  filterType.value
    ? notifications.value.filter((n) => n.type === filterType.value)
    : notifications.value
);
const unreadCount = computed(() => notifications.value.filter((n) => !n.isRead).length);
const total = computed(() => notifications.value.length);

function typeLabel(type) {
  const map = { INFO: "信息", WARNING: "警告", ALERT: "告警", SUCCESS: "成功" };
  return map[type] || type;
}

function typeClass(type) {
  const map = { INFO: "badge--muted", WARNING: "badge--warning", ALERT: "badge--danger", SUCCESS: "badge--success" };
  return map[type] || "badge--muted";
}

function formatTime(dateStr) {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleString("zh-CN", {
    month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit"
  });
}

async function loadNotifications() {
  loading.value = true;
  message.value = "";
  try {
    const { data } = await http.get("/notifications");
    notifications.value = data.data || [];
  } catch {
    // 后端未就绪时展示演示数据
    notifications.value = [
      { id: 1, title: "系统启动成功", content: "酒店运营支持系统已成功启动，前端页面、后端服务与演示数据可用。", type: "SUCCESS", isRead: false, createdAt: new Date().toISOString() },
      { id: 2, title: "预测与问答服务检测", content: "预测服务与问答服务已就绪，可查看经营预测并查询处理建议。", type: "INFO", isRead: true, createdAt: new Date(Date.now() - 3600000).toISOString() },
      { id: 3, title: "入住率预警", content: "当前入住率低于预警线 70%，请结合渠道策略和价格策略复盘。", type: "ALERT", isRead: false, createdAt: new Date(Date.now() - 7200000).toISOString() },
      { id: 4, title: "差评率上升", content: "近 7 日差评率较上周上升 2.3%，建议在知识库中查询高频投诉处置流程并排查原因。", type: "WARNING", isRead: false, createdAt: new Date(Date.now() - 86400000).toISOString() }
    ];
    message.value = "当前展示的是演示通知；连接后端后会切换为实时消息。";
  } finally {
    loading.value = false;
  }
}

async function markRead(id) {
  try {
    await http.put(`/notifications/${id}/read`);
    const item = notifications.value.find((n) => n.id === id);
    if (item) item.isRead = true;
  } catch {
    const item = notifications.value.find((n) => n.id === id);
    if (item) item.isRead = true;
  }
}

async function markAllRead() {
  try {
    await http.put("/notifications/read-all");
    notifications.value.forEach((n) => { n.isRead = true; });
  } catch {
    notifications.value.forEach((n) => { n.isRead = true; });
  }
}

onMounted(loadNotifications);
</script>

<style scoped>
.notification-fact-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.notification-fact-card {
  display: grid;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  border: 1px solid var(--line);
  background: var(--bg-panel-muted);
  box-shadow: var(--shadow-xs);
  transition: all var(--transition-base);
}

.notification-fact-card:hover {
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
  border-color: var(--line-strong);
}

.notification-fact-card span {
  font-size: 11px;
  color: var(--ink-soft);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 700;
}

.notification-fact-card strong {
  font-size: 13px;
  color: var(--ink-strong);
}

.notification-fact-card p {
  margin: 0;
  color: var(--ink-soft);
  font-size: 12px;
  line-height: 1.6;
}

.filter-select {
  width: auto;
  min-width: 120px;
}

.notification-list {
  display: grid;
  gap: 2px;
}

.notification-item {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-md);
  padding: var(--spacing-lg) var(--spacing-xl);
  border-radius: var(--radius-md);
  border: 1px solid var(--line);
  background: var(--bg-panel);
  transition: all var(--transition-base);
}

.notification-item:hover {
  box-shadow: var(--shadow-sm);
  border-color: var(--line-strong);
}

.notification-item--unread {
  background: var(--accent-soft);
  border-color: var(--accent);
}

.notification-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  margin-top: 6px;
  flex-shrink: 0;
  background: var(--ink-soft);
}

.notification-dot.badge--success { background: var(--success); }
.notification-dot.badge--warning { background: var(--warning); }
.notification-dot.badge--danger  { background: var(--danger); }

.notification-content {
  flex: 1;
  min-width: 0;
  display: grid;
  gap: 4px;
}

.notification-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.notification-head strong {
  font-size: 14px;
  color: var(--ink-strong);
}

.notification-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.notification-time {
  color: var(--ink-soft);
  font-size: 12px;
}

.unread-dot {
  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
  background: var(--accent-soft);
  padding: 2px 8px;
  border-radius: 999px;
}

.notification-body {
  margin: 0;
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.65;
}
@media (max-width: 860px) {
  .notification-fact-strip {
    grid-template-columns: 1fr;
  }
}
</style>
