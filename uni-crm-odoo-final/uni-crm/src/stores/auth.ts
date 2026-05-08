// stores/auth.ts — Session + role state. Used by the router guard,
// sidebar, login page and every page header.
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { callKw, getSessionInfo, odooLogin, odooLogout, jsonrpcCall } from '../services/odoo'

export const useAuthStore = defineStore('auth', () => {
  // ── STATE ──────────────────────────────────────────────────
  const uid = ref<number | null>(null)
  const userName = ref('')
  const userLogin = ref('')
  const isManager = ref(false)
  const isSuperAdmin = ref(false)
  const loading = ref(false)
  const error = ref('')
  const needsPasswordSetup = ref(false)
  const pendingLogin = ref('')

  const isLoggedIn = computed(() => !!uid.value)

  // ── ROLE DETECTION ─────────────────────────────────────────
  // Role flags come from Odoo groups: base.group_system = admin,
  // university_crm.group_university_manager = manager.
  async function checkManagerGroup() {
    try {
      const result = await callKw('res.users', 'has_group', [[uid.value], 'university_crm.group_university_manager'], {})
      isManager.value = !!result
    } catch {
      isManager.value = false
    }
  }

  async function checkAdminGroup() {
    try {
      const result = await callKw('res.users', 'has_group', [[uid.value], 'base.group_system'], {})
      isSuperAdmin.value = !!result
    } catch {
      isSuperAdmin.value = false
    }
  }

  async function syncRoles(session: any) {
    isSuperAdmin.value = !!session?.is_admin
    await Promise.all([checkManagerGroup(), isSuperAdmin.value ? Promise.resolve() : checkAdminGroup()])
  }

  // ── CUSTOM PASSWORD (first-time setup) ─────────────────────
  // Talks to the addon's /api/auth controllers for the flow where
  // a freshly-invited user sets their own password before first login.
  async function checkPasswordStatus(loginStr: string) {
    // Check if user has set a custom password.
    try {
      const result = await jsonrpcCall('/api/auth/check-password', { login: loginStr })
      if (result.error) {
        error.value = result.error
        return { hasPassword: false, found: false }
      }
      return { hasPassword: result.has_custom_password, found: true }
    } catch (e: any) {
      error.value = e.message || 'Failed to check password status'
      return { hasPassword: false, found: false }
    }
  }

  async function setCustomPassword(loginStr: string, password: string, password2: string) {
    // Set custom password for first-time login.
    loading.value = true
    error.value = ''
    try {
      const result = await jsonrpcCall('/api/auth/set-password', { 
        login: loginStr,
        password,
        password2
      })
      if (result.error) {
        error.value = result.error
        return false
      }
      needsPasswordSetup.value = false
      return true
    } catch (e: any) {
      error.value = e.message || 'Failed to set password'
      return false
    } finally {
      loading.value = false
    }
  }

  // ── LOGIN / LOGOUT / SESSION ───────────────────────────────
  // login() calls /web/session/authenticate, then syncs role flags.
  async function login(loginStr: string, password: string) {
    loading.value = true
    error.value = ''
    try {
      const result = await odooLogin(loginStr, password)
      if (result && result.uid) {
        uid.value = result.uid
        userName.value = result.name || loginStr
        userLogin.value = loginStr
        needsPasswordSetup.value = false
        await syncRoles(result)
        return true
      }
      error.value = 'Invalid credentials'
      return false
    } catch (e: any) {
      error.value = 'Invalid credentials'
      return false
    } finally {
      loading.value = false
    }
  }

  // Password change for already-signed-in users (PasswordChangeModal).
  async function changePassword(oldPassword: string, newPassword: string, newPassword2: string) {
    // Change password for logged-in user.
    loading.value = true
    error.value = ''
    try {
      const result = await jsonrpcCall('/api/auth/change-password', {
        old_password: oldPassword,
        new_password: newPassword,
        new_password2: newPassword2,
      })
      if (result.error) {
        error.value = result.error
        return false
      }
      return true
    } catch (e: any) {
      error.value = e.message || 'Failed to change password'
      return false
    } finally {
      loading.value = false
    }
  }

  // Rehydrates state on hard refresh when Odoo still has a cookie.
  async function restoreSession() {
    try {
      const info = await getSessionInfo()
      if (info && info.uid) {
        uid.value = info.uid
        userName.value = info.name || ''
        userLogin.value = info.username || ''
        await syncRoles(info)
        return true
      }
    } catch {
      // Ignore session restore errors and let the router redirect to login.
    }
    return false
  }

  // Clears server session then wipes local state.
  async function logout() {
    try {
      await odooLogout()
    } catch {
      // Ignore logout errors and clear local state anyway.
    }

    uid.value = null
    userName.value = ''
    userLogin.value = ''
    isManager.value = false
    isSuperAdmin.value = false
    needsPasswordSetup.value = false
    pendingLogin.value = ''
  }

  return {
    error,
    isLoggedIn,
    isManager,
    isSuperAdmin,
    loading,
    uid,
    userLogin,
    userName,
    needsPasswordSetup,
    pendingLogin,
    login,
    logout,
    restoreSession,
    checkPasswordStatus,
    setCustomPassword,
    changePassword,
  }
})
