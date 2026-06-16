<template>
  <div v-if="isLoginRoute" class="login-scene">
    <div class="login-scene__backdrop"></div>
    <router-view />
  </div>

  <div v-else class="app-shell" :class="{ 'app-shell--admin': isAdminRoute }">
    <aside class="app-rail" :class="{ 'app-rail--admin': isAdminRoute }">
      <div class="app-rail__brand-wrap">
        <div class="app-rail__brand">
          <div class="brand-mark" aria-hidden="true">
            <span></span>
            <span></span>
            <span></span>
            <span></span>
          </div>
          <div>
            <p class="brand-eyebrow">酒店运营</p>
            <h1>运营支持系统</h1>
            <p class="brand-note">{{ isAdminRoute ? "管理员控制空间" : "运营支持工作台" }}</p>
          </div>
        </div>
        <div class="brand-meta">
          <span>{{ isAdminRoute ? "管理域" : "企业版" }}</span>
          <span>{{ isAdminRoute ? "高权限控制" : "统一工作区" }}</span>
        </div>
        <div v-if="isAdminRoute" class="rail-command-board">
          <article v-for="item in adminShellSignals" :key="item.label" class="rail-command-board__item">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <small>{{ item.detail }}</small>
          </article>
        </div>
        <div class="rail-overview">
          <div v-for="item in shellStats" :key="item.label" class="rail-overview__card">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
      </div>

      <div class="rail-group">
        <p class="rail-group__title">{{ isAdminRoute ? "业务区" : "导航" }}</p>
        <nav class="app-nav" aria-label="主导航">
          <router-link
            v-for="item in workspaceNavItems"
            :key="item.to"
            :to="item.to"
            class="app-nav__item"
          >
            <span class="app-nav__index">{{ item.badge }}</span>
            <span class="app-nav__body">
              <strong>{{ item.label }}</strong>
              <small>{{ item.desc }}</small>
            </span>
          </router-link>
        </nav>
      </div>

      <div v-if="authRole === 'ADMIN'" class="rail-group rail-group--admin-nav">
        <p class="rail-group__title">管理区</p>
        <nav class="app-nav app-nav--admin" aria-label="管理导航">
          <router-link
            v-for="item in adminNavItems"
            :key="item.to"
            :to="item.to"
            class="app-nav__item app-nav__item--admin"
          >
            <span class="app-nav__index">{{ item.badge }}</span>
            <span class="app-nav__body">
              <strong>{{ item.label }}</strong>
              <small>{{ item.desc }}</small>
            </span>
          </router-link>
        </nav>
      </div>

      <div class="rail-group rail-group--meta">
        <p class="rail-group__title">系统状态</p>
        <dl class="rail-meta">
          <div>
            <dt>账号</dt>
            <dd>{{ authDisplayName || authRole || "未登录" }}</dd>
          </div>
          <div>
            <dt>角色</dt>
            <dd>{{ authRoleLabel }}</dd>
          </div>
          <div>
            <dt>预测服务</dt>
            <dd>{{ mlStatus }}</dd>
          </div>
        </dl>

        <div class="rail-actions">
          <router-link class="ghost-btn" to="/login">
            {{ authState ? "切换账号" : "进入登录" }}
          </router-link>
          <button
            v-if="authState"
            type="button"
            class="ghost-btn ghost-btn--danger"
            @click="logout"
          >
            退出登录
          </button>
        </div>
      </div>

      <div v-if="isAdminRoute" class="rail-group rail-group--admin">
        <p class="rail-group__title">管理域</p>
        <div class="admin-lane-list">
          <div class="admin-lane">
            <span>01</span>
            <div>
              <strong>账号目录</strong>
              <small>主表、筛选、批量状态</small>
            </div>
          </div>
          <div class="admin-lane">
            <span>02</span>
            <div>
              <strong>授权基线</strong>
              <small>角色组与权限边界</small>
            </div>
          </div>
          <div class="admin-lane">
            <span>03</span>
            <div>
              <strong>对象写入</strong>
              <small>新增账号与角色落位</small>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <div class="app-frame" :class="{ 'app-frame--admin': isAdminRoute }">
      <header class="app-header" :class="{ 'app-header--admin': isAdminRoute }">
        <div class="app-header__main">
          <div class="page-caption-row">
            <p class="page-caption">{{ isAdminRoute ? "管理控制台" : "酒店运营支持系统" }}</p>
            <span class="page-caption__divider"></span>
            <span class="page-caption__module">{{ currentNav.module }}</span>
          </div>
          <div class="app-header__title-row">
            <h2>{{ currentNav.label }}</h2>
            <p>{{ currentNav.desc }}</p>
          </div>
        </div>

        <div class="app-header__tools">
          <span class="header-status" :class="{ 'header-status--admin': isAdminRoute }">
            <i></i>
            {{ mlStatus }}
          </span>
          <button type="button" class="ghost-btn" @click="refreshSystemState">刷新状态</button>
          <div class="account-chip">{{ accountInitial }}</div>
        </div>
      </header>

      <div class="system-band" :class="{ 'system-band--admin': isAdminRoute }">
        <div class="system-band__item">
          <span>当前页面</span>
          <strong>{{ currentNav.module }}</strong>
        </div>
        <div class="system-band__item system-band__item--wide">
          <span>工作说明</span>
          <strong>{{ currentNav.longDesc }}</strong>
        </div>
        <div class="system-band__item">
          <span>{{ isAdminRoute ? "控制级别" : "当前账号" }}</span>
          <strong>{{ isAdminRoute ? adminLevelLabel : authDisplayName || authRole || "未登录" }}</strong>
        </div>
      </div>

      <main class="app-workspace" :class="{ 'app-workspace--admin': isAdminRoute }">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();

