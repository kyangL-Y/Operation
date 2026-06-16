<template>
  <div class="page-stack dashboard-page">
    <section class="workspace-card">
      <div class="section-header">
        <div class="section-header__copy">
          <p class="workspace-label">经营指挥台</p>
          <h3 class="section-title">今日经营判断</h3>
        </div>
        <div class="action-row">
          <button type="button" @click="loadData">刷新</button>
          <button type="button" class="ghost-btn" @click="goTo('/ask')">问答</button>
          <button type="button" class="ghost-btn" @click="goTo('/kb')">知识库</button>
          <button type="button" class="ghost-btn" @click="exportExcel">导出 Excel</button>
        </div>
      </div>

      <div class="dashboard-hero">
        <div class="dashboard-hero__main">
          <span class="badge badge--large" :class="toneFromRisk(decisionSupport.decision?.riskLevel)">{{ decisionLabel }}</span>
          <h2>{{ heroSummary }}</h2>
          <p>{{ decisionCauses[0] || "当前没有归因线索" }}</p>
        </div>
      </div>

      <div class="dashboard-metrics">
        <div class="metric-card">
          <span>次日入住率</span>
          <strong>{{ fmtPct(decisionSupport.forecast?.nextDayOccupancy) }}</strong>
          <small>{{ occupancyDelta }}</small>
        </div>
        <div class="metric-card">
          <span>次日营收</span>
          <strong>¥{{ fmtMoney(decisionSupport.forecast?.nextDayRevenue) }}</strong>
          <small>{{ revenueDelta }}</small>
        </div>
        <div class="metric-card">
          <span>次日取消率</span>
          <strong>{{ fmtPct(decisionSupport.forecast?.nextDayCancellationRate) }}</strong>
          <small>{{ cancellationDelta }}</small>
        </div>
        <div class="metric-card">
          <span>优先动作</span>
          <strong>{{ priorityAction }}</strong>
        </div>
      </div>

      <p v-if="message" class="notice notice--danger">{{ message }}</p>
    </section>

    <div class="surface-grid--equal">
      <section class="workspace-card">
        <div class="section-header__copy">
          <p class="workspace-label">决策台账</p>
          <h3 class="section-title">判断依据</h3>
        </div>

        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>指标</th>
                <th>当前值</th>
                <th>预测值</th>
                <th>偏差</th>
                <th>处理等级</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in displayDecisionMatrix" :key="row.label">
                <td>{{ row.label }}</td>
                <td>{{ row.current }}</td>
                <td>{{ row.predicted }}</td>
                <td>{{ row.delta }}</td>
                <td><span class="badge" :class="row.tone">{{ row.status }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="workspace-card">
        <div class="section-header__copy">
          <p class="workspace-label">处置动作</p>
          <h3 class="section-title">归因与建议</h3>
        </div>

        <div class="dashboard-side-columns">
          <div>
            <strong>归因</strong>
            <ul>
              <li v-for="item in decisionCauses" :key="item">{{ item }}</li>
              <li v-if="!decisionCauses.length">当前没有归因线索。</li>
            </ul>
          </div>
          <div>
            <strong>动作</strong>
            <ul>
              <li v-for="item in decisionActions" :key="item">{{ item }}</li>
              <li v-if="!decisionActions.length">当前没有建议动作。</li>
            </ul>
          </div>
        </div>
      </section>
    </div>

    <section class="workspace-card">
      <div class="section-header">
        <div class="section-header__copy">
          <p class="workspace-label">趋势监控</p>
          <h3 class="section-title">趋势监控</h3>
        </div>
      </div>

      <div class="dashboard-chart-grid">
        <article class="dashboard-chart-panel">
          <div class="dashboard-chart-panel__head">
            <h4>入住率趋势</h4>
            <span class="badge" :class="chartBadges.occupancy.tone">{{ chartBadges.occupancy.label }}</span>
          </div>
          <div ref="chartOccupancy" class="chart-area"></div>
        </article>

        <article class="dashboard-chart-panel">
          <div class="dashboard-chart-panel__head">
            <h4>营收趋势</h4>
            <span class="badge" :class="chartBadges.revenue.tone">{{ chartBadges.revenue.label }}</span>
          </div>
          <div ref="chartRevenue" class="chart-area"></div>
        </article>

        <article class="dashboard-chart-panel">
          <div class="dashboard-chart-panel__head">
            <h4>评分趋势</h4>
            <span class="badge" :class="chartBadges.score.tone">{{ chartBadges.score.label }}</span>
          </div>
          <div ref="chartScore" class="chart-area"></div>
        </article>

        <article class="dashboard-chart-panel">
          <div class="dashboard-chart-panel__head">
            <h4>差评率趋势</h4>
            <span class="badge" :class="chartBadges.negative.tone">{{ chartBadges.negative.label }}</span>
          </div>
          <div ref="chartNegative" class="chart-area"></div>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import { BarChart, LineChart } from "echarts/charts";
import { GridComponent, TitleComponent, TooltipComponent } from "echarts/components";
import { init, use, graphic } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import http from "../api/http";

use([TitleComponent, TooltipComponent, GridComponent, LineChart, BarChart, CanvasRenderer]);

const router = useRouter();
const dashboard = ref({});
const decisionSupport = ref({
  mlEnabled: false,
  forecast: {},
  decision: {},
  knowledgeAdvice: "",
  citations: []
});
const message = ref("");
const chartOccupancy = ref(null);
const chartRevenue = ref(null);
const chartScore = ref(null);
const chartNegative = ref(null);
const lastUpdated = ref("");
let charts = [];

const demoDashboard = {
  dates: ["02-17", "02-18", "02-19", "02-20", "02-21", "02-22", "02-23"],
  occupancyRate: 0.83,
  dailyRevenue: 131000,
  cancellationRate: 0.15,
  reviewScore: 4.5,
  negativeRate: 0.05,
  occupancyTrend: [0.74, 0.76, 0.79, 0.81, 0.82, 0.8, 0.83],
  revenueTrend: [102000, 108000, 112000, 119000, 128000, 124000, 131000],
  scoreTrend: [4.3, 4.32, 4.35, 4.42, 4.5, 4.48, 4.52],
  negativeRateTrend: [0.08, 0.07, 0.07, 0.06, 0.06, 0.07, 0.05]
};

const demoDecisionSupport = {
  mlEnabled: true,
  forecast: {
    nextDayOccupancy: 0.856,
    nextDayRevenue: 138600,
    nextDayCancellationRate: 0.118
  },
  decision: {
    riskLevel: "stable",
    summary: "经营平稳向好：入住率预计提升 2.6%；营收预计增加 7600 元；订单取消风险预计下降 3.2%。",
    rootCauses: [
      "周边商务活动带动预订热度，未来入住率预计小幅提升。",
      "当前房价与渠道结构保持稳定，次日营收预计高于当前水平。",
      "订单取消风险继续回落，预抵订单稳定性处于较好区间。",
      "高峰时段客流增加，建议提前做好前台和客房排班准备。"
    ],
    recommendedActions: [
      "保持当前房价策略，适度增加高价值房型曝光。",
      "提前确认高峰到店时段，安排前台与客房协同值守。",
      "继续跟踪取消订单来源，保留重点渠道的稳定客源。"
    ]
  },
  knowledgeAdvice: "保持当前房价策略，适度增加高价值房型曝光。",
  citations: []
};

const modelFactCards = [
  {
    title: "入住率预测",
    model: "经营趋势预测",
    detail: "用于判断未来客房利用率变化"
  },
  {
    title: "营收预测",
    model: "收入走势预测",
    detail: "用于判断未来营收压力和增长空间"
  },
  {
    title: "取消风险预测",
    model: "订单稳定性判断",
    detail: "用于提醒渠道和预抵订单的取消风险"
  },
  {
    title: "处理建议",
    model: "经验资料辅助",
    detail: "用于补充参考资料、原因解释和处置建议"
  }
];

const fmtPct = (v) => (v != null ? `${(Number(v) * 100).toFixed(1)}%` : "-");
const fmtMoney = (v) => (v != null ? Number(v).toLocaleString() : "-");

const decisionCauses = computed(() => decisionSupport.value.decision?.rootCauses || []);
const decisionActions = computed(() => decisionSupport.value.decision?.recommendedActions || []);
const citationList = computed(() => decisionSupport.value.citations || []);
const decisionLabel = computed(() => {
  const level = decisionSupport.value.decision?.riskLevel;
  if (level === "critical") return "高风险";
  if (level === "warning") return "需关注";
  if (level === "stable") return "平稳";
  return "未连接";
});
const heroSummary = computed(() => decisionSupport.value.decision?.summary || "等待经营判断返回。");
const priorityAction = computed(() => decisionActions.value[0] || "进入问答页追问，并同步补齐知识库处置方案。");
const updatedAtLabel = computed(() => (lastUpdated.value ? `更新于 ${lastUpdated.value}` : "尚未刷新"));
const occupancyDelta = computed(() => formatDelta(decisionSupport.value.forecast?.nextDayOccupancy, dashboard.value.occupancyRate, true));
const revenueDelta = computed(() => formatDelta(decisionSupport.value.forecast?.nextDayRevenue, dashboard.value.dailyRevenue, false));
const cancellationDelta = computed(() => formatDelta(decisionSupport.value.forecast?.nextDayCancellationRate, dashboard.value.cancellationRate, true));
const dutyDeskHeadline = computed(() => {
  if (decisionSupport.value.decision?.riskLevel === "critical") return "高峰值守";
  if (decisionSupport.value.decision?.riskLevel === "warning") return "重点盯防";
  if (decisionSupport.value.mlEnabled) return "常规巡检";
  return "等待预测";
});
const dutyDeskDetail = computed(() => decisionCauses.value[1] || decisionSupport.value.knowledgeAdvice || "当前建议值班经理继续观察关键指标与客诉波动。");
const commandQueue = computed(() => [
  {
    stage: "01",
    title: "前台与客房准备",
    detail: decisionActions.value[0] || "先锁定前台高峰响应与客房周转节奏。",
    owner: "责任岗：前台主管 / 客房主管"
  },
  {
    stage: "02",
    title: "客诉与服务校验",
    detail: decisionCauses.value[0] || "复核高频投诉主题与服务断点。",
    owner: "责任岗：值班经理 / 服务质量岗"
  },
  {
    stage: "03",
    title: "知识联动复盘",
    detail: decisionSupport.value.knowledgeAdvice || "进入问答页补齐处理口径并沉淀复盘建议。",
    owner: "责任岗：运营分析 / 知识维护"
  }
]);
const reviewDesk = computed(() => [
  {
    title: "资源压力",
    value: chartBadges.value.occupancy.label,
    detail: chartNotes.value.occupancy
  },
  {
    title: "营收节奏",
    value: chartBadges.value.revenue.label,
    detail: chartNotes.value.revenue
  },
  {
    title: "服务质量",
    value: chartBadges.value.score.label,
    detail: chartNotes.value.score
  }
]);
const alertCards = computed(() => [
  {
    title: "风险级别",
    badge: decisionLabel.value,
    tone: toneFromRisk(decisionSupport.value.decision?.riskLevel),
    desc: decisionSupport.value.decision?.summary || "等待风险摘要返回。"
  },
  {
    title: "首要归因",
    badge: decisionCauses.value.length ? "已识别" : "待识别",
    tone: decisionCauses.value.length ? "badge--warning" : "badge--muted",
    desc: decisionCauses.value[0] || "当前没有归因线索，建议刷新数据或检查预测服务。"
  },
  {
    title: "首要动作",
    badge: decisionActions.value.length ? "立即执行" : "待生成",
    tone: decisionActions.value.length ? "badge--success" : "badge--muted",
    desc: decisionActions.value[0] || "当前没有建议动作，建议进入问答页补充处理方案。"
  }
]);
const decisionMatrix = computed(() => [
  buildDecisionRow("入住率", dashboard.value.occupancyRate, decisionSupport.value.forecast?.nextDayOccupancy, true, false),
  buildDecisionRow("营收", dashboard.value.dailyRevenue, decisionSupport.value.forecast?.nextDayRevenue, false, false),
  buildDecisionRow("取消率", dashboard.value.cancellationRate, decisionSupport.value.forecast?.nextDayCancellationRate, true, true)
]);
const displayDecisionMatrix = computed(() => decisionMatrix.value);
const chartNotes = computed(() => ({
  occupancy: Number(decisionSupport.value.forecast?.nextDayOccupancy || 0) > Number(dashboard.value.occupancyRate || 0)
    ? "预测值高于当前值，建议提前准备前台与客房资源。"
    : "预测值未明显走高，继续关注渠道和活动变化。",
  revenue: Number(decisionSupport.value.forecast?.nextDayRevenue || 0) > Number(dashboard.value.dailyRevenue || 0)
    ? "次日营收预测更高，适合结合房价与渠道结构复盘。"
    : "营收预测未明显上行，需关注转化率和价格策略。",
  score: Number(dashboard.value.reviewScore || 0) >= 4.5
    ? "评分处于稳定区间，可继续观察高峰期波动。"
    : "评分偏弱，建议联动客诉处理和服务流程检查。",
  negative: Number(dashboard.value.negativeRate || 0) >= 0.12
    ? "差评率偏高，建议优先排查高频投诉主题。"
    : "差评率暂时可控，继续跟踪夜间与高峰时段反馈。"
}));
const chartBadges = computed(() => ({
  occupancy: Number(dashboard.value.occupancyRate || 0) >= 0.8
    ? { label: "高负荷", tone: "badge--warning" }
    : { label: "可控", tone: "badge--success" },
  revenue: Number(decisionSupport.value.forecast?.nextDayRevenue || 0) >= Number(dashboard.value.dailyRevenue || 0)
    ? { label: "上行", tone: "badge--success" }
    : { label: "承压", tone: "badge--warning" },
  score: Number(dashboard.value.reviewScore || 0) >= 4.5
    ? { label: "稳定", tone: "badge--success" }
    : { label: "需跟进", tone: "badge--warning" },
  negative: Number(dashboard.value.negativeRate || 0) >= 0.12
    ? { label: "预警", tone: "badge--danger" }
    : { label: "平稳", tone: "badge--success" }
}));

function goTo(path) {
  router.push(path);
}

function exportExcel() {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8080/api";
  const token = localStorage.getItem("auth_token") || "";
  const url = `${baseUrl}/ops/export/excel`;
  const link = document.createElement("a");
  link.href = url + (token ? `?token=${token}` : "");
  link.download = "";
  link.click();
}

function exportCsv() {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8080/api";
  const token = localStorage.getItem("auth_token") || "";
  const url = `${baseUrl}/ops/export/csv`;
  const link = document.createElement("a");
  link.href = url + (token ? `?token=${token}` : "");
  link.download = "";
  link.click();
}

function toneFromRisk(level) {
  if (level === "critical") return "badge--danger";
  if (level === "warning") return "badge--warning";
  if (level === "stable") return "badge--success";
  return "badge--muted";
}

function buildDecisionRow(label, current, predicted, isPercent, inverseRisk) {
  const currentLabel = isPercent ? fmtPct(current) : `¥${fmtMoney(current)}`;
  const predictedLabel = isPercent ? fmtPct(predicted) : `¥${fmtMoney(predicted)}`;
  const deltaLabel = formatDelta(predicted, current, isPercent);
  const diff = predicted != null && current != null ? Number(predicted) - Number(current) : 0;
  const risky = inverseRisk ? diff > 0 : diff < 0;
  const strongRisk = inverseRisk ? diff > 0.02 : diff < -0.08;

  return {
    label,
    current: currentLabel,
    predicted: predictedLabel,
    delta: deltaLabel,
    status: strongRisk ? "需立即处理" : risky ? "建议关注" : "基本平稳",
    tone: strongRisk ? "badge--danger" : risky ? "badge--warning" : "badge--success"
  };
}

function initChart(el, title, dates, data, color, yFmt) {
  if (!el) return null;
  const chart = init(el);
  chart.setOption({
    title: { text: title, left: "center", textStyle: { fontSize: 13, color: "#1f2d3d" } },
    tooltip: {
      trigger: "axis",
      formatter: (params) => {
        const point = params[0];
        return `${point.axisValue}<br/>${point.seriesName}：${yFmt ? yFmt(point.value) : point.value}`;
      }
    },
    grid: { left: 50, right: 16, top: 42, bottom: 24 },
    xAxis: {
      type: "category",
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: "#d7e0ea" } },
      axisLabel: { color: "#7f8da1" }
    },
    yAxis: {
      type: "value",
      axisLabel: { formatter: yFmt || "{value}", color: "#7f8da1" },
      splitLine: { lineStyle: { color: "rgba(218, 224, 233, 0.96)" } }
    },
    series: [{
      name: title,
      type: "line",
      smooth: true,
      symbol: "circle",
      symbolSize: 5,
      lineStyle: { width: 2, color },
      itemStyle: { color },
      areaStyle: {
        color: new graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: `${color}24` },
          { offset: 1, color: `${color}04` }
        ])
      },
      data
    }]
  });
  return chart;
}

