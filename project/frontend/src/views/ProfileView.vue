<template>
  <div class="page-stack">
    <section class="workspace-card">
      <div class="section-header">
        <div class="section-header__copy">
          <p class="workspace-label">个人中心</p>
          <h3 class="section-title">个人中心</h3>
        </div>
      </div>

      <div class="profile-fact-strip">
        <article class="profile-fact-card">
          <span>当前身份</span>
          <strong>{{ roleLabel }} · {{ statusLabel }}</strong>
        </article>
        <article class="profile-fact-card">
          <span>账号同步</span>
          <strong>修改后即时广播</strong>
        </article>
        <article class="profile-fact-card">
          <span>安全动作</span>
          <strong>改密后重新登录</strong>
        </article>
      </div>

      <div class="profile-grid">
        <div class="profile-info">
          <div class="profile-avatar">{{ avatarInitial }}</div>
          <div class="profile-details">
            <h4>{{ userInfo.displayName || userInfo.username }}</h4>
            <p>@{{ userInfo.username }}</p>
            <div class="stat-pills">
              <span class="badge" :class="roleClass">{{ roleLabel }}</span>
              <span class="stat-pill">{{ statusLabel }}</span>
            </div>
          </div>
        </div>

        <div class="profile-meta">
          <div class="meta-item">
            <span>账号编号</span>
            <strong>{{ userInfo.id || '-' }}</strong>
          </div>
          <div class="meta-item">
            <span>创建时间</span>
            <strong>{{ formatDate(userInfo.createdAt) }}</strong>
          </div>
        </div>
      </div>
    </section>

    <div class="surface-grid--equal">
      <section class="workspace-card">
        <div class="section-header">
          <div class="section-header__copy">
            <p class="workspace-label">显示名称</p>
            <h3 class="panel-title">修改显示名称</h3>
          </div>
        </div>

        <form @submit.prevent="updateDisplayName" class="form-stack">
          <div class="form-field">
            <label for="displayName">新显示名称</label>
            <input
              id="displayName"
              v-model="profileForm.displayName"
              type="text"
              placeholder="请输入新的显示名称"
              required
            />
          </div>
          <div class="action-row">
            <button type="submit" :disabled="profileLoading">
              {{ profileLoading ? '保存中...' : '保存名称' }}
            </button>
          </div>
          <p v-if="profileMessage" class="notice" :class="profileSuccess ? 'notice--success' : 'notice--danger'">
            {{ profileMessage }}
          </p>
        </form>
      </section>

      <section class="workspace-card">
        <div class="section-header">
          <div class="section-header__copy">
            <p class="workspace-label">密码管理</p>
            <h3 class="panel-title">修改密码</h3>
          </div>
        </div>

        <form @submit.prevent="updatePassword" class="form-stack">
          <div class="form-field">
            <label for="oldPassword">当前密码</label>
            <input
              id="oldPassword"
              v-model="passwordForm.oldPassword"
              type="password"
              placeholder="请输入当前密码"
              required
            />
          </div>
          <div class="form-field">
            <label for="newPassword">新密码</label>
            <input
              id="newPassword"
              v-model="passwordForm.newPassword"
              type="password"
              placeholder="请输入新密码（至少6位）"
              required
              minlength="6"
            />
          </div>
          <div class="form-field">
            <label for="confirmPassword">确认新密码</label>
            <input
              id="confirmPassword"
              v-model="passwordForm.confirmPassword"
              type="password"
              placeholder="请再次输入新密码"
              required
            />
          </div>
          <div class="action-row">
            <button type="submit" :disabled="passwordLoading">
              {{ passwordLoading ? '修改中...' : '修改密码' }}
            </button>
          </div>
          <p v-if="passwordMessage" class="notice" :class="passwordSuccess ? 'notice--success' : 'notice--danger'">
            {{ passwordMessage }}
          </p>
        </form>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import http from "../api/http";

const router = useRouter();

const userInfo = ref({});
const profileForm = reactive({ displayName: "" });
const passwordForm = reactive({ oldPassword: "", newPassword: "", confirmPassword: "" });

const profileLoading = ref(false);
const profileMessage = ref("");
const profileSuccess = ref(false);

const passwordLoading = ref(false);
const passwordMessage = ref("");
const passwordSuccess = ref(false);

const avatarInitial = computed(() =>
  (userInfo.value.displayName || userInfo.value.username || "U").slice(0, 1).toUpperCase()
);

const roleLabel = computed(() => {
  const role = userInfo.value.role;
  if (role === "ADMIN") return "系统管理员";
  if (role === "MANAGER") return "业务管理";
  if (role === "STAFF") return "一线执行";
  return role || "未知";
});

const roleClass = computed(() => {
  const role = userInfo.value.role;
  if (role === "ADMIN") return "badge--danger";
  if (role === "MANAGER") return "badge--warning";
  return "badge--success";
});

const statusLabel = computed(() =>
  userInfo.value.status === "ACTIVE" ? "启用" : "停用"
);

