<!-- PasswordChangeModal — logged-in user changes their own password.
     Calls auth.changePassword which hits the addon's /api/auth endpoint. -->
<script setup lang="ts">
import { ref } from 'vue'
import { X, Eye, EyeOff } from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const auth = useAuthStore()
// ── LOCAL FORM STATE ─────────────────────────────────────────
const oldPassword = ref('')
const newPassword = ref('')
const newPassword2 = ref('')
const showOldPassword = ref(false)
const showNewPassword = ref(false)
const showNewPassword2 = ref(false)
const success = ref(false)

// ── SUBMIT ───────────────────────────────────────────────────
// Runs client-side checks, then delegates to auth.changePassword.
// Closes the modal 2s after a successful change.
async function handleSubmit(e: Event) {
  e.preventDefault()
  auth.error = ''
  success.value = false
  
  if (!oldPassword.value.trim()) {
    auth.error = 'Current password is required'
    return
  }
  if (!newPassword.value.trim() || !newPassword2.value.trim()) {
    auth.error = 'Both password fields are required'
    return
  }
  if (newPassword.value !== newPassword2.value) {
    auth.error = 'New passwords do not match'
    return
  }
  if (newPassword.value.length < 6) {
    auth.error = 'New password must be at least 6 characters'
    return
  }
  
  const ok = await auth.changePassword(oldPassword.value, newPassword.value, newPassword2.value)
  if (ok) {
    success.value = true
    setTimeout(() => {
      resetForm()
      emit('close')
    }, 2000)
  }
}

// Clears the form back to initial state.
function resetForm() {
  oldPassword.value = ''
  newPassword.value = ''
  newPassword2.value = ''
  showOldPassword.value = false
  showNewPassword.value = false
  showNewPassword2.value = false
  auth.error = ''
  success.value = false
}

function handleClose() {
  resetForm()
  emit('close')
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
    <div class="bg-white rounded-xl shadow-xl max-w-sm w-full mx-4">
      <!-- Header -->
      <div class="flex items-center justify-between p-6 border-b border-gray-200">
        <h3 class="text-lg font-semibold text-gray-900">Change Password</h3>
        <button @click="handleClose" type="button" class="text-gray-400 hover:text-gray-600">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Body -->
      <form @submit="handleSubmit" class="p-6 space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1.5">Current Password</label>
          <div class="relative">
            <input v-model="oldPassword" :type="showOldPassword ? 'text' : 'password'" 
              placeholder="Enter your current password" required
              class="w-full px-4 py-2.5 rounded-lg border border-gray-200 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
            <button type="button" @click="showOldPassword = !showOldPassword" 
              class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
              <EyeOff v-if="showOldPassword" class="w-4 h-4" />
              <Eye v-else class="w-4 h-4" />
            </button>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1.5">New Password</label>
          <div class="relative">
            <input v-model="newPassword" :type="showNewPassword ? 'text' : 'password'" 
              placeholder="Enter new password" required
              class="w-full px-4 py-2.5 rounded-lg border border-gray-200 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
            <button type="button" @click="showNewPassword = !showNewPassword" 
              class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
              <EyeOff v-if="showNewPassword" class="w-4 h-4" />
              <Eye v-else class="w-4 h-4" />
            </button>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1.5">Confirm New Password</label>
          <div class="relative">
            <input v-model="newPassword2" :type="showNewPassword2 ? 'text' : 'password'" 
              placeholder="Confirm new password" required
              class="w-full px-4 py-2.5 rounded-lg border border-gray-200 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
            <button type="button" @click="showNewPassword2 = !showNewPassword2" 
              class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
              <EyeOff v-if="showNewPassword2" class="w-4 h-4" />
              <Eye v-else class="w-4 h-4" />
            </button>
          </div>
        </div>

        <div v-if="auth.error" class="p-3 rounded-lg bg-red-50 text-red-600 text-sm">
          {{ auth.error }}
        </div>

        <div v-if="success" class="p-3 rounded-lg bg-green-50 text-green-600 text-sm">
          ✓ Password changed successfully! Closing...
        </div>

        <div class="flex gap-3 pt-4">
          <button type="button" @click="handleClose" 
            class="flex-1 px-4 py-2.5 rounded-lg border border-gray-200 text-gray-700 font-medium hover:bg-gray-50 transition-colors">
            Cancel
          </button>
          <button type="submit" :disabled="auth.loading || success"
            class="flex-1 px-4 py-2.5 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2">
            <svg v-if="auth.loading" class="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            <span v-if="auth.loading">Saving...</span>
            <span v-else>Change Password</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
