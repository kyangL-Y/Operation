<template>
  <div class="page-stack">
    <section class="workspace-card">
      <div class="section-header">
        <div class="section-header__copy">
          <p class="workspace-label">系统设置</p>
          <h3 class="section-title">系统设置</h3>
        </div>
        <div class="action-row">
          <button type="button" @click="saveSettings" :disabled="saving">
            {{ saving ? '保存中...' : '保存设置' }}
          </button>
          <button type="button" class="ghost-btn" @click="resetToDefault">恢复默认</button>
        </div>
      </div>

      <div class="settings-fact-strip">
        <article class="settings-fact-card">
          <span>负责内容</span>
          <strong>预测服务负责经营判断，问答服务负责处理建议</strong>
        </article>
        <article class="settings-fact-card">
          <span>当前目标</span>
          <strong>统一系统口径</strong>
        </article>
        <article class="settings-fact-card">
          <span>连接状态</span>
          <strong>{{ settings.mlEnabled ? "已启用" : "已停用" }}</strong>
        </article>
      </div>

      <p v-if="message" class="notice" :class="success ? 'notice--success' : 'notice--danger'">{{ message }}</p>

      <div class="settings-grid">
        <section class="settings-section">
          <h4>连接设置</h4>
          <div class="settings-list">
            <div class="setting-item">
              <div class="setting-info">
                <strong>预测与问答服务位置</strong>
              </div>
              <input type="text" v-model="settings.mlServiceUrl" placeholder="http://localhost:5000" />
            </div>
            <div class="setting-item">
              <div class="setting-info">
                <strong>启用预测服务</strong>
              </div>
              <label class="toggle">
                <input type="checkbox" v-model="settings.mlEnabled" />
                <span class="toggle-slider"></span>
              </label>
            </div>
          </div>
        </section>

        <section class="settings-section">
          <h4>经营预警线</h4>
          <div class="settings-list">
            <div class="setting-item">
              <div class="setting-info">
                <strong>入住率预警线</strong>
              </div>
              <input type="number" v-model.number="settings.occupancyThreshold" step="0.01" min="0" max="1" />
            </div>
            <div class="setting-item">
              <div class="setting-info">
                <strong>取消率预警线</strong>
              </div>
              <input type="number" v-model.number="settings.cancellationThreshold" step="0.01" min="0" max="1" />
            </div>
            <div class="setting-item">
              <div class="setting-info">
                <strong>差评率预警线</strong>
              </div>
              <input type="number" v-model.number="settings.negativeThreshold" step="0.01" min="0" max="1" />
            </div>
          </div>
        </section>

        <section class="settings-section">
          <h4>系统信息</h4>
          <div class="settings-list">
            <div class="setting-item">
              <div class="setting-info">
                <strong>系统名称</strong>
              </div>
              <input type="text" v-model="settings.systemName" placeholder="酒店运营支持系统" />
            </div>
            <div class="setting-item">
              <div class="setting-info">
                <strong>默认语言</strong>
                <p>系统界面显示语言</p>
              </div>
              <select v-model="settings.language">
                <option value="zh-CN">简体中文</option>
                <option value="en-US">英文</option>
              </select>
            </div>
          </div>
        </section>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import http from "../api/http";

const saving = ref(false);
const message = ref("");
const success = ref(false);

const defaultSettings = {
  mlServiceUrl: "http://localhost:5000",
  mlEnabled: true,
  occupancyThreshold: 0.7,
  cancellationThreshold: 0.15,
  negativeThreshold: 0.12,
  systemName: "酒店运营支持系统",
  language: "zh-CN"
};

const settings = reactive({ ...defaultSettings });

async function loadSettings() {
  try {
    const { data } = await http.get("/admin/settings");
    const cfg = data.data || {};
    settings.mlServiceUrl = cfg["ml.service.url"] || defaultSettings.mlServiceUrl;
    settings.mlEnabled = cfg["ml.enabled"] !== "false";
    settings.occupancyThreshold = parseFloat(cfg["alert.occupancy.threshold"]) || defaultSettings.occupancyThreshold;
    settings.cancellationThreshold = parseFloat(cfg["alert.cancellation.threshold"]) || defaultSettings.cancellationThreshold;
    settings.negativeThreshold = parseFloat(cfg["alert.negative.threshold"]) || defaultSettings.negativeThreshold;
    settings.systemName = cfg["system.name"] || defaultSettings.systemName;
    settings.language = cfg["system.language"] || defaultSettings.language;
  } catch {
    // 使用默认值
  }
}

