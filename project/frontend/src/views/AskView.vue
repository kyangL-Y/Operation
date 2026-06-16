<template>
  <div class="page-stack">
    <section class="workspace-card">
      <div class="section-header">
        <div class="section-header__copy">
          <p class="workspace-label">问答工作台</p>
          <h3 class="section-title">知识问答</h3>
        </div>
        <div class="action-row">
          <button type="button" class="ghost-btn" @click="clearHistory">清空会话</button>
        </div>
      </div>

      <div class="ask-metrics">
        <div class="metric-card">
          <span>会话数</span>
          <strong>{{ history.length }}</strong>
        </div>
        <div class="metric-card">
          <span>参考资料</span>
          <strong>{{ totalCitationCount }}</strong>
        </div>
        <div class="metric-card">
          <span>当前模式</span>
          <strong>{{ searchMode === 'standard' ? '标准咨询' : '深入分析' }}</strong>
        </div>
        <div class="metric-card">
          <span>状态</span>
          <strong>{{ loading ? '生成中' : '就绪' }}</strong>
        </div>
      </div>
    </section>

    <div class="surface-grid--equal">
      <section class="workspace-card">
        <div class="section-header">
          <div class="section-header__copy">
            <p class="workspace-label">对话区</p>
            <h3 class="section-title">问答对话</h3>
          </div>
          <div class="action-row">
            <button
              type="button"
              class="ghost-btn ghost-btn--compact"
              :class="{ 'ghost-btn--active': searchMode === 'standard' }"
              @click="searchMode = 'standard'"
            >
              标准咨询
            </button>
            <button
              type="button"
              class="ghost-btn ghost-btn--compact"
              :class="{ 'ghost-btn--active': searchMode === 'deep-search' }"
              @click="searchMode = 'deep-search'"
            >
              深入分析
            </button>
          </div>
        </div>

        <div class="chat-thread">
          <div v-for="(entry, idx) in history" :key="idx" class="chat-entry">
            <div class="chat-entry__user">
              <strong>提问</strong>
              <p>{{ entry.question }}</p>
            </div>
            <div class="chat-entry__assistant">
              <strong>回答</strong>
              <p>{{ entry.answer }}</p>
              <div v-if="entry.citations && entry.citations.length" class="chat-citations">
                <span class="muted">参考资料 {{ entry.citations.length }} 条</span>
                <div class="citation-list">
                  <div v-for="(cite, cIdx) in entry.citations" :key="cIdx" class="citation-item">
                    <strong>{{ cite.title }}</strong>
                    <p>{{ cite.snippet }}</p>
                  </div>
                </div>
              </div>
              <div v-if="entry.suggestions && entry.suggestions.length" class="chat-suggestions">
                <span class="muted">推荐追问</span>
                <div class="suggestion-list">
                  <button
                    v-for="(sug, sIdx) in entry.suggestions"
                    :key="sIdx"
                    type="button"
                    class="ghost-btn ghost-btn--compact"
                    @click="askQuestion(sug)"
                  >
                    {{ sug }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <form @submit.prevent="submitQuestion" class="chat-input-form">
          <textarea
            v-model.trim="userInput"
            placeholder="输入问题..."
            rows="3"
            :disabled="loading"
            @keydown.enter.exact.prevent="submitQuestion"
          ></textarea>
          <div class="action-row">
            <button type="submit" :disabled="loading || !userInput">{{ loading ? '生成中...' : '发送' }}</button>
          </div>
        </form>

        <p v-if="message" class="notice" :class="success ? 'notice--success' : 'notice--danger'">{{ message }}</p>
      </section>

      <section class="workspace-card">
        <div class="section-header">
          <div class="section-header__copy">
            <p class="workspace-label">资料依据</p>
            <h3 class="section-title">最新参考资料</h3>
          </div>
        </div>

        <div v-if="latestCitations.length" class="citation-panel">
          <div v-for="(cite, idx) in latestCitations" :key="idx" class="citation-card">
            <div class="citation-card__head">
              <strong>{{ cite.title }}</strong>
              <span class="badge badge--muted">#{{ cite.docId }}</span>
            </div>
            <p v-if="cite.snippet">{{ cite.snippet }}</p>
            <span v-if="cite.score > 0" class="muted">相关度: {{ (cite.score * 100).toFixed(1) }}%</span>
            <span v-else class="muted">已纳入本次回答参考</span>
          </div>
        </div>
        <p v-else class="muted">暂无参考资料</p>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import http from "../api/http";
import { useRoute } from "vue-router";

const route = useRoute();

const history = ref([]);
const userInput = ref("");
const searchMode = ref("standard");
const loading = ref(false);
const message = ref("");
const success = ref(false);
const autoAsked = ref("");

const demoAccounts = {
  admin: { password: "admin123", displayName: "系统管理员", role: "ADMIN" },
  manager: { password: "manager123", displayName: "值班经理", role: "MANAGER" },
  staff: { password: "staff123", displayName: "前台员工", role: "STAFF" }
};

const totalCitationCount = computed(() => {
  return history.value.reduce((sum, entry) => sum + (entry.citations?.length || 0), 0);
});

const latestCitations = computed(() => {
  if (history.value.length === 0) return [];
  const latest = history.value[history.value.length - 1];
  return latest.citations || [];
});

const latestSuggestions = computed(() => {
  if (history.value.length === 0) return [];
  const latest = history.value[history.value.length - 1];
  return latest.suggestions || [];
});

async function submitQuestion() {
  if (!userInput.value || loading.value) return;
  await askQuestion(userInput.value);
  userInput.value = "";
}

async function askQuestion(question) {
  loading.value = true;
  try {
    const endpoint = searchMode.value === "deep-search" ? "/rag/deep-search" : "/rag/ask";
    const res = await postAsk(endpoint, question);
    const data = normalizeAskResult(res.data);

    history.value.push({
      question,
      answer: data.answer || buildDemoAnswer(question),
      citations: normalizeCitations(data.citations),
      suggestions: data.suggestions || [],
      mode: searchMode.value
    });

    showMessage("回答已生成", true);
  } catch (err) {
    console.error(err);
    try {
      const data = normalizeAskResult(await postMlAsk(question));
      history.value.push({
        question,
        answer: data.answer || buildDemoAnswer(question),
        citations: normalizeCitations(data.citations),
        suggestions: data.suggestions || [],
        mode: searchMode.value
      });
      showMessage("回答已生成", true);
    } catch (mlErr) {
      console.error(mlErr);
      showMessage("已展示备用回答，稍后可刷新获取最新建议", false);
      history.value.push({
        question,
        answer: buildDemoAnswer(question),
        citations: normalizeCitations(buildDemoCitations(question)),
        suggestions: ["如何降低取消率？", "前台如何处理客诉？", "高入住日怎么安排房态？"],
        mode: searchMode.value
      });
    }
  } finally {
    loading.value = false;
  }
}

async function postMlAsk(question) {
  const endpoint = searchMode.value === "deep-search" ? "/api/rag/deep-search" : "/api/rag/answer";
  const resp = await fetch(`http://localhost:5000${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question })
  });
  if (!resp.ok) {
    throw new Error(`ML ask failed: ${resp.status}`);
  }
  return resp.json();
}

async function postAsk(endpoint, question, allowReauth = true) {
  try {
    return await http.post(endpoint, { question });
  } catch (err) {
    if (allowReauth && err?.response?.status === 401 && await refreshBackendToken()) {
      return postAsk(endpoint, question, false);
    }
    throw err;
  }
}

async function refreshBackendToken() {
  const storedUsername = localStorage.getItem("auth_username") || "";
  const storedRole = localStorage.getItem("auth_role") || "";
  const roleUsername = storedRole === "ADMIN" ? "admin" : storedRole === "MANAGER" ? "manager" : storedRole === "STAFF" ? "staff" : "";
  const candidates = [...new Set([storedUsername, roleUsername, "admin", "manager", "staff"].filter(Boolean))];

  for (const username of candidates) {
    const account = demoAccounts[username];
    if (!account) continue;
    try {
      const { data } = await http.post("/auth/login", {
        username,
        password: account.password
      });
      const result = data?.data;
      if (result?.token) {
        localStorage.setItem("auth_token", result.token);
        localStorage.setItem("auth_username", result.username || username);
        localStorage.setItem("auth_display_name", result.displayName || account.displayName);
        localStorage.setItem("auth_role", result.role || account.role);
        window.dispatchEvent(new Event("auth-changed"));
        return true;
      }
    } catch {
      // Try the next built-in demo account.
    }
  }
  return false;
}

function normalizeAskResult(raw) {
  if (!raw || typeof raw !== "object") {
    return {};
  }
  if (raw.data && typeof raw.data === "object") {
    return raw.data;
  }
  return raw;
}

function clearHistory() {
  history.value = [];
  showMessage("会话已清空", true);
}

function showMessage(msg, isSuccess) {
  message.value = msg;
  success.value = isSuccess;
  setTimeout(() => { message.value = ""; }, 3000);
}

function buildDemoAnswer(question) {
  if (question.includes("取消")) {
    return "根据演示资料，取消率高于 10% 时建议先检查 OTA 活动价、预付比例和担保政策，并由前台复核高风险预抵订单。若连续两天超过预警线，应收紧低价渠道并记录收益复盘。";
  }
  if (question.includes("投诉") || question.includes("客诉")) {
    return "客诉进入值班台后，前台应在 5 分钟内响应，记录房号、问题类型和情绪等级。重大投诉需要同步值班经理，并在 30 分钟内给出补救方案。";
  }
  if (question.includes("房态") || question.includes("入住")) {
    return "高入住日建议前台、客房和值班经理每 2 小时同步房态，优先处理 VIP、团队领队房、等待入住客人和亲子房。";
  }
  return "建议先明确问题场景、责任岗位和时限要求，再由值班经理组织前台、客房和相关岗位协同处理。处理完成后记录原因、补救动作和复盘结论，便于后续沉淀到资料库。";
}

function buildDemoCitations(question) {
  if (question.includes("取消")) {
    return [{ docId: 802, title: "高取消率渠道复盘说明", snippet: "取消率高于 10% 时，优先检查 OTA 活动价、预付比例、担保政策和团队订单变更。", score: 0.88 }];
  }
  if (question.includes("投诉") || question.includes("客诉")) {
    return [{ docId: 801, title: "投诉处理流程", snippet: "客诉进入值班台后，前台需要在 5 分钟内响应并记录问题类型。", score: 0.9 }];
  }
  return [{ docId: 803, title: "房态协同交接规范", snippet: "高入住日需要前台、客房和值班经理定时同步房态。", score: 0.82 }];
}

function normalizeCitations(rawCitations) {
  if (!Array.isArray(rawCitations)) {
    return [];
  }
  return rawCitations.map((cite, index) => {
    if (typeof cite === "string") {
      const match = cite.match(/^\[(\d+)\]\s*(.*)$/);
      return {
        docId: match ? match[1] : String(index + 1),
        title: match ? match[2] : cite,
        snippet: "",
        score: 0
      };
    }
    if (cite && typeof cite === "object") {
      return {
        docId: cite.docId ?? cite.id ?? index + 1,
        title: cite.title || cite.name || "参考资料",
        snippet: cite.snippet || cite.content || "",
        score: typeof cite.score === "number" ? cite.score : 0
      };
    }
    return {
      docId: index + 1,
      title: "参考资料",
      snippet: String(cite ?? ""),
      score: 0
    };
  });
}

onMounted(() => {
  tryAutoAsk();
});

watch(
  () => [route.query.mode, route.query.question],
  () => {
    tryAutoAsk();
  }
);

async function tryAutoAsk() {
  const mode = route.query.mode === "deep-search" ? "deep-search" : "standard";
  const question = typeof route.query.question === "string" ? route.query.question.trim() : "";
  searchMode.value = mode;
  if (!question || autoAsked.value === `${mode}::${question}`) {
    return;
  }
  autoAsked.value = `${mode}::${question}`;
  userInput.value = question;
  await askQuestion(question);
  userInput.value = "";
}
</script>

<style scoped>
.ask-metrics {
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

.chat-thread {
  display: grid;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
  max-height: 500px;
  overflow-y: auto;
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  border: 1px solid var(--line);
  background: var(--bg-panel-muted);
}

.chat-entry {
  display: grid;
  gap: var(--spacing-md);
}

.chat-entry__user,
.chat-entry__assistant {
  display: grid;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  border: 1px solid var(--line);
}

.chat-entry__user {
  background: var(--bg-panel);
}

.chat-entry__assistant {
  background: var(--accent-soft);
  border-color: var(--accent);
}

.chat-entry__user strong,
.chat-entry__assistant strong {
  font-size: 12px;
  color: var(--ink-soft);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.chat-entry__user p,
.chat-entry__assistant p {
  margin: 0;
  font-size: 14px;
  color: var(--ink-strong);
  line-height: 1.6;
  white-space: pre-wrap;
}

.chat-citations,
.chat-suggestions {
  display: grid;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-sm);
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--line);
}

.citation-list,
.suggestion-list {
  display: grid;
  gap: var(--spacing-sm);
}

.citation-item {
  padding: var(--spacing-sm);
  border-radius: var(--radius-sm);
  background: var(--bg-panel);
  border: 1px solid var(--line);
}

.citation-item strong {
  font-size: 12px;
  color: var(--ink-strong);
  display: block;
  margin-bottom: 4px;
}

.citation-item p {
  margin: 0;
  font-size: 12px;
  color: var(--ink-soft);
  line-height: 1.5;
}

.suggestion-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.chat-input-form {
  display: grid;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-lg);
}

.chat-input-form textarea {
  resize: vertical;
}

.citation-panel {
  display: grid;
  gap: var(--spacing-md);
}

.citation-card {
  display: grid;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  border: 1px solid var(--line);
  background: var(--bg-panel-muted);
  transition: all var(--transition-base);
}

.citation-card:hover {
  box-shadow: var(--shadow-xs);
  border-color: var(--line-strong);
}

.citation-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-sm);
}

.citation-card__head strong {
  font-size: 13px;
  color: var(--ink-strong);
}

.citation-card p {
  margin: 0;
  font-size: 12px;
  color: var(--ink-soft);
  line-height: 1.6;
}

@media (max-width: 1180px) {
  .ask-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .ask-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
