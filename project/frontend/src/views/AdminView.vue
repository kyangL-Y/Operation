<template>
  <div class="page-stack">
    <section class="workspace-card">
      <div class="section-header">
        <div class="section-header__copy">
          <p class="workspace-label">管理员控制台</p>
          <h3 class="section-title">账号管理</h3>
        </div>
        <div class="action-row">
          <button type="button" class="ghost-btn" @click="loadAdminData">刷新数据</button>
        </div>
      </div>

      <div class="admin-metrics">
        <div class="metric-card">
          <span>总账号</span>
          <strong>{{ overview.totalUsers ?? users.length }}</strong>
        </div>
        <div class="metric-card">
          <span>启用</span>
          <strong>{{ activeUsers }}</strong>
        </div>
        <div class="metric-card">
          <span>停用</span>
          <strong>{{ disabledUsers }}</strong>
        </div>
        <div class="metric-card">
          <span>当前筛选</span>
          <strong>{{ filteredUsers.length }}</strong>
        </div>
      </div>

      <div class="admin-toolbar">
        <input v-model.trim="userQuery" placeholder="搜索用户名或姓名" />
        <select v-model="roleFilter">
          <option value="ALL">全部角色</option>
          <option v-for="item in roles" :key="item" :value="item">{{ roleLabel(item) }}</option>
        </select>
        <select v-model="statusFilter">
          <option value="ALL">全部状态</option>
          <option value="ACTIVE">启用</option>
          <option value="DISABLED">停用</option>
        </select>
        <button type="button" class="ghost-btn" @click="clearFilters">清空筛选</button>
      </div>

      <div v-if="selectedIds.length" class="admin-batch-bar">
        <strong>已选 {{ selectedIds.length }} 个账号</strong>
        <div class="action-row">
          <button type="button" class="ghost-btn ghost-btn--compact" @click="clearSelection">清空</button>
          <button type="button" class="ghost-btn ghost-btn--compact" :disabled="!canBatchEnable" @click="batchUpdateStatus('ACTIVE')">批量启用</button>
          <button type="button" class="ghost-btn ghost-btn--compact" :disabled="!canBatchDisable" @click="batchUpdateStatus('DISABLED')">批量停用</button>
        </div>
      </div>

      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 40px;">
                <input type="checkbox" :checked="isAllVisibleSelected" @click.stop @change="toggleSelectAll" />
              </th>
              <th>账号</th>
              <th>姓名</th>
              <th>角色</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in filteredUsers" :key="user.id">
              <td>
                <input type="checkbox" :checked="selectedIds.includes(user.id)" @click.stop @change="toggleSelection(user.id)" />
              </td>
              <td>
                <strong>{{ user.username }}</strong>
                <span class="muted">#{{ user.id }}</span>
              </td>
              <td>{{ user.displayName }}</td>
              <td>
                <select :value="user.role" @click.stop @change="changeRole(user, $event.target.value)">
                  <option v-for="item in roles" :key="item" :value="item">{{ roleLabel(item) }}</option>
                </select>
              </td>
              <td>
                <span class="badge" :class="user.status === 'ACTIVE' ? 'badge--success' : 'badge--muted'">
                  {{ user.status === 'ACTIVE' ? '启用' : '停用' }}
                </span>
              </td>
              <td>
                <div class="action-row">
                  <button type="button" class="ghost-btn ghost-btn--compact" @click="toggleStatus(user)">
                    {{ user.status === 'ACTIVE' ? '停用' : '启用' }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <p v-if="message" class="notice" :class="success ? 'notice--success' : 'notice--danger'">{{ message }}</p>
    </section>

    <section class="workspace-card">
      <div class="section-header">
        <div class="section-header__copy">
          <p class="workspace-label">新增账号</p>
          <h3 class="section-title">新增账号</h3>
        </div>
      </div>

      <form @submit.prevent="createUser" class="form-stack">
        <div class="form-row">
          <div class="form-field">
            <label>姓名</label>
            <input v-model.trim="form.displayName" placeholder="例如：前台主管" required />
          </div>
          <div class="form-field">
            <label>用户名</label>
            <input v-model.trim="form.username" placeholder="例如：frontlead" required />
          </div>
          <div class="form-field">
            <label>初始密码</label>
            <input v-model="form.password" type="password" placeholder="至少6位" required />
          </div>
        </div>

        <div class="form-field">
          <label>角色</label>
          <div class="role-picker">
            <button
              v-for="item in roles"
              :key="item"
              type="button"
              class="ghost-btn ghost-btn--compact"
              :class="{ 'ghost-btn--active': form.role === item }"
              @click="form.role = item"
            >
              {{ roleLabel(item) }}
            </button>
          </div>
        </div>

        <div class="action-row">
          <button type="submit">新增账号</button>
          <button type="button" class="ghost-btn" @click="resetForm">清空</button>
        </div>
      </form>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import http from "../api/http";

const users = ref([]);
const overview = ref({});
const roles = ["ADMIN", "MANAGER", "STAFF"];
const userQuery = ref("");
const roleFilter = ref("ALL");
const statusFilter = ref("ALL");
const selectedIds = ref([]);
const message = ref("");
const success = ref(false);

const form = ref({
  username: "",
  password: "",
  displayName: "",
  role: "STAFF"
});

function roleLabel(r) {
  const map = { ADMIN: "管理员", MANAGER: "经理", STAFF: "员工" };
  return map[r] || r;
}

const activeUsers = computed(() => users.value.filter(u => u.status === "ACTIVE").length);
const disabledUsers = computed(() => users.value.filter(u => u.status === "DISABLED").length);

const filteredUsers = computed(() => {
  let list = users.value;
  if (userQuery.value) {
    const q = userQuery.value.toLowerCase();
    list = list.filter(u => u.username.toLowerCase().includes(q) || u.displayName.toLowerCase().includes(q));
  }
  if (roleFilter.value !== "ALL") {
    list = list.filter(u => u.role === roleFilter.value);
  }
  if (statusFilter.value !== "ALL") {
    list = list.filter(u => u.status === statusFilter.value);
  }
  return list;
});

const isAllVisibleSelected = computed(() => {
  return filteredUsers.value.length > 0 && filteredUsers.value.every(u => selectedIds.value.includes(u.id));
});

const canBatchEnable = computed(() => {
  return selectedIds.value.some(id => {
    const u = users.value.find(x => x.id === id);
    return u && u.status === "DISABLED";
  });
});

const canBatchDisable = computed(() => {
  return selectedIds.value.some(id => {
    const u = users.value.find(x => x.id === id);
    return u && u.status === "ACTIVE";
  });
});

function toggleSelectAll() {
  if (isAllVisibleSelected.value) {
    selectedIds.value = selectedIds.value.filter(id => !filteredUsers.value.find(u => u.id === id));
  } else {
    const newIds = filteredUsers.value.map(u => u.id).filter(id => !selectedIds.value.includes(id));
    selectedIds.value = [...selectedIds.value, ...newIds];
  }
}

function toggleSelection(id) {
  const idx = selectedIds.value.indexOf(id);
  if (idx >= 0) {
    selectedIds.value.splice(idx, 1);
  } else {
    selectedIds.value.push(id);
  }
}

function clearSelection() {
  selectedIds.value = [];
}

function clearFilters() {
  userQuery.value = "";
  roleFilter.value = "ALL";
  statusFilter.value = "ALL";
}

async function loadAdminData() {
  try {
    const [usersRes, overviewRes] = await Promise.all([
      http.get("/admin/users"),
      http.get("/admin/overview")
    ]);
    users.value = usersRes.data?.data ?? [];
    overview.value = overviewRes.data?.data ?? {};
  } catch (err) {
    console.error(err);
  }
}

async function toggleStatus(user) {
  const newStatus = user.status === "ACTIVE" ? "DISABLED" : "ACTIVE";
  try {
    await http.put(`/admin/users/${user.id}/status`, { status: newStatus });
    user.status = newStatus;
    showMessage("状态已更新", true);
  } catch (err) {
    showMessage("状态暂未更新，请稍后重试。", false);
  }
}

async function changeRole(user, newRole) {
  try {
    await http.put(`/admin/users/${user.id}/role`, { role: newRole });
    user.role = newRole;
    showMessage("角色已更新", true);
  } catch (err) {
    showMessage("角色暂未更新，请稍后重试。", false);
  }
}

async function batchUpdateStatus(newStatus) {
  try {
    await Promise.all(selectedIds.value.map((id) => http.put(`/admin/users/${id}/status`, { status: newStatus })));
    selectedIds.value.forEach(id => {
      const u = users.value.find(x => x.id === id);
      if (u) u.status = newStatus;
    });
    showMessage("批量更新成功", true);
    clearSelection();
  } catch (err) {
    showMessage("批量操作暂未完成，请稍后重试。", false);
  }
}

async function createUser() {
  try {
    const res = await http.post("/admin/users", form.value);
    users.value.push(res.data?.data ?? res.data);
    showMessage("账号创建成功", true);
    resetForm();
    await loadAdminData();
  } catch (err) {
    showMessage("账号暂未创建，请稍后重试。", false);
  }
}

function resetForm() {
  form.value = { username: "", password: "", displayName: "", role: "STAFF" };
}

function showMessage(msg, isSuccess) {
  message.value = msg;
  success.value = isSuccess;
  setTimeout(() => { message.value = ""; }, 3000);
}

onMounted(() => {
  loadAdminData();
});
</script>

<style scoped>
.admin-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: var(--spacing-lg);
}

