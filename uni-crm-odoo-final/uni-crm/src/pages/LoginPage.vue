<!--
  LoginPage — staff sign-in (Admin / Manager / Employee).
  Students never see this page; they enter via /portal/:token.
  On success, routes the user to their role-appropriate dashboard.
-->
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { GraduationCap, Eye, EyeOff, CheckCircle2, Users, FileText, BarChart3, Zap } from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'

// ── FORM STATE ───────────────────────────────────────────────
const router = useRouter()
const auth = useAuthStore()
const username = ref('')
const password = ref('')
const showPassword = ref(false)

// Static list shown on the hero panel (left side).
const FEATURE_PILLS = [
  { icon: Users, label: 'Smart Student Tracking' },
  { icon: FileText, label: 'Document Management' },
  { icon: BarChart3, label: 'Performance Analytics' },
  { icon: Zap, label: 'Real-time Updates' },
]

// ── SUBMIT ───────────────────────────────────────────────────
// auth.login populates role flags; we route accordingly.
async function handleSubmit(e: Event) {
  e.preventDefault()
  if (!username.value.trim() || !password.value.trim()) return
  const ok = await auth.login(username.value, password.value)
  if (ok) {
    if (auth.isSuperAdmin) router.push('/admin')
    else if (auth.isManager) router.push('/manager')
    else router.push('/employee')
  }
}
</script>

<template>
  <div class="min-h-screen flex" style="font-family: 'Plus Jakarta Sans', sans-serif; min-width: 1024px">
    <!-- LEFT PANEL: brand, tagline, feature pills, Mandela quote -->
    <div class="flex flex-col justify-between p-12 relative overflow-hidden" style="background-color: #162340; width: 42%">
      <div class="absolute top-0 right-0 w-72 h-72 rounded-full opacity-5" style="background-color: #B8966A; transform: translate(30%, -30%)" />
      <div class="absolute bottom-0 left-0 w-96 h-96 rounded-full opacity-5" style="background-color: #B8966A; transform: translate(-30%, 30%)" />
      <div class="relative z-10">
        <div class="flex items-center gap-3 mb-10">
          <div class="w-11 h-11 rounded-xl flex items-center justify-center" style="background-color: #B8966A">
            <GraduationCap class="w-6 h-6 text-white" />
          </div>
          <div>
            <div class="text-white font-semibold text-lg" style="font-family: Sora, sans-serif">University CRM</div>
            <div class="text-xs" style="color: #B8966A">Admissions Management Suite</div>
          </div>
        </div>
        <h1 class="text-white mb-3" style="font-family: Sora, sans-serif; font-size: 32px; font-weight: 700; line-height: 1.2">
          Enroll smarter.<br /><span style="color: #B8966A">Track every step.</span>
        </h1>
        <p class="text-white/60 text-sm leading-relaxed mb-10 max-w-xs">The complete admissions management platform for modern universities.</p>
        <div class="space-y-3">
          <div v-for="item in FEATURE_PILLS" :key="item.label" class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" style="background-color: rgba(184,150,106,0.2)">
              <component :is="item.icon" class="w-4 h-4" style="color: #B8966A" />
            </div>
            <span class="text-white/80 text-sm">{{ item.label }}</span>
            <CheckCircle2 class="w-4 h-4 ml-auto" style="color: #B8966A" />
          </div>
        </div>
      </div>
      <div class="relative z-10 border-l-2 pl-5" style="border-color: #B8966A">
        <p class="text-white/70 text-sm italic leading-relaxed mb-2">"Education is the most powerful weapon which you can use to change the world."</p>
        <p class="text-xs font-medium" style="color: #B8966A">— Nelson Mandela</p>
      </div>
    </div>

    <!-- RIGHT PANEL: username + password form -->
    <div class="flex flex-col justify-center px-16 py-12 flex-1" style="background-color: #FAFAF8">
      <div class="max-w-sm w-full mx-auto">
        <div class="mb-8">
          <h2 class="text-[#162340] mb-1" style="font-family: Sora, sans-serif; font-size: 28px; font-weight: 700">
            Welcome back.
          </h2>
          <p class="text-gray-500 text-sm">
            Manager & Employee sign in. Students: use the link sent by your advisor.
          </p>
        </div>

        <!-- Info box -->
        <div class="mb-5 px-4 py-3 rounded-xl text-xs" style="background-color: rgba(22,35,64,0.05); color: #162340">
          <span class="font-semibold">ℹ Note:</span> Use your Odoo username or email address to sign in.
        </div>

        <form @submit="handleSubmit" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">Username or Email</label>
            <input v-model="username" type="text" placeholder="your.email@example.com" required
              class="w-full px-4 py-3 rounded-xl border border-gray-200 bg-white text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#162340]/20 focus:border-[#162340]/40 transition-all" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">Password</label>
            <div class="relative">
              <input v-model="password" :type="showPassword ? 'text' : 'password'" placeholder="Your password" required
                class="w-full px-4 py-3 pr-11 rounded-xl border border-gray-200 bg-white text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#162340]/20 focus:border-[#162340]/40 transition-all" />
              <button type="button" @click="showPassword = !showPassword" class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                <EyeOff v-if="showPassword" class="w-4 h-4" /><Eye v-else class="w-4 h-4" />
              </button>
            </div>
          </div>
          <p v-if="auth.error" class="text-red-600 text-xs bg-red-50 px-3 py-2 rounded-lg">{{ auth.error }}</p>
          <button type="submit" :disabled="auth.loading"
            class="w-full py-3 rounded-xl text-white text-sm font-semibold transition-all disabled:opacity-70 hover:opacity-90"
            style="background-color: #162340">
            <span v-if="auth.loading" class="flex items-center justify-center gap-2">
              <svg class="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Signing in...
            </span>
            <span v-else>Sign In →</span>
          </button>
        </form>

        <p class="mt-6 text-xs text-center text-gray-400">University CRM · Powered by Odoo · v2.4</p>
      </div>
    </div>
  </div>
</template>