const baseNavItems = [
  {
    to: "/",
    badge: "01",
    label: "经营总览",
    desc: "预测、建议、风险",
    module: "经营总览",
    longDesc: "汇总入住率、营收与订单取消风险三项预测结果，输出决策建议与风险提示。"
  },
  {
    to: "/ask",
    badge: "02",
    label: "问答工作台",
    desc: "咨询、追问、参考资料",
    module: "问答工作台",
    longDesc: "围绕运营问题查询处理建议，支持连续追问并查看参考资料来源。"
  },
  {
    to: "/kb",
    badge: "03",
    label: "知识库",
    desc: "录入、目录、阅读",
    module: "知识库",
    longDesc: "维护处理流程与运营经验等资料，作为问答工作台的参考依据。"
  },
  {
    to: "/data",
    badge: "04",
    label: "数据管理",
    desc: "录入、编辑、预测数据",
    module: "数据管理",
    longDesc: "维护入住率、营收、取消率等每日指标，为经营预测提供基础数据。"
  },
  {
    to: "/notifications",
    badge: "05",
    label: "消息通知",
    desc: "预警、预测状态、提醒",
    module: "消息通知",
    longDesc: "汇总预测服务状态、经营预警线和系统业务提醒。"
  },
  {
    to: "/profile",
    badge: "06",
    label: "个人中心",
    desc: "身份、改密、同步",
    module: "个人中心",
    longDesc: "查看当前账号角色与状态，维护显示名称与登录凭证。"
  },
  {
    to: "/help",
    badge: "07",
    label: "帮助文档",
    desc: "系统口径、常见问题、快速上手",
    module: "帮助文档",
    longDesc: "统一说明系统使用范围、预测适用场景与常见使用路径。"
  }
];

const adminNavItem = {
  to: "/admin",
  badge: "08",
  label: "管理控制台",
  desc: "账号主表、权限、状态",
  module: "管理中枢",
  longDesc: "围绕用户主表和角色权限执行管理操作，适用于管理员角色。"
};

