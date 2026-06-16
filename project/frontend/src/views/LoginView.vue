<template>
  <div class="login-shell">
    <section class="login-shell__meta">
      <div class="login-meta-block">
        <p class="eyebrow">系统访问</p>
        <h2>酒店运营支持系统</h2>
        <p class="muted">登录后直接进入工作系统。页面只保留访问说明、演示账号和登录表单。</p>
      </div>

      <div class="login-meta-block">
        <p class="workspace-label">系统范围</p>
        <ul class="login-brief-list">
          <li>经营总览、风险判断与预测摘要</li>
          <li>运营咨询、参考资料与连续追问</li>
          <li>资料录入、目录查询和长文阅读</li>
          <li>管理员账号、权限控制与审计追踪</li>
        </ul>
      </div>

      <div class="login-fact-strip">
        <div class="login-fact-card">
          <span>系统闭环</span>
          <strong>运营数据 → 经营预测 → 处理建议 → 经验复盘</strong>
        </div>
        <div class="login-fact-card">
          <span>预测范围</span>
          <strong>系统重点关注入住率、营收和订单取消风险</strong>
        </div>
        <div class="login-fact-card">
          <span>咨询范围</span>
          <strong>问答工作台负责查询资料、整理依据和补充建议</strong>
        </div>
      </div>

      <div class="login-account-strip">
        <div>
          <span class="login-account-strip__label">管理员</span>
          <strong>admin / admin123</strong>
        </div>
        <div>
          <span class="login-account-strip__label">经理</span>
          <strong>manager / manager123</strong>
        </div>
        <div>
          <span class="login-account-strip__label">员工</span>
          <strong>staff / staff123</strong>
        </div>
      </div>
    </section>

    <section class="login-shell__form">
      <div class="form-tabs">
        <button
          type="button"
          class="ghost-btn"
          :class="{ 'ghost-btn--active': mode === 'login' }"
          @click="mode = 'login'"
        >
          账号登录
        </button>
        <button
          type="button"
          class="ghost-btn"
          :class="{ 'ghost-btn--active': mode === 'register' }"
          @click="mode = 'register'"
        >
          新用户注册
        </button>
      </div>

      <div class="login-form-head">
        <p class="workspace-label">{{ mode === "login" ? "账号登录" : "账号注册" }}</p>
        <h3>{{ mode === "login" ? "登录系统" : "创建账号" }}</h3>
        <p class="muted">
          {{ mode === "login"
            ? "建议先登录演示账号，确认首页经营预测、处理建议与问答工作台都可正常访问。"
            : "注册完成后会自动进入系统，并以普通员工角色进入工作台。"
          }}
        </p>
      </div>

      <div class="login-form-fields">
        <input v-if="mode === 'register'" v-model.trim="displayName" placeholder="姓名，例如：前台主管" />
        <input v-model.trim="username" placeholder="用户名" />
        <input v-model="password" placeholder="密码" type="password" />
        <input
          v-if="mode === 'register'"
          v-model="confirmPassword"
          placeholder="确认密码"
          type="password"
        />
      </div>

      <div class="login-form-actions">
        <button type="button" :disabled="loading" @click="mode === 'login' ? login() : register()">
          {{ loading ? "处理中..." : mode === "login" ? "登录并进入系统" : "注册并进入系统" }}
        </button>
        <router-link class="ghost-btn" :to="mode === 'login' ? '/login?mode=register' : '/login'">
          {{ mode === "login" ? "没有账号，去注册" : "已有账号，去登录" }}
        </router-link>
      </div>

      <p class="status-text">{{ message }}</p>
    </section>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import http from "../api/http";

const router = useRouter();
const route = useRoute();
const mode = ref(route.query.mode === "register" ? "register" : "login");
const displayName = ref("");
const username = ref("admin");
const password = ref("admin123");
const confirmPassword = ref("");
const message = ref("准备就绪，可直接登录演示账号。");
const loading = ref(false);

const demoAccounts = {
  admin: { password: "admin123", displayName: "系统管理员", role: "ADMIN" },
  manager: { password: "manager123", displayName: "值班经理", role: "MANAGER" },
  staff: { password: "staff123", displayName: "前台员工", role: "STAFF" }
};

watch(
  () => route.query.mode,
  (value) => {
    mode.value = value === "register" ? "register" : "login";
  }
);

function persistLogin(result) {
  localStorage.setItem("auth_token", result.token);
  localStorage.setItem("auth_username", result.username || "");
  localStorage.setItem("auth_display_name", result.displayName || "");
  localStorage.setItem("auth_role", result.role || "");
  window.dispatchEvent(new Event("auth-changed"));
}

