<template>
  <div class="page-stack">
    <section class="workspace-card">
      <div class="section-header">
        <div class="section-header__copy">
          <p class="workspace-label">知识库</p>
          <h3 class="section-title">知识管理</h3>
        </div>
        <div class="action-row">
          <button type="button" class="ghost-btn" @click="loadDocs">刷新</button>
        </div>
      </div>

      <div class="knowledge-metrics">
        <div class="metric-card">
          <span>总文档</span>
          <strong>{{ docs.length }}</strong>
        </div>
        <div class="metric-card">
          <span>当前分类</span>
          <strong>{{ activeCatalogLabel }}</strong>
        </div>
        <div class="metric-card">
          <span>已选文档</span>
          <strong>{{ selectedDoc ? selectedDoc.title : "未选中" }}</strong>
        </div>
        <div class="metric-card">
          <span>当前模式</span>
          <strong>{{ isEditing ? "编辑" : title || content ? "录入" : "浏览" }}</strong>
        </div>
      </div>
    </section>

    <div class="surface-grid--equal">
      <section class="workspace-card">
        <div class="section-header">
          <div class="section-header__copy">
            <p class="workspace-label">文档录入</p>
            <h3 class="section-title">{{ isEditing ? "编辑文档" : "新增文档" }}</h3>
          </div>
          <div class="action-row">
            <button type="button" class="ghost-btn ghost-btn--compact" @click="fillTemplate">插入模板</button>
            <label class="ghost-btn ghost-btn--compact" for="knowledge-upload">导入文件</label>
            <button
              v-if="selectedDoc && !isEditing"
              type="button"
              class="ghost-btn ghost-btn--compact"
              @click="startEditSelectedDoc"
            >
              编辑当前
            </button>
          </div>
        </div>

        <form @submit.prevent="isEditing ? updateDoc() : addDoc()" class="form-stack">
          <div class="form-field">
            <label>标题</label>
            <input v-model.trim="title" placeholder="例如：客诉处理流程" required />
          </div>

          <div class="form-field">
            <label>内容</label>
            <textarea v-model="content" rows="12" placeholder="输入文档内容..." required></textarea>
          </div>

          <div class="form-field">
            <label>分类</label>
            <select v-model="category">
              <option value="SOP">处理流程</option>
              <option value="FAQ">常见问题</option>
              <option value="POLICY">管理规范</option>
              <option value="OTHER">其他</option>
            </select>
          </div>

          <div class="action-row">
            <button type="submit">{{ isEditing ? "保存修改" : "添加文档" }}</button>
            <button type="button" class="ghost-btn" @click="cancelEdit">{{ isEditing ? "取消编辑" : "清空" }}</button>
          </div>
        </form>

        <input
          id="knowledge-upload"
          type="file"
          accept=".txt,.md"
          multiple
          style="display: none"
          @change="handleFileUpload"
        />

        <p v-if="message" class="notice" :class="success ? 'notice--success' : 'notice--danger'">{{ message }}</p>
      </section>

      <section class="workspace-card">
        <div class="section-header">
          <div class="section-header__copy">
            <p class="workspace-label">文档列表</p>
            <h3 class="section-title">文档目录</h3>
          </div>
          <div class="action-row">
            <select v-model="catalogFilter" class="ghost-btn ghost-btn--compact">
              <option value="ALL">全部</option>
              <option value="SOP">处理流程</option>
              <option value="FAQ">常见问题</option>
              <option value="POLICY">管理规范</option>
              <option value="OTHER">其他</option>
            </select>
            <input v-model.trim="searchQuery" placeholder="搜索文档..." />
          </div>
        </div>

        <div class="doc-list">
          <div
            v-for="doc in filteredDocs"
            :key="doc.id"
            class="doc-item"
            :class="{ 'doc-item--active': selectedDoc && selectedDoc.id === doc.id }"
            @click="selectDoc(doc)"
          >
            <div class="doc-item__head">
              <strong>{{ doc.title }}</strong>
              <span class="badge badge--muted">{{ categoryLabel(doc.category) }}</span>
            </div>
            <p>{{ doc.content.substring(0, 80) }}...</p>
            <div class="doc-item__actions">
              <button type="button" class="ghost-btn ghost-btn--compact" @click.stop="startEditDoc(doc)">编辑</button>
              <button type="button" class="ghost-btn ghost-btn--compact" @click.stop="deleteDoc(doc.id)">删除</button>
            </div>
          </div>
        </div>
      </section>
    </div>

    <section v-if="selectedDoc" class="workspace-card">
      <div class="section-header">
        <div class="section-header__copy">
          <p class="workspace-label">文档阅读</p>
          <h3 class="section-title">{{ selectedDoc.title }}</h3>
        </div>
        <div class="action-row">
          <button type="button" class="ghost-btn" @click="selectedDoc = null">关闭</button>
        </div>
      </div>

      <div class="doc-reader">
        <div class="doc-reader__meta">
          <span class="badge">{{ categoryLabel(selectedDoc.category) }}</span>
          <span class="muted">#{{ selectedDoc.id }}</span>
        </div>
        <div class="doc-reader__content">
          {{ selectedDoc.content }}
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import http from "../api/http";