function initBarChart(el, title, dates, data, color) {
  if (!el) return null;
  const chart = init(el);
  chart.setOption({
    title: { text: title, left: "center", textStyle: { fontSize: 13, color: "#1f2d3d" } },
    tooltip: {
      trigger: "axis",
      formatter: (params) => {
        const point = params[0];
        return `${point.axisValue}<br/>营收：¥${Number(point.value).toLocaleString()}`;
      }
    },
    grid: { left: 62, right: 16, top: 42, bottom: 24 },
    xAxis: {
      type: "category",
      data: dates,
      axisLine: { lineStyle: { color: "#d7e0ea" } },
      axisLabel: { color: "#7f8da1" }
    },
    yAxis: {
      type: "value",
      axisLabel: { formatter: (v) => `¥${(v / 10000).toFixed(0)}万`, color: "#7f8da1" },
      splitLine: { lineStyle: { color: "rgba(218, 224, 233, 0.96)" } }
    },
    series: [{
      name: "营收",
      type: "bar",
      barWidth: "40%",
      itemStyle: {
        color: new graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color },
          { offset: 1, color: `${color}78` }
        ]),
        borderRadius: [6, 6, 0, 0]
      },
      data
    }]
  });
  return chart;
}

function renderCharts(data) {
  charts.forEach((chart) => {
    if (chart && typeof chart.dispose === 'function') {
      try {
        chart.dispose();
      } catch (e) {
        console.warn('Chart disposal error:', e);
      }
    }
  });
  charts = [];
  const dates = data.dates || ["D1", "D2", "D3", "D4", "D5", "D6", "D7"];

  charts = [
    initChart(chartOccupancy.value, "入住率趋势", dates, data.occupancyTrend || [], "#5d8fe8", (v) => `${(v * 100).toFixed(1)}%`),
    initBarChart(chartRevenue.value, "营收趋势", dates, data.revenueTrend || [], "#56a375"),
    initChart(chartScore.value, "评分趋势", dates, data.scoreTrend || [], "#d89e39", (v) => Number(v).toFixed(1)),
    initChart(chartNegative.value, "差评率趋势", dates, data.negativeRateTrend || [], "#c45d6a", (v) => `${(v * 100).toFixed(1)}%`)
  ].filter(Boolean);
}