async function login() {
  loading.value = true;
  try {
    const { data } = await http.post("/auth/login", {
      username: username.value,
      password: password.value
    });
    const result = data?.data;
    if (result?.token) {
      persistLogin(result);
      message.value = "登录成功，正在进入系统。";
      router.push("/");
    } else if (tryDemoLogin()) {
      message.value = "已使用本地演示账号进入系统。";
      router.push("/");
    } else {
      message.value = "暂未完成登录，请稍后再试。";
    }
  } catch (err) {
    if (tryDemoLogin()) {
      message.value = err?.response
        ? "后端账号校验未通过，已使用本地演示账号进入系统。"
        : "后端未连接，已使用本地演示账号进入系统。";
      router.push("/");
    } else {
      message.value = err?.response?.data?.message || "暂未完成登录，请检查账号密码。";
    }
  } finally {
    loading.value = false;
  }
}

async function register() {
  if (!displayName.value.trim()) {
    message.value = "请输入姓名后再注册。";
    return;
  }
  if (password.value !== confirmPassword.value) {
    message.value = "两次输入的密码不一致。";
    return;
  }

  loading.value = true;
  try {
    const { data } = await http.post("/auth/register", {
      displayName: displayName.value,
      username: username.value,
      password: password.value
    });
    const result = data?.data;
    if (result?.token) {
      persistLogin(result);
      message.value = "注册成功，正在进入系统。";
      router.push("/");
    } else {
      message.value = "暂未完成注册，请稍后再试。";
    }
  } catch (err) {
    if (!err?.response) {
      persistLogin({
        token: `demo-token-${Date.now()}`,
        username: username.value,
        displayName: displayName.value,
        role: "STAFF"
      });
      message.value = "后端未连接，已创建本地演示账号。";
      router.push("/");
    } else {
      message.value = err?.response?.data?.message || "暂未完成注册，请稍后重试。";
    }
  } finally {
    loading.value = false;
  }
}

function tryDemoLogin() {
  const account = demoAccounts[username.value];
  if (!account || account.password !== password.value) return false;
  persistLogin({
    token: `demo-token-${username.value}`,
    username: username.value,
    displayName: account.displayName,
    role: account.role
  });
  return true;
}
</script>

<style scoped>
.login-shell {
  position: relative;
  z-index: 1;
  width: min(1100px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(400px, 0.88fr);
  border-radius: var(--radius-xl);
  overflow: hidden;
  background: var(--bg-panel);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-xl);
}

.login-shell__meta,
.login-shell__form {
  padding: var(--spacing-2xl);
}

.login-shell__meta {
  display: grid;
  gap: var(--spacing-xl);
  background: var(--bg-panel-muted);
  border-right: 1px solid var(--line);
}

.login-meta-block,
.login-form-head,
.login-form-fields {
  display: grid;
  gap: var(--spacing-md);
}

.login-shell__meta h2,
.login-shell__form h3 {
  margin: 0;
  color: var(--ink-strong);
  font-weight: 700;
}

.login-brief-list {
  margin: 0;
  color: var(--ink);
  line-height: 1.75;
}

.login-fact-strip {
  display: grid;
  gap: var(--spacing-md);
}

.login-fact-card {
  display: grid;
  gap: var(--spacing-sm);
  padding: var(--spacing-lg);
  border-radius: var(--radius-md);
  background: var(--bg-panel);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-xs);
  transition: all var(--transition-base);
}

.login-fact-card:hover {
  box-shadow: var(--shadow-sm);
  transform: translateY(-2px);
  border-color: var(--line-strong);
}

.login-fact-card span {
  color: var(--ink-soft);
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-weight: 600;
}

.login-fact-card strong {
  color: var(--ink-strong);
  font-size: 13px;
  line-height: 1.65;
  font-weight: 600;
}

.login-account-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--spacing-md);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--line);
}

.login-account-strip > div {
  padding: var(--spacing-md);
  border-radius: var(--radius-sm);
  background: var(--bg-panel);
  border: 1px solid var(--line);
  transition: all var(--transition-base);
}

.login-account-strip > div:hover {
  box-shadow: var(--shadow-sm);
  transform: translateY(-2px);
  border-color: var(--accent);
}

.login-account-strip__label {
  color: var(--ink-soft);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 600;
}

.login-account-strip strong {
  display: block;
  margin-top: var(--spacing-sm);
  color: var(--accent);
  font-size: 13px;
  font-weight: 600;
}

.login-shell__form {
  display: grid;
  align-content: center;
  gap: var(--spacing-lg);
  background: var(--bg-panel);
}

.form-tabs,
.login-form-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.ghost-btn--active {
  color: #ffffff;
  background: var(--accent);
  border-color: var(--accent);
  box-shadow: var(--shadow-sm);
}

@media (max-width: 1040px) {
  .login-shell,
  .login-account-strip {
    grid-template-columns: 1fr;
  }

  .login-shell__meta {
    border-right: none;
    border-bottom: 1px solid rgba(224, 231, 241, 0.96);
  }
}

@media (max-width: 768px) {
  .login-shell__meta,
  .login-shell__form {
    padding: 22px;
  }
}
</style>
