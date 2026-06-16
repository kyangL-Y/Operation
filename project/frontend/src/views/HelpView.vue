<template>
  <div class="page-stack">
    <section class="workspace-card">
      <div class="section-header__copy">
        <p class="workspace-label">帮助中心</p>
        <h3 class="section-title">帮助文档</h3>
      </div>
    </section>

    <section class="workspace-card">
      <div class="section-header__copy">
        <p class="workspace-label">系统口径</p>
        <h3 class="section-title">系统口径说明</h3>
      </div>
      <div class="help-facts-grid">
        <div class="help-fact-item">
          <span>系统闭环</span>
          <strong>数据 → 判断 → 建议 → 复盘</strong>
        </div>
        <div class="help-fact-item">
          <span>预测内容</span>
          <strong>入住率、营收、订单取消风险</strong>
        </div>
        <div class="help-fact-item">
          <span>使用口径</span>
          <strong>以经营数据和历史表现为依据</strong>
        </div>
        <div class="help-fact-item">
          <span>知识问答职责</span>
          <strong>处理建议与参考资料</strong>
        </div>
      </div>
    </section>

    <div class="surface-grid--equal">
      <section class="workspace-card">
        <div class="section-header__copy">
          <p class="workspace-label">功能说明</p>
          <h3 class="panel-title">功能说明</h3>
        </div>
        <div class="help-module-list">
          <div v-for="mod in modules" :key="mod.name" class="help-module">
            <div class="help-module__head">
              <span class="help-module__badge">{{ mod.badge }}</span>
              <strong>{{ mod.name }}</strong>
            </div>
            <p>{{ mod.desc }}</p>
            <ul>
              <li v-for="tip in mod.tips" :key="tip">{{ tip }}</li>
            </ul>
          </div>
        </div>
      </section>

      <section class="workspace-card">
        <div class="section-header__copy">
          <p class="workspace-label">常见问题</p>
          <h3 class="panel-title">常见问题</h3>
        </div>
        <div class="faq-list">
          <div v-for="(faq, idx) in faqs" :key="idx" class="faq-item">
            <div class="faq-question" @click="toggleFaq(idx)">
              <strong>Q: {{ faq.q }}</strong>
              <span class="faq-toggle">{{ openFaq === idx ? '▲' : '▼' }}</span>
            </div>
            <div v-if="openFaq === idx" class="faq-answer">
              <p>A: {{ faq.a }}</p>
            </div>
          </div>
        </div>
      </section>
    </div>

    <section class="workspace-card">
      <div class="section-header__copy">
        <p class="workspace-label">快速上手</p>
        <h3 class="panel-title">快速上手流程</h3>
      </div>
      <div class="quickstart-steps">
        <div v-for="(step, idx) in steps" :key="idx" class="quickstart-step">
          <div class="step-num">{{ idx + 1 }}</div>
          <div class="step-content">
            <strong>{{ step.title }}</strong>
            <p>{{ step.desc }}</p>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref } from "vue";

const openFaq = ref(null);

function toggleFaq(idx) {
  openFaq.value = openFaq.value === idx ? null : idx;
}

const modules = [
  {
    badge: "01",
    name: "经营总览",
    desc: "展示运营指标、判断结果、处理建议与原因说明，是系统的首页工作台。",
    tips: ["点击「刷新首页」获取最新数据", "查看判断依据确认当前判断口径", "先看判断依据表，再进入问答页继续追问"]
  },
  {
    badge: "02",
    name: "问答工作台",
    desc: "面向业务问题的咨询区，可用于处理流程查询、客诉处理与运营建议补充。",
    tips: ["输入具体业务问题更容易得到可执行回答", "回答中的参考资料可追溯到资料库文档", "问答页负责解释和建议，不直接生成入住率或营收数值"]
  },
  {
    badge: "03",
    name: "知识库",
    desc: "管理处理流程、处置方案等资料文档，为问答工作台提供依据。",
    tips: ["定期录入新的运营经验和处置方案", "文档标题要清晰准确，便于查询", "可通过搜索框快速定位相关文档"]
  },
  {
    badge: "04",
    name: "数据管理",
    desc: "录入和编辑每日运营数据，是经营预测和分析的数据基础。",
    tips: ["每日录入入住率、营收等核心指标", "数据录入后会自动用于经营预测", "可编辑历史数据修正录入口径"]
  }
];