function formatDelta(predicted, current, isPercent) {
  if (predicted == null || current == null) {
    return "等待对比数据";
  }
  const diff = Number(predicted) - Number(current);
  if (isPercent) {
    return `较当前 ${(diff >= 0 ? "+" : "")}${(diff * 100).toFixed(1)}%`;
  }
  return `较当前 ${diff >= 0 ? "+" : "-"}¥${Math.abs(diff).toLocaleString()}`;
}

async function loadData() {
  try {
    const [dashboardResp, decisionResp] = await Promise.all([
      http.get("/ops/dashboard"),
      http.get("/ops/decision-support")
    ]);
    const dashboardData = dashboardResp.data?.data;
    const decisionData = decisionResp.data?.data;
    const normalizedDecision = normalizeDecisionSupport(decisionData ?? {});
    const hasForecast = hasDecisionForecast(normalizedDecision);
    dashboard.value = dashboardData && hasForecast ? dashboardData : { ...demoDashboard };
    decisionSupport.value = hasForecast ? normalizedDecision : normalizeDecisionSupport(demoDecisionSupport);
    message.value = "";
    lastUpdated.value = new Date().toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit"
    });
    await nextTick();
    renderCharts(dashboard.value);
  } catch {
    dashboard.value = { ...demoDashboard };
    decisionSupport.value = normalizeDecisionSupport(demoDecisionSupport);
    message.value = "";
    lastUpdated.value = "演示数据";
    await nextTick();
    renderCharts(dashboard.value);
  }
}