function formatDate(dateStr) {
  if (!dateStr) return "-";
  const date = new Date(dateStr);
  return date.toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

async function loadUserInfo() {
  try {
    const { data } = await http.get("/auth/me");
    userInfo.value = data.data || {};
    profileForm.displayName = userInfo.value.displayName || "";
  } catch {
    router.push("/login");
  }
}

function clearStoredAuth() {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("auth_username");
  localStorage.removeItem("auth_display_name");
  localStorage.removeItem("auth_role");
  window.dispatchEvent(new Event("auth-changed"));
}

async function updateDisplayName() {
  if (!profileForm.displayName.trim()) {
    profileMessage.value = "显示名称不能为空。";
    profileSuccess.value = false;
    return;
  }

  profileLoading.value = true;
  profileMessage.value = "";

  try {
    const { data } = await http.put("/auth/profile", {
      displayName: profileForm.displayName.trim()
    });
    userInfo.value = data.data || userInfo.value;
    localStorage.setItem("auth_display_name", userInfo.value.displayName);
    window.dispatchEvent(new Event("auth-changed"));
    profileMessage.value = "显示名称修改成功。";
    profileSuccess.value = true;
  } catch (err) {
    profileMessage.value = err.response?.data?.message || "暂未保存成功，请稍后重试。";
    profileSuccess.value = false;
  } finally {
    profileLoading.value = false;
  }
}

async function updatePassword() {
  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    passwordMessage.value = "两次输入的新密码不一致。";
    passwordSuccess.value = false;
    return;
  }

  if (passwordForm.newPassword.length < 6) {
    passwordMessage.value = "新密码长度不能少于 6 位。";
    passwordSuccess.value = false;
    return;
  }

  passwordLoading.value = true;
  passwordMessage.value = "";

  try {
    await http.put("/auth/password", {
      oldPassword: passwordForm.oldPassword,
      newPassword: passwordForm.newPassword
    });
    passwordMessage.value = "密码修改成功，请重新登录。";
    passwordSuccess.value = true;
    passwordForm.oldPassword = "";
    passwordForm.newPassword = "";
    passwordForm.confirmPassword = "";

    setTimeout(() => {
      clearStoredAuth();
      router.push("/login");
    }, 1500);
  } catch (err) {
    passwordMessage.value = err.response?.data?.message || "暂未修改成功，请稍后重试。";
    passwordSuccess.value = false;
  } finally {
    passwordLoading.value = false;
  }
}

onMounted(() => {
  loadUserInfo();
});
</script>

<style scoped>
.profile-fact-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.profile-fact-card {
  display: grid;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  background: var(--bg-panel-muted);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-xs);
  transition: all var(--transition-base);
}

.profile-fact-card:hover {
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
  border-color: var(--line-strong);
}

.profile-fact-card span {
  font-size: 11px;
  color: var(--ink-soft);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 700;
}

.profile-fact-card strong {
  font-size: 13px;
  color: var(--ink-strong);
}

.profile-fact-card p {
  margin: 0;
  font-size: 12px;
  color: var(--ink-soft);
  line-height: 1.6;
}

.profile-grid {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 24px;
  align-items: center;
}

.profile-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.profile-avatar {
  width: 72px;
  height: 72px;
  border-radius: 12px;
  background: linear-gradient(135deg, #4f70ab, #6b8bc7);
  color: #ffffff;
  font-size: 28px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.profile-details {
  display: grid;
  gap: 6px;
}

.profile-details h4 {
  margin: 0;
  font-size: 20px;
  color: var(--ink-strong);
}

.profile-details p {
  margin: 0;
  color: var(--ink-soft);
  font-size: 14px;
}

.profile-meta {
  display: flex;
  gap: 24px;
}

.meta-item {
  display: grid;
  gap: var(--spacing-xs);
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--radius-md);
  background: var(--bg-panel-muted);
  border: 1px solid var(--line);
  transition: all var(--transition-base);
}

.meta-item:hover {
  border-color: var(--line-strong);
  box-shadow: var(--shadow-xs);
}

.meta-item span {
  color: var(--ink-soft);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 700;
}

.meta-item strong {
  color: var(--ink-strong);
  font-size: 14px;
}

.form-stack {
  display: grid;
  gap: 16px;
}

.form-field {
  display: grid;
  gap: 6px;
}

.form-field label {
  color: var(--ink-soft);
  font-size: 13px;
  font-weight: 600;
}

.notice--success {
  color: var(--success);
  background: rgba(46, 150, 107, 0.1);
  border: 1px solid rgba(46, 150, 107, 0.2);
}

@media (max-width: 860px) {
  .profile-fact-strip,
  .profile-grid {
    grid-template-columns: 1fr;
  }

  .profile-meta {
    flex-direction: column;
    gap: 8px;
  }

  .surface-grid--equal {
    grid-template-columns: 1fr;
  }
}
</style>