const faqs = [
  { q: "预测服务显示未就绪怎么办？", a: "请确认演示服务已启动。运行 start_demo.ps1 脚本可一键启动前端、后端与预测/问答服务。预测服务未就绪时，首页会展示备用判断结果，保证答辩演示不中断。" },
  { q: "如何添加资料文档？", a: "进入「知识库」页面，在录入区填写文档标题和内容，点击「添加文档」即可。建议标题清晰，正文包含处理步骤、适用场景与处置要点，便于问答工作台参考。" },
  { q: "预测结果不理想怎么办？", a: "请先检查「数据管理」中的运营数据是否连续、完整，再核对预测使用口径。入住率、营收和订单取消风险都依赖历史数据质量，数据缺失会影响判断结果。" },
  { q: "问答工作台为什么没有直接给出入住率或营收数值？", a: "问答工作台负责查询资料、整理依据和补充建议，不直接承担数值预测。入住率、营收和订单取消风险预测结果应以首页预测卡片和判断依据为准。" },
  { q: "如何导出经营报表？", a: "在「经营总览」页面，点击页面右上角的「导出 Excel」按钮即可下载当日报表。报表通常包含核心指标、趋势图、预测摘要与处理建议。" },
  { q: "忘记密码怎么办？", a: "请联系管理员账号在后台重置用户状态。演示环境常用账号为 admin/admin123 与 staff/staff123，正式部署时应改为独立账号和自定义密码策略。" }
];

const steps = [
  { title: "登录系统", desc: "使用管理员账号 admin/admin123 或员工账号 staff/staff123 登录系统，进入运营支持工作台。" },
  { title: "查看经营总览", desc: "先在首页查看今日运营判断、预测结果、风险提示和处理建议，确认当前经营态势。" },
  { title: "录入运营数据", desc: "在「数据管理」中录入或修正入住率、营收等日常指标，为经营预测提供最新输入。" },
  { title: "补充知识库", desc: "将处理流程、客诉处理方案、节假日运营经验等录入「知识库」，提升问答参考质量。" },
  { title: "使用问答工作台", desc: "围绕运营问题、服务波动和处置流程发起提问，结合参考资料继续追问并辅助解释首页建议。" }
];
</script>

<style scoped>
.help-facts-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.help-fact-item {
  display: grid;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  border: 1px solid var(--line);
  background: var(--bg-panel-muted);
  box-shadow: var(--shadow-xs);
  transition: all var(--transition-base);
}

.help-fact-item:hover {
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
  border-color: var(--line-strong);
}

.help-fact-item span {
  font-size: 11px;
  color: var(--ink-soft);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 700;
}

.help-fact-item strong {
  font-size: 13px;
  color: var(--ink-strong);
  line-height: 1.6;
}

.help-module-list {
  display: grid;
  gap: 12px;
}

.help-module {
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--radius-md);
  border: 1px solid var(--line);
  background: var(--bg-panel-muted);
  display: grid;
  gap: var(--spacing-sm);
  transition: all var(--transition-base);
}

.help-module:hover {
  border-color: var(--line-strong);
  box-shadow: var(--shadow-xs);
}

.help-module__head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.help-module__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 24px;
  border-radius: 4px;
  background: var(--accent-soft);
  color: var(--accent-strong);
  font-size: 11px;
  font-weight: 700;
}

.help-module p {
  margin: 0;
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.6;
}

.help-module ul {
  margin: 0;
  padding-left: 16px;
}

.help-module li {
  font-size: 13px;
  color: var(--ink);
  margin-bottom: 4px;
  line-height: 1.6;
}

.faq-list {
  display: grid;
  gap: 2px;
}

.faq-item {
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: all var(--transition-base);
}

.faq-item:hover {
  border-color: var(--line-strong);
  box-shadow: var(--shadow-xs);
}

.faq-question {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md) var(--spacing-lg);
  cursor: pointer;
  background: var(--bg-panel);
  transition: all var(--transition-base);
}

.faq-question:hover {
  background: var(--bg-panel-muted);
}

.faq-question strong {
  font-size: 13px;
  color: var(--ink-strong);
  line-height: 1.5;
}

.faq-toggle {
  color: var(--ink-soft);
  font-size: 10px;
  flex-shrink: 0;
}

.faq-answer {
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--bg-panel-muted);
  border-top: 1px solid var(--line);
}

.faq-answer p {
  margin: 0;
  font-size: 13px;
  color: var(--ink);
  line-height: 1.7;
}

.quickstart-steps {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.quickstart-step {
  display: grid;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  border: 1px solid var(--line);
  background: var(--bg-panel-muted);
  transition: all var(--transition-base);
}

.quickstart-step:hover {
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
  border-color: var(--line-strong);
}

.step-num {
  width: 32px;
  height: 32px;
  border-radius: 999px;
  background: var(--accent);
  color: #ffffff;
  font-size: 14px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.step-content {
  display: grid;
  gap: 4px;
}

.step-content strong {
  font-size: 13px;
  color: var(--ink-strong);
}

.step-content p {
  margin: 0;
  font-size: 12px;
  color: var(--ink-soft);
  line-height: 1.6;
}

@media (max-width: 1180px) {
  .help-facts-grid,
  .quickstart-steps {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .help-facts-grid,
  .quickstart-steps {
    grid-template-columns: 1fr;
  }
}
</style>