const adminSubNavItems = [
  {
    to: "/admin/settings",
    badge: "A1",
    label: "系统设置",
    desc: "预测服务、预警线、基础设置",
    module: "系统设置",
    longDesc: "统一维护预测与问答连接、经营预警线和系统基础设置。"
  },
  {
    to: "/admin/audit",
    badge: "A2",
    label: "操作日志",
    desc: "审计、追踪、记录",
    module: "审计日志",
    longDesc: "记录登录、管理、知识库与运营侧关键动作，支持分页筛选。"
  },
  {
    to: "/about",
    badge: "A3",
    label: "关于系统",
    desc: "版本、建设说明、业务闭环",
    module: "系统概览",
    longDesc: "系统版本信息、建设方式与经营预测 + 处理建议闭环说明。"
  }
];

const loginMeta = {
  label: "登录入口",
  desc: "系统访问与身份验证",
  module: "访问入口",
  longDesc: "登录后进入统一工作系统。"
};

const authState = ref(Boolean(localStorage.getItem("auth_token")));
const authRole = ref(localStorage.getItem("auth_role") || "");
const authDisplayName = ref(localStorage.getItem("auth_display_name") || "");
const mlStatus = ref(authState.value ? "状态未知" : "未登录");

const isLoginRoute = computed(() => route.path === "/login");
const isAdminRoute = computed(() => route.path.startsWith("/admin"));
const allNavItems = computed(() => (authRole.value === "ADMIN" ? [...baseNavItems, adminNavItem] : baseNavItems));
const workspaceNavItems = computed(() => baseNavItems);
const adminNavItems = computed(() => (authRole.value === "ADMIN" ? [adminNavItem, ...adminSubNavItems] : []));
const currentNav = computed(() =>
  [...baseNavItems, adminNavItem, ...adminSubNavItems].find((item) => item.to === route.path) || loginMeta
);
const shellStats = computed(() => {
  if (!authState.value) {
    return [
      { label: "访问", value: "待登录" },
      { label: "页面", value: `${baseNavItems.length} 个` },
      { label: "状态", value: "待登录" }
    ];
  }

  return [
    { label: "访问", value: authDisplayName.value || authRoleLabel.value || "已登录" },
    { label: "页面", value: `${allNavItems.value.length} 个` },
    { label: "状态", value: mlStatus.value }
  ];
});
const accountInitial = computed(() => (authDisplayName.value || authRole.value || "访").slice(0, 1).toUpperCase());
const authRoleLabel = computed(() => {
  if (authRole.value === "ADMIN") return "系统管理员";
  if (authRole.value === "MANAGER") return "业务管理";
  if (authRole.value === "STAFF") return "一线执行";
  return authRole.value || "访客";
});
const adminLevelLabel = computed(() => {
  if (authRole.value === "ADMIN") {
    return "系统管理员";
  }
  if (authRole.value) {
    return `受限访问 / ${authRoleLabel.value}`;
  }
  return "未登录";
});
const adminShellSignals = computed(() => [
  {
    label: "控制模式",
    value: "治理优先",
    detail: "先账号治理，再进入审计和设置。"
  },
  {
    label: "审计节奏",
    value: route.path === "/admin/audit" ? "日志复核" : "控制主表",
    detail: "管理域保持可追踪、可回滚、可交接。"
  },
  {
    label: "当前页",
    value: currentNav.value.module,
    detail: currentNav.value.desc
  }
]);

function syncAuthState() {
  authState.value = Boolean(localStorage.getItem("auth_token"));
  authRole.value = localStorage.getItem("auth_role") || "";
  authDisplayName.value = localStorage.getItem("auth_display_name") || "";
}

async function refreshSystemState() {
  syncAuthState();
  try {
    const resp = await fetch("http://localhost:5000/api/health");
    const data = await resp.json();
    mlStatus.value = isPredictionRunning(data?.data) ? "预测可用" : "预测待启";
  } catch {
    mlStatus.value = authState.value ? "预测待启" : "未登录";
  }
}

function isPredictionRunning(status) {
  if (!status || typeof status !== "object") {
    return false;
  }
  return status.ml_service === "running"
    || status.status === "running"
    || status.running === true
    || status.mlEnabled === true;
}

function logout() {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("auth_username");
  localStorage.removeItem("auth_display_name");
  localStorage.removeItem("auth_role");
  syncAuthState();
  mlStatus.value = "未登录";
  window.dispatchEvent(new Event("auth-changed"));
  router.push("/login");
}