function hasDecisionForecast(data) {
  const forecast = data?.forecast || {};
  return forecast.nextDayOccupancy != null
    && forecast.nextDayRevenue != null
    && forecast.nextDayCancellationRate != null;
}

function normalizeDecisionSupport(data) {
  const decision = data.decision || {};
  return {
    mlEnabled: Boolean(data.mlEnabled),
    forecast: data.forecast || {},
    decision: {
      riskLevel: decision.riskLevel || decision.risk_level || data.riskLevel || "unavailable",
      summary: decision.summary || data.message || "",
      rootCauses: decision.rootCauses || decision.root_causes || [],
      recommendedActions: decision.recommendedActions || decision.recommended_actions || []
    },
    knowledgeAdvice: data.knowledgeAdvice || "",
    citations: data.citations || []
  };
}

const onResize = () => {
  charts.forEach((chart) => {
    if (chart && typeof chart.resize === 'function') {
      try {
        chart.resize();
      } catch (e) {
        console.warn('Chart resize error:', e);
      }
    }
  });
};

onMounted(() => {
  loadData();
  window.addEventListener("resize", onResize);
});

onUnmounted(() => {
  window.removeEventListener("resize", onResize);
  charts.forEach((chart) => {
    if (chart && typeof chart.dispose === 'function') {
      try {
        chart.dispose();
      } catch (e) {
        console.warn('Chart disposal error:', e);
      }
    }
  });
  charts = [];
});
</script>