const docs = ref([]);
const selectedDoc = ref(null);
const title = ref("");
const content = ref("");
const category = ref("SOP");
const catalogFilter = ref("ALL");
const searchQuery = ref("");
const isEditing = ref(false);
const editingId = ref(null);
const message = ref("");
const success = ref(false);

const activeCatalogLabel = computed(() => {
  if (catalogFilter.value === "ALL") return "全部";
  return categoryLabel(catalogFilter.value);
});

const filteredDocs = computed(() => {
  let list = docs.value;
  if (catalogFilter.value !== "ALL") {
    list = list.filter(d => d.category === catalogFilter.value);
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase();
    list = list.filter(d => d.title.toLowerCase().includes(q) || d.content.toLowerCase().includes(q));
  }
  return list;
});

async function loadDocs() {
  try {
    const res = await http.get("/kb/docs");
    const normalized = normalizeDocs(res.data?.data ?? res.data ?? []);
    docs.value = normalized.length ? normalized : buildDemoDocs();
    if (!normalized.length) {
      showMessage("当前展示演示资料，连接后端后会自动切换为真实资料库。", false);
    }
  } catch (err) {
    console.error(err);
    docs.value = buildDemoDocs();
    showMessage("已加载备用资料，稍后可刷新同步最新资料库。", false);
  }
}

async function addDoc() {
  try {
    const res = await http.post("/kb/docs", {
      title: title.value,
      content: content.value,
    });
    docs.value.unshift(normalizeDoc(res.data?.data ?? res.data));
    showMessage("文档已添加", true);
    clearForm();
  } catch (err) {
    showMessage("暂未添加成功，请稍后重试。", false);
  }
}

async function updateDoc() {
  try {
    const res = await http.put(`/kb/docs/${editingId.value}`, {
      title: title.value,
      content: content.value,
    });
    const normalized = normalizeDoc(res.data?.data ?? res.data);
    const idx = docs.value.findIndex(d => d.id === editingId.value);
    if (idx >= 0) {
      docs.value[idx] = normalized;
    }
    if (selectedDoc.value && selectedDoc.value.id === editingId.value) {
      selectedDoc.value = normalized;
    }
    showMessage("文档已更新", true);
    cancelEdit();
  } catch (err) {
    showMessage("暂未更新成功，请稍后重试。", false);
  }
}

async function deleteDoc(id) {
  if (!confirm("确认删除此文档？")) return;
  try {
    await http.delete(`/kb/docs/${id}`);
    docs.value = docs.value.filter(d => d.id !== id);
    if (selectedDoc.value && selectedDoc.value.id === id) {
      selectedDoc.value = null;
    }
    showMessage("文档已删除", true);
  } catch (err) {
    showMessage("暂未删除成功，请稍后重试。", false);
  }
}

function selectDoc(doc) {
  selectedDoc.value = doc;
}

function normalizeDocs(list) {
  return Array.isArray(list) ? list.map(normalizeDoc) : [];
}

function normalizeDoc(doc) {
  const raw = doc || {};
  return {
    ...raw,
    category: raw.category || inferCategory(raw.title, raw.content)
  };
}