function handleAuthChange() {
  refreshSystemState();
}

watch(
  () => route.fullPath,
  () => {
    refreshSystemState();
  },
  { immediate: true }
);

onMounted(() => {
  window.addEventListener("auth-changed", handleAuthChange);
});

onUnmounted(() => {
  window.removeEventListener("auth-changed", handleAuthChange);
});
</script>

<style scoped>
.login-scene {
  position: relative;
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  overflow: hidden;
}

.login-scene__backdrop {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(241, 245, 249, 0.92), rgba(248, 250, 252, 0.98));
}

.app-shell {
  position: relative;
  isolation: isolate;
  min-height: 100vh;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  background: var(--bg);
}

.app-rail {
  position: relative;
  display: grid;
  grid-template-rows: auto 1fr auto;
  gap: var(--spacing-xl);
  padding: var(--spacing-xl) var(--spacing-lg);
  background: var(--bg-panel);
  border-right: 1px solid var(--line);
  box-shadow: var(--shadow-sm);
}

.app-rail__brand,
.app-nav__item,
.app-header,
.app-header__title-row,
.app-header__tools,
.rail-actions {
  display: flex;
}

.app-rail__brand-wrap {
  display: grid;
  gap: 12px;
  padding: 0 0 18px;
  border-bottom: 1px solid rgba(226, 231, 238, 0.96);
}

.app-rail__brand {
  align-items: flex-start;
  gap: 12px;
}

.brand-mark {
  display: grid;
  grid-template-columns: repeat(2, 11px);
  grid-template-rows: repeat(2, 11px);
  gap: 4px;
  margin-top: 3px;
}

.brand-mark span {
  display: block;
  border-radius: 2px;
  background: linear-gradient(180deg, #4f70ab, #8da3c9);
}

.brand-mark span:nth-child(2) {
  opacity: 0.82;
}

.brand-mark span:nth-child(3) {
  opacity: 0.58;
}

.brand-mark span:nth-child(4) {
  opacity: 0.34;
}

.brand-eyebrow,
.page-caption,
.rail-group__title {
  margin: 0;
  color: var(--ink-soft);
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 700;
}

.app-rail__brand h1,
.app-header__title-row h2 {
  margin: 0;
  color: var(--ink-strong);
}

.app-rail__brand h1 {
  font-size: 20px;
  line-height: 1.35;
}

.brand-note {
  margin: 4px 0 0;
  color: var(--ink-soft);
  font-size: 12px;
  line-height: 1.5;
}

.brand-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.brand-meta span {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(237, 241, 246, 0.98), rgba(228, 235, 243, 0.98));
  color: #5d6a7c;
  font-size: 11px;
  font-weight: 700;
}

.rail-command-board {
  display: grid;
  gap: 8px;
}

.rail-command-board__item {
  display: grid;
  gap: 4px;
  padding: 11px 12px;
  border-radius: 10px;
  border: 1px solid rgba(217, 224, 233, 0.96);
  background: linear-gradient(180deg, rgba(250, 252, 255, 0.98), rgba(242, 246, 251, 0.98));
}

.rail-command-board__item span {
  color: var(--ink-soft);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 700;
}

.rail-command-board__item strong {
  color: var(--ink-strong);
  font-size: 14px;
  line-height: 1.45;
}

.rail-command-board__item small {
  color: var(--ink-soft);
  font-size: 12px;
  line-height: 1.55;
}

.rail-overview {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.rail-overview__card {
  display: grid;
  gap: 4px;
  padding: 12px 11px;
  border-radius: 10px;
  border: 1px solid rgba(226, 231, 238, 0.96);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(245, 248, 252, 0.88));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.74);
}

.rail-overview__card span {
  color: var(--ink-soft);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 700;
}

.rail-overview__card strong {
  color: var(--ink-strong);
  font-size: 13px;
  line-height: 1.5;
}

.rail-group {
  display: grid;
  gap: 8px;
  align-content: start;
}

.rail-group--meta {
  padding-top: 16px;
  border-top: 1px solid rgba(226, 231, 238, 0.96);
}

