<template>
  <div class="page-stack">
    <section class="workspace-card">
      <div class="section-header">
        <div class="section-header__copy">
          <p class="workspace-label">数据管理</p>
          <h3 class="section-title">运营数据</h3>
        </div>
        <div class="action-row">
          <button type="button" @click="showForm = true" v-if="!showForm">新增数据</button>
          <button type="button" class="ghost-btn" @click="loadData">刷新</button>
        </div>
      </div>

      <div class="data-metrics">
        <div class="metric-card">
          <span>总记录</span>
          <strong>{{ dataList.length }}</strong>
        </div>
        <div class="metric-card">
          <span>当前模式</span>
          <strong>{{ showForm ? (editingId ? "编辑" : "新增") : "浏览" }}</strong>
        </div>
        <div class="metric-card">
          <span>筛选区间</span>
          <strong>{{ filterStart || filterEnd ? "已筛选" : "全部" }}</strong>
        </div>
        <div class="metric-card">
          <span>筛选结果</span>
          <strong>{{ filteredData.length }}</strong>
        </div>
      </div>
    </section>

    <section v-if="showForm" class="workspace-card">
      <div class="section-header">
        <div class="section-header__copy">
          <p class="workspace-label">{{ editingId ? '编辑数据' : '新增数据' }}</p>
          <h3 class="section-title">{{ editingId ? '编辑数据' : '新增数据' }}</h3>
        </div>
        <div class="action-row">
          <button type="button" class="ghost-btn" @click="cancelEdit">取消</button>
        </div>
      </div>

      <form @submit.prevent="saveData" class="form-stack">
        <div class="form-row">
          <div class="form-field">
            <label>业务日期</label>
            <input type="date" v-model="form.bizDate" required />
          </div>
          <div class="form-field">
            <label>入住率 (0-1)</label>
            <input type="number" v-model.number="form.occupancyRate" step="0.01" min="0" max="1" required />
          </div>
          <div class="form-field">
            <label>日营收 (元)</label>
            <input type="number" v-model.number="form.revenue" step="0.01" min="0" required />
          </div>
        </div>

        <div class="form-row">
          <div class="form-field">
            <label>取消订单数</label>
            <input type="number" v-model.number="form.cancelCount" min="0" required />
          </div>
          <div class="form-field">
            <label>总订单数</label>
            <input type="number" v-model.number="form.totalOrders" min="0" required />
          </div>
          <div class="form-field">
            <label>平均房价 (元)</label>
            <input type="number" v-model.number="form.avgRoomPrice" step="0.01" min="0" required />
          </div>
        </div>

        <div class="form-row">
          <div class="form-field">
            <label>可用房间数</label>
            <input type="number" v-model.number="form.availableRooms" min="0" required />
          </div>
          <div class="form-field">
            <label>已售房间数</label>
            <input type="number" v-model.number="form.soldRooms" min="0" required />
          </div>
          <div class="form-field">
            <label>备注</label>
            <input type="text" v-model="form.notes" placeholder="可选" />
          </div>
        </div>

        <div class="action-row">
          <button type="submit">{{ editingId ? '保存修改' : '添加数据' }}</button>
          <button type="button" class="ghost-btn" @click="cancelEdit">取消</button>
        </div>
      </form>

      <p v-if="message" class="notice" :class="success ? 'notice--success' : 'notice--danger'">{{ message }}</p>
    </section>

    <section class="workspace-card">
      <div class="section-header">
        <div class="section-header__copy">
          <p class="workspace-label">数据列表</p>
          <h3 class="section-title">历史数据</h3>
        </div>
      </div>

      <div class="filter-bar">
        <div class="form-field">
          <label>开始日期</label>
          <input type="date" v-model="filterStart" />
        </div>
        <div class="form-field">
          <label>结束日期</label>
          <input type="date" v-model="filterEnd" />
        </div>
        <button type="button" class="ghost-btn" @click="clearFilters">清空筛选</button>
      </div>

      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>日期</th>
              <th>入住率</th>
              <th>营收</th>
              <th>取消/总订单</th>
              <th>房价</th>
              <th>房间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in filteredData" :key="item.id">
              <td><strong>{{ item.bizDate }}</strong></td>
              <td>{{ (item.occupancyRate * 100).toFixed(1) }}%</td>
              <td>¥{{ item.revenue.toLocaleString() }}</td>
              <td>{{ item.cancelCount }} / {{ item.totalOrders }}</td>
              <td>¥{{ item.avgRoomPrice.toFixed(0) }}</td>
              <td>{{ item.soldRooms }} / {{ item.availableRooms }}</td>
              <td>
                <div class="action-row">
                  <button type="button" class="ghost-btn ghost-btn--compact" @click="editData(item)">编辑</button>
                  <button type="button" class="ghost-btn ghost-btn--compact" @click="deleteData(item.id)">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import http from "../api/http";

