<template>
  <div class="page-stack">
    <section class="workspace-card about-hero">
      <div class="about-logo">
        <div class="brand-mark brand-mark--large">
          <span></span><span></span><span></span><span></span>
        </div>
      </div>
      <div class="about-intro">
        <h2>酒店运营支持系统</h2>
        <p class="version">版本 1.1.0 · 构建于 2026.03.30</p>
      </div>
    </section>

    <div class="surface-grid--equal">
      <section class="workspace-card">
        <div class="section-header__copy">
          <p class="workspace-label">建设说明</p>
          <h3 class="panel-title">系统组成</h3>
        </div>
        <div class="tech-grid">
          <div class="tech-item">
            <span class="tech-icon">🖥</span>
            <div>
              <strong>业务界面</strong>
              <p>提供经营看板、数据维护、问答和管理页面</p>
            </div>
          </div>
          <div class="tech-item">
            <span class="tech-icon">⚙</span>
            <div>
              <strong>业务服务</strong>
              <p>负责账号、数据、通知、资料文档等业务处理</p>
            </div>
          </div>
          <div class="tech-item">
            <span class="tech-icon">🤖</span>
            <div>
              <strong>经营预测</strong>
              <p>负责入住率、营收和订单取消风险预测</p>
            </div>
          </div>
          <div class="tech-item">
            <span class="tech-icon">💬</span>
            <div>
              <strong>运营咨询</strong>
              <p>负责查询参考资料、整理依据并补充处理建议</p>
            </div>
          </div>
        </div>
      </section>

      <section class="workspace-card">
        <div class="section-header__copy">
          <p class="workspace-label">核心能力</p>
          <h3 class="panel-title">核心功能</h3>
        </div>
        <div class="feature-list">
          <div class="feature-item">
            <span class="badge badge--success">✓</span>
            <span>实时运营指标监控与可视化</span>
          </div>
          <div class="feature-item">
            <span class="badge badge--success">✓</span>
            <span>入住率、营收、订单取消风险联动分析</span>
          </div>
          <div class="feature-item">
            <span class="badge badge--success">✓</span>
            <span>基于预测结果与业务规则的运营决策支持</span>
          </div>
          <div class="feature-item">
            <span class="badge badge--success">✓</span>
            <span>运营问答、参考资料与处理建议</span>
          </div>
          <div class="feature-item">
            <span class="badge badge--success">✓</span>
            <span>多角色权限、知识管理与运营数据维护</span>
          </div>
          <div class="feature-item">
            <span class="badge badge--success">✓</span>
            <span>服务波动时的备用展示数据</span>
          </div>
        </div>
      </section>
    </div>

    <section class="workspace-card">
      <div class="section-header__copy">
        <p class="workspace-label">预测口径</p>
        <h3 class="panel-title">预测口径</h3>
      </div>
      <div class="fact-grid">
        <div class="info-item">
          <span>入住率预测</span>
          <strong>基于历史入住表现和近期趋势判断</strong>
          <small>用于提示未来客房利用率变化</small>
        </div>
        <div class="info-item">
          <span>营收预测</span>
          <strong>基于历史营收和客房销售表现判断</strong>
          <small>用于提示未来收入压力和增长空间</small>
        </div>
        <div class="info-item">
          <span>订单取消风险预测</span>
          <strong>基于历史订单取消表现判断</strong>
          <small>用于提醒渠道和预抵订单的稳定性风险</small>
        </div>
        <div class="info-item">
          <span>运营咨询</span>
          <strong>资料库 + 处理建议</strong>
          <small>用于问答、参考资料追溯与决策解释，不直接参与数值预测</small>
        </div>
      </div>
    </section>

    <section class="workspace-card">
      <div class="section-header__copy">
        <p class="workspace-label">项目信息</p>
        <h3 class="panel-title">项目信息</h3>
      </div>
      <div class="info-grid">
        <div class="info-item">
          <span>项目类型</span>
          <strong>毕业设计</strong>
        </div>
        <div class="info-item">
          <span>数据来源</span>
          <strong>Hotel Booking Demand + Hotel Reservations</strong>
        </div>
        <div class="info-item">
          <span>服务组成</span>
          <strong>业务界面 / 后端服务 / 预测与问答服务</strong>
        </div>
        <div class="info-item">
          <span>演示账号</span>
          <strong>admin / admin123</strong>
        </div>
      </div>
    </section>

    <section class="workspace-card copyright">
      <p>© 2026 酒店运营支持系统</p>
      <p class="muted">面向酒店管理层的经营预测、风险提醒与处理建议系统</p>
    </section>
  </div>
</template>

<script setup>
</script>

<style scoped>
.about-hero {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 24px;
}

.about-logo {
  flex-shrink: 0;
}

.brand-mark--large {
  display: grid;
  grid-template-columns: repeat(2, 24px);
  grid-template-rows: repeat(2, 24px);
  gap: 6px;
}

.brand-mark--large span {
  display: block;
  border-radius: 4px;
  background: linear-gradient(135deg, #4f70ab, #8da3c9);
}

.brand-mark--large span:nth-child(2) { opacity: 0.82; }
.brand-mark--large span:nth-child(3) { opacity: 0.58; }
.brand-mark--large span:nth-child(4) { opacity: 0.34; }

.about-intro {
  display: grid;
  gap: 6px;
}

.about-intro h2 {
  margin: 0;
  font-size: 26px;
  color: var(--ink-strong);
}

.about-intro .version {
  margin: 0;
  font-size: 13px;
  color: var(--accent);
  font-weight: 600;
}

.about-intro .desc {
  margin: 0;
  font-size: 14px;
  color: var(--ink-soft);
  line-height: 1.7;
  max-width: 760px;
}

.tech-grid,
.fact-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.tech-item {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  background: var(--bg-panel-muted);
  border: 1px solid var(--line);
  transition: all var(--transition-base);
}

.tech-item:hover {
  border-color: var(--line-strong);
  box-shadow: var(--shadow-xs);
}

.tech-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.tech-item strong {
  font-size: 13px;
  color: var(--ink-strong);
  display: block;
  margin-bottom: 2px;
}

.tech-item p {
  margin: 0;
  font-size: 12px;
  color: var(--ink-soft);
  line-height: 1.5;
}

.feature-list {
  display: grid;
  gap: 8px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 4px;
  background: rgba(46, 150, 107, 0.06);
}

.feature-item span:last-child {
  font-size: 13px;
  color: var(--ink);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.info-item {
  display: grid;
  gap: var(--spacing-xs);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  background: var(--bg-panel-muted);
  border: 1px solid var(--line);
  transition: all var(--transition-base);
}

.info-item:hover {
  border-color: var(--line-strong);
  box-shadow: var(--shadow-xs);
}

.info-item span {
  font-size: 11px;
  color: var(--ink-soft);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 700;
}

.info-item strong {
  font-size: 13px;
  color: var(--ink-strong);
}

.info-item small {
  font-size: 12px;
  color: var(--ink-soft);
  line-height: 1.6;
}

.copyright {
  text-align: center;
}

.copyright p {
  margin: 0;
}

@media (max-width: 960px) {
  .tech-grid,
  .fact-grid,
  .info-grid {
    grid-template-columns: 1fr;
  }

  .about-hero {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