.metric-card {
  display: grid;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  border: 1px solid var(--line);
  background: var(--bg-panel-muted);
  box-shadow: var(--shadow-xs);
  transition: all var(--transition-base);
}

.metric-card:hover {
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
  border-color: var(--line-strong);
}

.metric-card span {
  font-size: 11px;
  color: var(--ink-soft);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 700;
}

.metric-card strong {
  font-size: 24px;
  color: var(--ink-strong);
  line-height: 1;
}

.admin-toolbar {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  border: 1px solid var(--line);
  background: var(--bg-panel-muted);
}

.admin-toolbar input {
  flex: 1;
  min-width: 200px;
}

.admin-toolbar select {
  min-width: 120px;
}

.admin-batch-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  padding: var(--spacing-md) var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
  border-radius: var(--radius-md);
  border: 1px solid var(--accent);
  background: var(--accent-soft);
}

.admin-batch-bar strong {
  font-size: 13px;
  color: var(--ink-strong);
}

.table-wrap {
  overflow-x: auto;
  margin-bottom: var(--spacing-lg);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.data-table thead {
  background: var(--bg-panel-muted);
  border-bottom: 2px solid var(--line);
}

.data-table th {
  padding: var(--spacing-sm) var(--spacing-md);
  text-align: left;
  font-weight: 700;
  color: var(--ink-strong);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.data-table td {
  padding: var(--spacing-sm) var(--spacing-md);
  border-bottom: 1px solid var(--line);
  color: var(--ink);
}

.data-table tbody tr:hover {
  background: var(--bg-panel-muted);
}

.data-table td strong {
  color: var(--ink-strong);
  margin-right: 6px;
}

.data-table td .muted {
  font-size: 11px;
  color: var(--ink-soft);
}

.data-table select {
  font-size: 12px;
  padding: 4px 8px;
}

.role-picker {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

@media (max-width: 1180px) {
  .admin-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .admin-metrics {
    grid-template-columns: 1fr;
  }

  .admin-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .admin-toolbar input,
  .admin-toolbar select {
    width: 100%;
  }

  .admin-batch-bar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