async function saveSettings() {
  saving.value = true;
  message.value = "";
  try {
    const configMap = {
      "ml.service.url": settings.mlServiceUrl,
      "ml.enabled": String(settings.mlEnabled),
      "alert.occupancy.threshold": String(settings.occupancyThreshold),
      "alert.cancellation.threshold": String(settings.cancellationThreshold),
      "alert.negative.threshold": String(settings.negativeThreshold),
      "system.name": settings.systemName,
      "system.language": settings.language
    };

    for (const [key, value] of Object.entries(configMap)) {
      await http.put(`/admin/settings/${encodeURIComponent(key)}`, { value });
    }

    message.value = "设置保存成功，部分配置可能需要刷新页面生效。";
    success.value = true;
  } catch (err) {
    message.value = err.response?.data?.message || "暂未保存成功，请稍后重试。";
    success.value = false;
  } finally {
    saving.value = false;
  }
}

function resetToDefault() {
  Object.assign(settings, defaultSettings);
  message.value = "已恢复默认设置，请点击保存使其生效。";
  success.value = true;
}

onMounted(loadSettings);
</script>

<style scoped>
.settings-fact-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.settings-fact-card {
  display: grid;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  background: var(--bg-panel-muted);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-xs);
  transition: all var(--transition-base);
}

.settings-fact-card:hover {
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
  border-color: var(--line-strong);
}

.settings-fact-card span {
  font-size: 11px;
  color: var(--ink-soft);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 700;
}

.settings-fact-card strong {
  font-size: 13px;
  color: var(--ink-strong);
}

.settings-fact-card p {
  margin: 0;
  font-size: 12px;
  color: var(--ink-soft);
  line-height: 1.6;
}

.settings-grid {
  display: grid;
  gap: 16px;
}

.settings-section {
  padding: var(--spacing-xl);
  border-radius: var(--radius-md);
  background: var(--bg-panel-muted);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-xs);
}

.settings-section h4 {
  margin: 0 0 var(--spacing-md);
  font-size: 14px;
  color: var(--ink-strong);
  padding-bottom: var(--spacing-sm);
  border-bottom: 1px solid var(--line);
}

.settings-list {
  display: grid;
  gap: 12px;
}

.setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-lg);
  padding: var(--spacing-md);
  border-radius: var(--radius-sm);
  background: var(--bg-panel);
  border: 1px solid var(--line);
  transition: all var(--transition-base);
}

.setting-item:hover {
  border-color: var(--line-strong);
  box-shadow: var(--shadow-xs);
}

.setting-info {
  flex: 1;
  min-width: 0;
}

.setting-info strong {
  font-size: 13px;
  color: var(--ink-strong);
  display: block;
}

.setting-info p {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--ink-soft);
  line-height: 1.5;
}

.setting-item input[type="text"],
.setting-item input[type="number"],
.setting-item select {
  width: auto;
  min-width: 200px;
}

.toggle {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 26px;
  cursor: pointer;
}

.toggle input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  inset: 0;
  background: #d1d5db;
  border-radius: 26px;
  transition: 0.2s;
}

.toggle-slider::before {
  content: "";
  position: absolute;
  left: 3px;
  top: 3px;
  width: 20px;
  height: 20px;
  border-radius: 999px;
  background: #ffffff;
  transition: 0.2s;
}

.toggle input:checked + .toggle-slider {
  background: var(--accent);
}

.toggle input:checked + .toggle-slider::before {
  transform: translateX(22px);
}

.notice--success {
  color: var(--success);
  background: rgba(46, 150, 107, 0.1);
  border: 1px solid rgba(46, 150, 107, 0.2);
}

@media (max-width: 860px) {
  .settings-fact-strip {
    grid-template-columns: 1fr;
  }

  .setting-item {
    flex-direction: column;
    align-items: stretch;
  }

  .setting-item input,
  .setting-item select {
    width: 100%;
    min-width: auto;
  }
}
</style>
