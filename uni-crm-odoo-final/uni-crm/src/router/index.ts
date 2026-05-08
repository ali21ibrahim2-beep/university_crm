// router/index.ts — Routes + auth guard. Base "/app/" matches the
// Odoo controller mount. Role flags live in route meta.
import { createRouter, createWebHistory } from 'vue-router'
import AdminDashboard from '../pages/AdminDashboard.vue'
import EmployeeDashboard from '../pages/EmployeeDashboard.vue'
import LoginPage from '../pages/LoginPage.vue'
import ManagerDashboard from '../pages/ManagerDashboard.vue'
import StudentDetail from '../pages/StudentDetail.vue'
import StudentPortal from '../pages/StudentPortal.vue'
import { useAuthStore } from '../stores/auth'

// ── ROUTE TABLE ──────────────────────────────────────────────
// /portal/:token is public; everything else needs a session.
const router = createRouter({
  history: createWebHistory("/app/"),
  routes: [
    { path: '/', component: LoginPage },
    { path: '/admin', component: AdminDashboard, meta: { requiresAuth: true, requiresAdmin: true } },
    { path: '/manager', component: ManagerDashboard, meta: { requiresAuth: true, requiresManager: true } },
    { path: '/employee', component: EmployeeDashboard, meta: { requiresAuth: true } },
    { path: '/portal/:token', component: StudentPortal },
    { path: '/student/:id', component: StudentDetail, meta: { requiresAuth: true } },
  ],
})

// ── AUTH GUARD ───────────────────────────────────────────────
// Rehydrates Vue state from the Odoo cookie on hard refresh, then
// bounces users down to the highest dashboard their role can see.
router.beforeEach(async (to) => {
  if (!to.meta.requiresAuth) return true

  const auth = useAuthStore()
  if (!auth.isLoggedIn) {
    const restored = await auth.restoreSession()
    if (!restored) return '/'
  }

  if (to.meta.requiresAdmin && !auth.isSuperAdmin) {
    return auth.isManager ? '/manager' : '/employee'
  }

  if (to.meta.requiresManager && !auth.isManager) {
    return auth.isSuperAdmin ? '/admin' : '/employee'
  }

  return true
})

export default router