function inferCategory(title = "", content = "") {
  const text = `${title} ${content}`.toLowerCase();
  if (text.includes("sop") || text.includes("流程") || text.includes("处置")) return "SOP";
  if (text.includes("faq") || text.includes("常见") || text.includes("问答")) return "FAQ";
  if (text.includes("政策") || text.includes("制度") || text.includes("规范")) return "POLICY";
  return "OTHER";
}

function categoryLabel(value) {
  const labels = {
    SOP: "处理流程",
    FAQ: "常见问题",
    POLICY: "管理规范",
    OTHER: "其他"
  };
  return labels[value] || value || "其他";
}

function startEditDoc(doc) {
  title.value = doc.title;
  content.value = doc.content;
  category.value = doc.category;
  isEditing.value = true;
  editingId.value = doc.id;
}

function startEditSelectedDoc() {
  if (selectedDoc.value) {
    startEditDoc(selectedDoc.value);
  }
}

function cancelEdit() {
  clearForm();
  isEditing.value = false;
  editingId.value = null;
}

function clearForm() {
  title.value = "";
  content.value = "";
  category.value = "SOP";
}

function fillTemplate() {
  title.value = "示例文档标题";
  content.value = "## 背景\n\n## 流程\n\n## 注意事项\n";
}

function buildDemoDocs() {
  return normalizeDocs([
    {
      id: 801,
      title: "投诉处理流程",
      category: "SOP",
      content: "## 背景\n客诉进入值班台后，前台需要在 5 分钟内响应。\n## 流程\n1. 记录客人姓名、房号、问题类型和情绪等级。\n2. 前台主管判断是否需要客房、工程或收益协同。\n3. 重大投诉同步值班经理并在 30 分钟内给出补救方案。\n## 注意事项\n所有补救动作需要写入交接记录。"
    },
    {
      id: 802,
      title: "高取消率渠道复盘说明",
      category: "FAQ",
      content: "当取消率高于 10% 时，收益经理优先检查 OTA 活动价、预付比例、担保政策和团队订单变更。若连续两天高于预警线，应收紧低价房型并提醒前台确认高风险预抵订单。"
    },
    {
      id: 803,
      title: "房态协同交接规范",
      category: "POLICY",
      content: "前台、客房和值班经理在高入住日需要每 2 小时同步一次房态。VIP、团队领队房、已到店等待入住和亲子房优先清扫。若出现售出房量与可用房量冲突，必须暂停继续放房。"
    }
  ]);
}

function handleFileUpload(event) {
  const files = event.target.files;
  if (!files || files.length === 0) return;

  Array.from(files).forEach(file => {
    const reader = new FileReader();
    reader.onload = e => {
      const text = e.target.result;
      title.value = file.name.replace(/\.(txt|md)$/, "");
      content.value = text;
    };
    reader.readAsText(file);
  });
}

function showMessage(msg, isSuccess) {
  message.value = msg;
  success.value = isSuccess;
  setTimeout(() => { message.value = ""; }, 3000);
}

onMounted(() => {
  loadDocs();
});
</script>

<style scoped>
.knowledge-metrics {
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
  font-size: 16px;
  color: var(--ink-strong);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-list {
  display: grid;
  gap: 8px;
  max-height: 600px;
  overflow-y: auto;
}

.doc-item {
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  border: 1px solid var(--line);
  background: var(--bg-panel-muted);
  cursor: pointer;
  transition: all var(--transition-base);
  display: grid;
  gap: var(--spacing-sm);
}

.doc-item:hover {
  border-color: var(--line-strong);
  box-shadow: var(--shadow-xs);
}

.doc-item--active {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.doc-item__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-sm);
}

.doc-item__head strong {
  font-size: 13px;
  color: var(--ink-strong);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-item p {
  margin: 0;
  font-size: 12px;
  color: var(--ink-soft);
  line-height: 1.6;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-item__actions {
  display: flex;
  gap: var(--spacing-sm);
}

.doc-reader {
  display: grid;
  gap: var(--spacing-md);
}

.doc-reader__meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.doc-reader__content {
  padding: var(--spacing-lg);
  border-radius: var(--radius-md);
  border: 1px solid var(--line);
  background: var(--bg-panel-muted);
  font-size: 13px;
  color: var(--ink);
  line-height: 1.8;
  white-space: pre-wrap;
  word-wrap: break-word;
}

@media (max-width: 1180px) {
  .knowledge-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .knowledge-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