.rail-group--admin {
  padding-top: 16px;
  border-top: 1px solid rgba(226, 231, 238, 0.96);
}

.rail-group--admin-nav {
  gap: 10px;
}

.app-nav {
  display: grid;
  gap: 2px;
}

.app-nav--admin {
  gap: 6px;
}

.app-nav__item {
  align-items: flex-start;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  color: var(--ink);
  text-decoration: none;
  position: relative;
  background: transparent;
  transition: all var(--transition-base);
}

.app-nav__item:hover {
  background: var(--bg-hover);
  border-color: var(--line);
  transform: translateX(2px);
}

.app-nav__item.router-link-active {
  background: var(--accent-soft);
  border-color: var(--accent);
  color: var(--accent-strong);
}

.app-nav__item--admin {
  background: linear-gradient(180deg, #f7f9fb 0%, #f1f5f9 100%);
  border-color: rgba(49, 70, 95, 0.1);
}

.app-nav__index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: var(--bg-panel-muted);
  border: 1px solid var(--line);
  color: var(--ink-soft);
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
  transition: all var(--transition-base);
}

.app-nav__item:hover .app-nav__index {
  background: var(--bg-panel);
  border-color: var(--line-strong);
}

.app-nav__item.router-link-active .app-nav__index {
  background: var(--accent);
  border-color: var(--accent);
  color: #ffffff;
}

.app-nav__body {
  display: grid;
  gap: 4px;
}

.app-nav__body strong {
  font-size: 14px;
  line-height: 1.45;
}

.app-nav__body small {
  color: var(--ink-soft);
  font-size: 12px;
  line-height: 1.45;
}

.rail-meta {
  display: grid;
  gap: 8px;
  margin: 0;
}

.rail-meta div {
  display: grid;
  gap: 2px;
  padding: 11px 12px;
  border-radius: 10px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.9), rgba(244, 248, 252, 0.84));
  border: 1px solid rgba(226, 231, 238, 0.96);
}

.rail-meta dt {
  color: var(--ink-soft);
  font-size: 12px;
}

.rail-meta dd {
  margin: 0;
  color: var(--ink-strong);
  font-size: 13px;
  font-weight: 600;
}

.rail-actions {
  flex-wrap: wrap;
  gap: 8px;
}

.admin-lane-list {
  display: grid;
  gap: 8px;
}

.admin-lane {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  padding: 12px;
  border: 1px solid rgba(226, 231, 238, 0.96);
  border-radius: 10px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.84), rgba(243, 247, 251, 0.78));
}

.admin-lane span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  border-radius: 4px;
  background: #edf1f6;
  color: var(--accent-strong);
  font-size: 11px;
  font-weight: 700;
}

.admin-lane div {
  display: grid;
  gap: 2px;
}

.admin-lane strong {
  color: var(--ink-strong);
  font-size: 13px;
}

.admin-lane small {
  color: var(--ink-soft);
  font-size: 12px;
  line-height: 1.5;
}

.app-frame {
  min-width: 0;
  display: grid;
  grid-template-rows: auto auto 1fr;
  gap: 0;
  padding: 24px 24px 28px;
}

.app-header {
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-xl);
  padding: var(--spacing-lg) var(--spacing-xl);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  background: var(--bg-panel);
  border: 1px solid var(--line);
  border-bottom: none;
  box-shadow: var(--shadow-xs);
}

.app-header__main {
  display: grid;
  gap: 6px;
}

.page-caption-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.page-caption__divider {
  width: 1px;
  height: 12px;
  background: rgba(214, 223, 235, 0.96);
}

.page-caption__module {
  color: var(--ink-soft);
  font-size: 12px;
  font-weight: 700;
}

.app-header__title-row {
  align-items: center;
  gap: 14px;
}

.app-header__title-row h2 {
  font-size: 30px;
  line-height: 1.2;
}

.app-header__title-row p {
  margin: 0;
  color: var(--ink-soft);
  font-size: 14px;
  line-height: 1.55;
  max-width: 520px;
}

.app-header__tools {
  align-items: center;
  gap: 10px;
}

