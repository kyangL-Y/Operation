<template>
  <div class="page-stack">
    <section class="workspace-card">
      <div class="section-header">
        <div class="section-header__copy">
          <p class="workspace-label">审计日志</p>
          <h3 class="section-title">操作日志</h3>
          <p class="muted">共 {{ total }} 条记录</p>
        </div>
        <div class="action-row">
          <select v-model="filterModule" class="filter-select">
            <option value="">全部范围</option>
            <option value="AUTH">登录</option>
            <option value="ADMIN">管理</option>
            <option value="KB">知识库</option>
            <option value="OPS">运营</option>
          </select>
          <select v-model="filterAction" class="filter-select">
            <option value="">全部操作</option>
            <option value="LOGIN">登录</option>
            <option value="LOGOUT">退出</option>
            <option value="CREATE">创建</option>
            <option value="UPDATE">更新</option>
            <option value="DELETE">删除</option>
          </select>
          <button type="button" class="ghost-btn" @click="loadLogs">刷新</button>
        </div>
      </div>

      <div class="audit-ops-strip">
        <article class="audit-ops-strip__item">
          <span>当前记录</span>
          <strong>{{ filteredLogs.length }} 条</strong>
        </article>
        <article class="audit-ops-strip__item">
          <span>筛选状态</span>
          <strong>{{ (filterModule ? moduleLabel(filterModule) : "全部范围") + " / " + (filterAction ? actionLabel(filterAction) : "全部操作") }}</strong>
        </article>
        <article class="audit-ops-strip__item">
          <span>分页位置</span>
          <strong>第 {{ page + 1 }} / {{ totalPages }} 页</strong>
        </article>
      </div>

      <div class="audit-fact-strip">
        <article class="audit-fact-card">
          <span>日志范围</span>
          <strong>认证 / 管理 / 知识库 / 运营</strong>
        </article>
        <article class="audit-fact-card">
          <span>追踪目标</span>
          <strong>关键动作可审计</strong>
        </article>
        <article class="audit-fact-card">
          <span>当前能力</span>
          <strong>分页、筛选、时间线查看</strong>
        </article>
      </div>

      <div class="audit-command-grid">
        <article class="audit-command-card">
          <span>当前审计任务</span>
          <strong>{{ loading ? "同步日志中" : "复核关键动作" }}</strong>
        </article>
        <article class="audit-command-card">
          <span>焦点筛选</span>
          <strong>{{ (filterModule ? moduleLabel(filterModule) : "全部范围") + " / " + (filterAction ? actionLabel(filterAction) : "全部操作") }}</strong>
        </article>
        <article class="audit-command-card">
          <span>分页审阅</span>
          <strong>第 {{ page + 1 }} / {{ totalPages }} 页</strong>
        </article>
      </div>

      <div v-if="loading" class="empty-state">加载中...</div>

      <div v-else-if="filteredLogs.length === 0" class="empty-state">
        暂无操作日志记录。
      </div>

      <div v-else class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>用户</th>
              <th>范围</th>
              <th>操作</th>
              <th>详情</th>
              <th>来源地址</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in filteredLogs" :key="log.id">
              <td>{{ formatTime(log.createdAt) }}</td>
              <td>
                <div class="user-cell">
                  <span class="user-avatar">{{ (log.username || 'U').charAt(0).toUpperCase() }}</span>
                  <span>{{ log.username || '-' }}</span>
                </div>
              </td>
              <td><span class="badge" :class="moduleClass(log.module)">{{ moduleLabel(log.module) }}</span></td>
              <td><span class="badge" :class="actionClass(log.action)">{{ actionLabel(log.action) }}</span></td>
              <td class="detail-cell">{{ log.detail || '-' }}</td>
              <td class="ip-cell">{{ log.ipAddress || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="totalPages > 1" class="pagination">
        <button type="button" class="ghost-btn ghost-btn--compact" :disabled="page === 0" @click="page--; loadLogs()">上一页</button>
        <span class="page-info">第 {{ page + 1 }} / {{ totalPages }} 页</span>
        <button type="button" class="ghost-btn ghost-btn--compact" :disabled="page >= totalPages - 1" @click="page++; loadLogs()">下一页</button>
      </div>

      <p v-if="message" class="notice notice--danger">{{ message }}</p>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import http from "../api/http";

const logs = ref([]);
const loading = ref(false);
const message = ref("");
const page = ref(0);
const pageSize = ref(20);
const total = ref(0);
const filterModule = ref("");
const filterAction = ref("");

const totalPages = computed(() => Math.ceil(total.value / pageSize.value) || 1);
const filteredLogs = computed(() => {
  let result = logs.value;
  if (filterModule.value) result = result.filter((l) => l.module === filterModule.value);
  if (filterAction.value) result = result.filter((l) => l.action?.includes(filterAction.value));
  return result;
});

function formatTime(dateStr) {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleString("zh-CN", {
    month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit"
  });
}

function moduleLabel(mod) {
  const map = { AUTH: "登录", ADMIN: "管理", KB: "知识库", OPS: "运营" };
  return map[mod] || mod || "-";
}

function moduleClass(mod) {
  const map = { AUTH: "badge--warning", ADMIN: "badge--danger", KB: "badge--success", OPS: "badge--muted" };
  return map[mod] || "badge--muted";
}

function actionLabel(action) {
  if (!action) return "-";
  if (action.includes("LOGIN")) return "登录";
  if (action.includes("LOGOUT")) return "退出";
  if (action.includes("CREATE")) return "创建";
  if (action.includes("UPDATE")) return "更新";
  if (action.includes("DELETE")) return "删除";
  return action;
}

function actionClass(action) {
  if (!action) return "badge--muted";
  if (action.includes("DELETE")) return "badge--danger";
  if (action.includes("CREATE")) return "badge--success";
  if (action.includes("UPDATE")) return "badge--warning";
  return "badge--muted";
}

async function loadLogs() {
  loading.value = true;
  message.value = "";
  try {
    const { data } = await http.get(`/admin/audit-logs?page=${page.value}&size=${pageSize.value}`);
    logs.value = data.data?.content || data.data || [];
    total.value = data.data?.totalElements || logs.value.length;
  } catch {
    // 后端未就绪时展示演示数据
    logs.value = [
      { id: 1, username: "admin", action: "LOGIN", module: "AUTH", detail: "管理员登录系统", ipAddress: "127.0.0.1", createdAt: new Date().toISOString() },
      { id: 2, username: "admin", action: "CREATE_USER", module: "ADMIN", detail: "创建用户: test001", ipAddress: "127.0.0.1", createdAt: new Date(Date.now() - 1800000).toISOString() },
      { id: 3, username: "staff", action: "LOGIN", module: "AUTH", detail: "员工登录系统", ipAddress: "192.168.1.100", createdAt: new Date(Date.now() - 3600000).toISOString() },
      { id: 4, username: "admin", action: "UPDATE_ROLE", module: "ADMIN", detail: "更新用户角色: 业务管理 -> 系统管理员", ipAddress: "127.0.0.1", createdAt: new Date(Date.now() - 7200000).toISOString() },
      { id: 5, username: "staff", action: "CREATE_DOC", module: "KB", detail: "创建资料文档: 前台接待流程", ipAddress: "192.168.1.100", createdAt: new Date(Date.now() - 86400000).toISOString() },
      { id: 6, username: "admin", action: "DELETE_DOC", module: "KB", detail: "删除资料文档: 旧版流程", ipAddress: "127.0.0.1", createdAt: new Date(Date.now() - 172800000).toISOString() },
      { id: 7, username: "manager", action: "UPDATE_METRIC", module: "OPS", detail: "更新 2026-03-25 运营指标并触发预测刷新", ipAddress: "192.168.1.120", createdAt: new Date(Date.now() - 5400000).toISOString() }
    ];
    total.value = logs.value.length;
    message.value = "当前展示的是演示审计日志；连接后端后会切换为真实记录。";
  } finally {
    loading.value = false;
  }
}

onMounted(loadLogs);
</script>

<style scoped>
.audit-ops-strip,
.audit-fact-strip,
.audit-command-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.audit-ops-strip__item,
.audit-fact-card,
.audit-command-card {
  display: grid;
  gap: var(--spacing-sm);
  padding: var(--spacing-lg) var(--spacing-xl);
  border-radius: var(--radius-lg);
  border: 1px solid var(--line);
  background: var(--bg-panel);
  box-shadow: var(--shadow-xs);
  transition: all var(--transition-base);
}

.audit-ops-strip__item:hover,
.audit-fact-card:hover,
.audit-command-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
  border-color: var(--line-strong);
}

.audit-ops-strip__item span,
.audit-fact-card span,
.audit-command-card span {
  font-size: 11px;
  color: var(--ink-soft);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 700;
}

.audit-ops-strip__item strong {
  font-size: 18px;
  line-height: 1.5;
  color: var(--ink-strong);
}

.audit-fact-card strong {
  font-size: 13px;
  color: var(--ink-strong);
}

.audit-command-card strong {
  font-size: 15px;
  color: var(--ink-strong);
  line-height: 1.55;
}

.audit-ops-strip__item small,
.audit-fact-card p,
.audit-command-card p {
  margin: 0;
  color: var(--ink-soft);
  font-size: 12px;
  line-height: 1.6;
}

.filter-select {
  width: auto;
  min-width: 100px;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-avatar {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  background: var(--accent-soft);
  color: var(--accent-strong);
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.detail-cell {
  max-width: 300px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--ink-soft);
  font-size: 13px;
}

.ip-cell {
  font-family: monospace;
  font-size: 12px;
  color: var(--ink-soft);
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding-top: 12px;
}

.page-info {
  font-size: 13px;
  color: var(--ink-soft);
}
@media (max-width: 860px) {
  .audit-ops-strip,
  .audit-fact-strip,
  .audit-command-grid {
    grid-template-columns: 1fr;
  }
}
</style>