const dataList = ref([]);
const showForm = ref(false);
const editingId = ref(null);
const filterStart = ref("");
const filterEnd = ref("");
const message = ref("");
const success = ref(false);

const form = ref({
  bizDate: "",
  occupancyRate: 0,
  revenue: 0,
  cancelCount: 0,
  totalOrders: 0,
  avgRoomPrice: 0,
  availableRooms: 0,
  soldRooms: 0,
  notes: ""
});

const filteredData = computed(() => {
  let list = dataList.value;
  if (filterStart.value) {
    list = list.filter(item => item.bizDate >= filterStart.value);
  }
  if (filterEnd.value) {
    list = list.filter(item => item.bizDate <= filterEnd.value);
  }
  return list.sort((a, b) => b.bizDate.localeCompare(a.bizDate));
});

async function loadData() {
  try {
    const res = await http.get("/ops/metrics");
    const normalized = normalizeMetrics(res.data?.data ?? []);
    dataList.value = normalized.length ? normalized : buildDemoMetrics();
    if (!normalized.length) {
      showMessage("当前展示演示运营数据，连接后端后会自动切换为真实数据。", false);
    }
  } catch (err) {
    console.error(err);
    dataList.value = buildDemoMetrics();
    showMessage("已加载备用运营数据，稍后可刷新同步最新记录。", false);
  }
}

async function saveData() {
  try {
    if (editingId.value) {
      await http.put(`/ops/metrics/${editingId.value}`, toMetricPayload(form.value));
      const idx = dataList.value.findIndex((d) => d.id === editingId.value);
      if (idx >= 0) {
        dataList.value[idx] = normalizeMetric({ ...toMetricPayload(form.value), id: editingId.value });
      }
      showMessage("数据已更新", true);
    } else {
      const res = await http.post("/ops/metrics", toMetricPayload(form.value));
      dataList.value.unshift(normalizeMetric(res.data?.data ?? res.data));
      showMessage("数据已添加", true);
    }
    cancelEdit();
  } catch (err) {
    showMessage("暂未保存成功，请稍后重试。", false);
  }
}

function editData(item) {
  form.value = { ...item };
  editingId.value = item.id;
  showForm.value = true;
}

async function deleteData(id) {
  if (!confirm("确认删除此数据？")) return;
  try {
    await http.delete(`/ops/metrics/${id}`);
    dataList.value = dataList.value.filter(d => d.id !== id);
    showMessage("数据已删除", true);
  } catch (err) {
    showMessage("暂未删除成功，请稍后重试。", false);
  }
}

function cancelEdit() {
  showForm.value = false;
  editingId.value = null;
  form.value = {
    bizDate: "",
    occupancyRate: 0,
    revenue: 0,
    cancelCount: 0,
    totalOrders: 0,
    avgRoomPrice: 0,
    availableRooms: 0,
    soldRooms: 0,
    notes: ""
  };
}

function clearFilters() {
  filterStart.value = "";
  filterEnd.value = "";
}

function showMessage(msg, isSuccess) {
  message.value = msg;
  success.value = isSuccess;
  setTimeout(() => { message.value = ""; }, 3000);
}