.header-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid rgba(218, 224, 233, 0.96);
  background: #ffffff;
  color: var(--ink-soft);
  font-size: 13px;
  font-weight: 700;
}

.header-status i {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #4f70ab;
}

.account-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 12px;
  border: 1px solid rgba(218, 224, 233, 0.96);
  background: linear-gradient(180deg, #ffffff, #f4f7fb);
  color: var(--ink-strong);
  font-size: 13px;
  font-weight: 700;
}

.system-band {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr) 220px;
  gap: 0;
  padding: 0;
  border: 1px solid var(--line);
  border-top: none;
  background: var(--bg-panel);
}

.system-band__item {
  display: grid;
  gap: var(--spacing-xs);
  padding: var(--spacing-md) var(--spacing-lg);
  border-right: 1px solid var(--line);
}

.system-band__item:last-child {
  border-right: none;
}

.system-band__item span {
  color: var(--ink-soft);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 600;
}

.system-band__item strong {
  color: var(--ink-strong);
  font-size: 13px;
  line-height: 1.5;
  font-weight: 600;
}

.system-band__item--wide strong {
  color: var(--ink);
  font-weight: 500;
}

.app-workspace {
  min-width: 0;
  padding: var(--spacing-xl);
  border: 1px solid var(--line);
  border-top: none;
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
  background: var(--bg-panel);
  box-shadow: var(--shadow-sm);
}

.app-shell--admin {
  background:
    linear-gradient(180deg, #e8edf3 0%, #e3e9f0 100%);
}

.app-rail--admin {
  background:
    linear-gradient(180deg, #e2e8ef 0%, #edf2f7 48%, #f6f8fb 100%);
}

.app-rail--admin .brand-mark span {
  background: linear-gradient(180deg, #31465f, #73849b);
}

.app-rail--admin .app-rail__brand-wrap {
  border-bottom-color: rgba(186, 198, 213, 0.96);
}

.app-rail--admin .brand-meta span,
.app-rail--admin .rail-overview__card,
.app-rail--admin .rail-command-board__item,
.app-rail--admin .rail-meta div,
.app-rail--admin .admin-lane {
  border-color: rgba(186, 198, 213, 0.96);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.82), rgba(241, 245, 249, 0.92));
}

.app-rail--admin .app-nav__item {
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(252, 253, 255, 0.78), rgba(241, 245, 249, 0.9));
}

.app-rail--admin .app-nav__item.router-link-active {
  border-color: rgba(49, 70, 95, 0.18);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(238, 243, 249, 0.98));
  box-shadow: 0 10px 18px rgba(29, 44, 70, 0.05);
}

.app-header--admin {
  background:
    linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  border-color: rgba(196, 206, 218, 0.98);
}

.header-status--admin {
  border-color: rgba(49, 70, 95, 0.14);
  color: #42556d;
}

.header-status--admin i {
  background: #31465f;
}

.system-band--admin {
  background: linear-gradient(180deg, rgba(249, 251, 253, 0.98), rgba(242, 246, 250, 0.98));
  border-color: rgba(196, 206, 218, 0.98);
}

.system-band--admin .system-band__item strong {
  color: #2c3948;
}

.app-workspace--admin {
  padding-top: 14px;
}

@media (max-width: 1180px) {
  .app-shell {
    grid-template-columns: 1fr;
  }

  .app-shell::before {
    inset: 12px;
  }

  .app-rail {
    grid-template-rows: auto auto auto;
    border-right: none;
    border-bottom: 1px solid rgba(218, 224, 233, 0.96);
  }

  .app-nav {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .system-band {
    grid-template-columns: 1fr;
  }

  .system-band__item {
    border-right: none;
    border-bottom: 1px solid rgba(226, 231, 238, 0.96);
  }

  .system-band__item:last-child {
    border-bottom: none;
  }
}

@media (max-width: 860px) {
  .app-frame,
  .login-scene {
    padding: 16px;
  }

  .app-header,
  .app-header__title-row,
  .app-header__tools,
  .page-caption-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .app-nav {
    grid-template-columns: 1fr;
  }
}
</style>
