<!-- AppSidebar — fixed left nav. Items + title change with role
     (admin / manager / employee). Emits viewChange up to the page. -->
<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  Archive,
  BookOpen,
  ChevronRight,
  FolderOpen,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  ShieldCheck,
  Users,
  UserCheck,
} from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'

defineProps<{ currentView: string }>()
const emit = defineEmits<{ (e: 'viewChange', view: string): void }>()

const auth = useAuthStore()
const router = useRouter()

// ── NAV ITEMS PER ROLE ───────────────────────────────────────
const adminNavItems = [
  { icon: LayoutDashboard, label: 'Dashboard', view: 'dashboard' },
  { icon: Users, label: 'Students', view: 'students' },
  { icon: ShieldCheck, label: 'Team & Roles', view: 'team' },
  { icon: Archive, label: 'Archived', view: 'archived' },
]

const managerNavItems = [
  { icon: LayoutDashboard, label: 'Dashboard', view: 'dashboard' },
  { icon: Users, label: 'All Students', view: 'students' },
  { icon: UserCheck, label: 'Employees', view: 'employees' },
  { icon: Archive, label: 'Archived', view: 'archived' },
]

const employeeNavItems = [
  { icon: BookOpen, label: 'My Students', view: 'my-students' },
  { icon: FolderOpen, label: 'My Archive', view: 'my-archive' },
]

// ── ROLE-BASED DERIVATIONS ───────────────────────────────────
// Pick the nav set + header labels based on current auth state.
const navItems = computed(() => {
  if (auth.isSuperAdmin) return adminNavItems
  if (auth.isManager) return managerNavItems
  return employeeNavItems
})

const panelLabel = computed(() => {
  if (auth.isSuperAdmin) return 'Super Admin Panel'
  if (auth.isManager) return 'Manager Panel'
  return 'Employee Panel'
})

const displayRole = computed(() => {
  if (auth.isSuperAdmin) return 'Super Admin'
  if (auth.isManager) return 'Manager'
  return 'Admissions Advisor'
})

// Build 2-letter avatar initials from the user's name.
const displayInitials = computed(() => auth.userName.split(' ').map((name) => name[0]).join('').slice(0, 2).toUpperCase() || 'U')

// ── ACTIONS ──────────────────────────────────────────────────
async function handleLogout() {
  await auth.logout()
  router.push('/')
}
</script>

<template>
  <aside class="fixed left-0 top-0 z-50 flex h-screen flex-col" style="width: 260px; background-color: #162340">
    <!-- Brand header -->
    <div class="border-b border-white/10 px-6 py-6">
      <div class="flex items-center gap-3">
        <div class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl" style="background-color: #B8966A">
          <GraduationCap class="h-5 w-5 text-white" />
        </div>
        <div>
          <div class="text-sm font-semibold leading-tight text-white" style="font-family: Sora, sans-serif">University CRM</div>
          <div class="text-xs leading-tight" style="color: #B8966A">Admissions Suite</div>
        </div>
      </div>
    </div>

    <!-- Role panel label -->
    <div class="px-4 py-4">
      <div
        class="rounded-lg px-3 py-2 text-xs font-medium uppercase tracking-wider"
        style="background-color: rgba(184, 150, 106, 0.15); color: #B8966A"
      >
        {{ panelLabel }}
      </div>
    </div>

    <!-- Nav items (role-dependent) -->
    <nav class="flex-1 overflow-y-auto px-3 pb-4">
      <div class="space-y-1">
        <button
          v-for="item in navItems"
          :key="item.view"
          @click="emit('viewChange', item.view)"
          class="group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all"
          :class="currentView === item.view ? 'text-white' : 'text-white/60 hover:bg-white/5 hover:text-white'"
          :style="currentView === item.view ? { backgroundColor: 'rgba(184,150,106,0.2)' } : {}"
        >
          <component
            :is="item.icon"
            class="h-[18px] w-[18px] flex-shrink-0 transition-colors"
            :class="currentView === item.view ? 'text-[#B8966A]' : 'text-white/50 group-hover:text-white/80'"
          />
          <span class="flex-1 text-left font-medium">{{ item.label }}</span>
          <ChevronRight v-if="currentView === item.view" class="h-3.5 w-3.5" style="color: #B8966A" />
        </button>
      </div>
    </nav>

    <div class="mx-4 border-t border-white/10" />

    <!-- User card + sign-out -->
    <div class="px-4 py-4">
      <div class="mb-3 flex items-center gap-3">
        <div
          class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl text-xs font-semibold text-white"
          style="background-color: #B8966A; font-family: Sora, sans-serif"
        >
          {{ displayInitials }}
        </div>
        <div class="min-w-0 flex-1">
          <div class="truncate text-sm font-medium text-white">{{ auth.userName }}</div>
          <div class="truncate text-xs text-white/50">{{ displayRole }}</div>
        </div>
      </div>

      <button
        @click="handleLogout"
        class="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-sm text-white/60 transition-all hover:bg-white/5 hover:text-white"
      >
        <LogOut class="h-4 w-4" />
        Sign Out
      </button>
    </div>
  </aside>
</template>