onMounted(() => {
  loadData();
});

function normalizeMetrics(list) {
  return Array.isArray(list) ? list.map(normalizeMetric) : [];
}

function normalizeMetric(item) {
  const metric = item || {};
  const occupancyRate = Number(metric.occupancyRate ?? 0);
  const availableRooms = 120;
  const soldRooms = Math.round(occupancyRate * availableRooms);
  const cancellationRate = Number(metric.cancellationRate ?? 0);
  const totalOrders = Math.max(Math.round(soldRooms * 1.18), soldRooms);
  const cancelCount = Math.round(totalOrders * cancellationRate);
  const revenue = Number(metric.revenue ?? 0);
  return {
    id: metric.id,
    bizDate: metric.bizDate,
    occupancyRate,
    revenue,
    cancelCount,
    totalOrders,
    avgRoomPrice: soldRooms > 0 ? revenue / soldRooms : 0,
    availableRooms,
    soldRooms,
    notes: metric.notes || "",
    reviewScore: Number(metric.reviewScore ?? 0),
    negativeRate: Number(metric.negativeRate ?? 0),
    cancellationRate
  };
}

function toMetricPayload(raw) {
  const occupancyRate = Number(raw.occupancyRate || 0);
  const totalOrders = Number(raw.totalOrders || 0);
  const cancelCount = Number(raw.cancelCount || 0);
  const cancellationRate = totalOrders > 0 ? cancelCount / totalOrders : 0;
  return {
    bizDate: raw.bizDate,
    occupancyRate,
    revenue: Number(raw.revenue || 0),
    cancellationRate,
    reviewScore: 4.5,
    negativeRate: 0.06
  };
}

function buildDemoMetrics() {
  return normalizeMetrics([
    { id: 901, bizDate: "2026-03-25", occupancyRate: 0.82, revenue: 58000, cancellationRate: 0.06, notes: "演示数据" },
    { id: 902, bizDate: "2026-03-24", occupancyRate: 0.78, revenue: 52000, cancellationRate: 0.08, notes: "演示数据" },
    { id: 903, bizDate: "2026-03-23", occupancyRate: 0.85, revenue: 62000, cancellationRate: 0.05, notes: "演示数据" },
    { id: 904, bizDate: "2026-03-22", occupancyRate: 0.72, revenue: 48000, cancellationRate: 0.10, notes: "演示数据" },
    { id: 905, bizDate: "2026-03-21", occupancyRate: 0.68, revenue: 45000, cancellationRate: 0.12, notes: "演示数据" }
  ]);
}
</script>

<style scoped>
.data-metrics {
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

.filter-bar {
  display: flex;
  align-items: flex-end;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  background: var(--bg-panel-muted);
  border: 1px solid var(--line);
  margin-bottom: var(--spacing-lg);
}

.filter-bar .form-field {
  min-width: 140px;
}

.table-wrap {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  text-align: left;
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: 11px;
  font-weight: 700;
  color: var(--ink-soft);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  border-bottom: 1px solid var(--line);
  background: var(--bg-panel-muted);
}

.data-table td {
  padding: var(--spacing-md);
  font-size: 13px;
  color: var(--ink);
  border-bottom: 1px solid var(--line);
}

.data-table tbody tr:hover {
  background: var(--bg-panel-muted);
}

.data-table td strong {
  color: var(--ink-strong);
}

.muted {
  color: var(--ink-soft);
  font-size: 12px;
}

.notice {
  margin-top: var(--spacing-lg);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  font-size: 13px;
}

.notice--success {
  color: var(--success);
  background: rgba(46, 150, 107, 0.1);
  border: 1px solid rgba(46, 150, 107, 0.2);
}

.notice--danger {
  color: var(--danger);
  background: rgba(220, 53, 69, 0.1);
  border: 1px solid rgba(220, 53, 69, 0.2);
}

@media (max-width: 860px) {
  .data-metrics,
  .form-row {
    grid-template-columns: 1fr;
  }

  .filter-bar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
