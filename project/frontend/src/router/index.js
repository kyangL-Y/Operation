import { createRouter, createWebHistory } from "vue-router";

const routes = [
  { path: "/login", component: () => import("../views/LoginView.vue") },
  { path: "/", component: () => import("../views/DashboardView.vue") },
  { path: "/ask", component: () => import("../views/AskView.vue") },
  { path: "/kb", component: () => import("../views/KnowledgeView.vue") },
  { path: "/profile", component: () => import("../views/ProfileView.vue") },
  { path: "/data", component: () => import("../views/DataManageView.vue") },
  { path: "/notifications", component: () => import("../views/NotificationView.vue") },
  { path: "/help", component: () => import("../views/HelpView.vue") },
  { path: "/about", component: () => import("../views/AboutView.vue") },
  { path: "/admin", component: () => import("../views/AdminView.vue"), meta: { requiresAdmin: true } },
  { path: "/admin/settings", component: () => import("../views/SettingsView.vue"), meta: { requiresAdmin: true } },
  { path: "/admin/audit", component: () => import("../views/AuditLogView.vue"), meta: { requiresAdmin: true } }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

router.beforeEach((to) => {
  if (typeof to.query.authToken === "string" && to.query.authToken) {
    localStorage.setItem("auth_token", to.query.authToken);
    localStorage.setItem("auth_username", typeof to.query.authUsername === "string" ? to.query.authUsername : "");
    localStorage.setItem("auth_display_name", typeof to.query.authDisplayName === "string" ? to.query.authDisplayName : "");
    localStorage.setItem("auth_role", typeof to.query.authRole === "string" ? to.query.authRole : "");
  }
  const token = localStorage.getItem("auth_token");
  const role = localStorage.getItem("auth_role");
  if (!token && to.path !== "/login") {
    return "/login";
  }
  if (to.meta?.requiresAdmin && role !== "ADMIN") {
    return "/";
  }
});

export default router;