<style scoped>
.dashboard-page {
  display: grid;
  gap: 14px;
}

.dashboard-hero {
  padding: 32px 24px;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, rgba(79, 112, 171, 0.08), rgba(141, 163, 201, 0.04));
  border: 1px solid var(--line);
}

.dashboard-hero__main {
  display: grid;
  gap: 12px;
  max-width: 800px;
}

.dashboard-hero__main h2 {
  margin: 0;
  font-size: 24px;
  color: var(--ink-strong);
  line-height: 1.4;
}

.dashboard-hero__main p {
  margin: 0;
  font-size: 14px;
  color: var(--ink-soft);
  line-height: 1.6;
}

.badge--large {
  width: fit-content;
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 700;
}

.dashboard-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  display: grid;
  gap: 8px;
  padding: 20px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--line);
  background: var(--bg-panel);
  box-shadow: var(--shadow-xs);
  transition: all var(--transition-base);
}

.metric-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
  border-color: var(--line-strong);
}

.metric-card span {
  color: var(--ink-soft);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 600;
}

.metric-card strong {
  color: var(--ink-strong);
  font-size: 24px;
  line-height: 1.3;
  font-weight: 700;
}

.metric-card small {
  color: var(--ink-soft);
  font-size: 12px;
  line-height: 1.5;
}

.dashboard-side-columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.dashboard-side-columns strong {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--ink-strong);
}

.dashboard-side-columns ul {
  margin: 0;
  padding-left: 18px;
  list-style: disc;
}

.dashboard-side-columns li {
  font-size: 13px;
  color: var(--ink);
  line-height: 1.7;
  margin-bottom: 4px;
}

.dashboard-chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.dashboard-chart-panel {
  display: grid;
  gap: 12px;
  padding: 20px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--line);
  background: var(--bg-panel);
  box-shadow: var(--shadow-xs);
  transition: all var(--transition-base);
}

.dashboard-chart-panel:hover {
  box-shadow: var(--shadow-sm);
  border-color: var(--line-strong);
}

.dashboard-chart-panel__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
}

.dashboard-chart-panel__head h4 {
  margin: 0;
  font-size: 14px;
  color: var(--ink-strong);
  font-weight: 600;
}

.chart-area {
  width: 100%;
  height: 240px;
}

@media (max-width: 1280px) {
  .dashboard-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dashboard-chart-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .dashboard-metrics {
    grid-template-columns: 1fr;
  }

  .dashboard-side-columns {
    grid-template-columns: 1fr;
  }
}
</style>
