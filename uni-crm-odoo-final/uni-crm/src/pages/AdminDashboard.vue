<!-- AdminDashboard — super-admin view. Full student list + the
     Team & Roles editor (toggle Employee/Manager) + archive list. -->
<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { FileText, GraduationCap, RefreshCw, ShieldCheck, UserCheck, UserPlus2, Users, Lock } from 'lucide-vue-next'
import AppSidebar from '../components/AppSidebar.vue'
import CreateEmployeeModal from '../components/CreateEmployeeModal.vue'
import CreateStudentModal from '../components/CreateStudentModal.vue'
import PasswordChangeModal from '../components/PasswordChangeModal.vue'
import StatCard from '../components/StatCard.vue'
import StudentTable from '../components/StudentTable.vue'
import { useAuthStore } from '../stores/auth'
import { useStudentsStore } from '../stores/students'
import type { OdooUser, OdooUserRole } from '../types/odoo'

// ── VIEW STATE ───────────────────────────────────────────────
type View = 'dashboard' | 'students' | 'team' | 'archived'

const view = ref<View>('dashboard')
const showCreateModal = ref(false)
const showCreateEmployeeModal = ref(false)
const showChangePasswordModal = ref(false)
// savingUserId tracks an in-flight role update; roleDrafts mirrors
// the selected role per user so we don't fight Pinia during edits.
const savingUserId = ref<number | null>(null)
const roleDrafts = reactive<Record<number, OdooUserRole>>({})

const studentsStore = useStudentsStore()
const auth = useAuthStore()

// Keep the local roleDrafts map in sync with the users list.
watch(
  () => studentsStore.users,
  (users) => {
    for (const user of users) {
      roleDrafts[user.id] = user.role || 'employee'
    }
  },
  { immediate: true, deep: true }
)

// Prime every data source the tabs need, in parallel.
onMounted(async () => {
  await Promise.all([
    studentsStore.fetchStudents(),
    studentsStore.fetchUsers(),
    studentsStore.fetchCountries(),
  ])
})

async function refreshAll() {
  await Promise.all([
    studentsStore.fetchStudents(),
    studentsStore.fetchUsers(),
    view.value === 'archived' ? studentsStore.fetchArchived() : Promise.resolve(),
  ])
}

async function handleViewChange(nextView: string) {
  view.value = nextView as View
  if (view.value === 'archived' && studentsStore.archivedStudents.length === 0) {
    await studentsStore.fetchArchived()
  }
}

async function handleStudentCreated() {
  await refreshAll()
}

async function handleEmployeeCreated() {
  await studentsStore.fetchUsers()
}

// Permanent delete from the archive table. Prompts for confirmation
// because this can't be undone (the lead is already gone).
async function confirmDeleteArchive(id: number, name: string) {
  if (!confirm(`Permanently delete "${name}" from the archive? This cannot be undone.`)) return
  try {
    await studentsStore.deleteArchived(id)
  } catch (e: any) {
    alert(e.message || 'Failed to delete archive entry.')
  }
}

// Writes the draft role to Odoo. Guards prevent self-demotion
// and redundant writes when the role hasn't actually changed.
async function saveRole(user: OdooUser) {
  const nextRole = roleDrafts[user.id]
  if (!nextRole || nextRole === user.role || user.id === auth.uid) return

  savingUserId.value = user.id
  try {
    await studentsStore.updateUserRole(user.id, nextRole)
  } finally {
    savingUserId.value = null
  }
}

// ── DASHBOARD KPI COMPUTEDS ──────────────────────────────────
const employees = computed(() => studentsStore.employees)
const managers = computed(() => studentsStore.managers)
const enrolledCount = computed(() => studentsStore.students.filter((student) => student.status === 'enrolled').length)
const activeStudents = computed(() => studentsStore.students.filter((student) => student.status !== 'lost'))
</script>

<template>
  <div class="flex h-screen" style="background-color: #F7F5F0; min-width: 1200px">
    <AppSidebar :current-view="view" @view-change="handleViewChange" />

    <div class="flex flex-1 flex-col overflow-hidden" style="margin-left: 260px">
      <header class="flex flex-shrink-0 items-center justify-between border-b border-gray-100 bg-white px-8 py-4">
        <div>
          <h1 class="text-[22px] font-bold text-[#162340]" style="font-family: Sora, sans-serif">
            {{ { dashboard: 'Super Admin Dashboard', students: 'All Students', team: 'Managers & Employees', archived: 'Archived Students' }[view] }}
          </h1>
          <p class="mt-0.5 text-sm text-gray-500">
            Logged in as <span class="font-medium text-[#162340]">{{ auth.userName }}</span> · Super Admin
          </p>
        </div>

        <div class="flex items-center gap-3">
          <button
            @click="showCreateEmployeeModal = true"
            class="inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white transition-all hover:opacity-90"
            style="background-color: #162340"
          >
            <UserPlus2 class="h-4 w-4" />
            Create Employee
          </button>
          <button
            @click="refreshAll"
            class="flex items-center gap-2 rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-600 transition-all hover:bg-gray-50"
            :class="studentsStore.loading ? 'opacity-50' : ''"
          >
            <RefreshCw class="h-4 w-4" :class="studentsStore.loading ? 'animate-spin' : ''" />
            Refresh
          </button>
          <button
            @click="showChangePasswordModal = true"
            class="flex items-center gap-2 rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-600 transition-all hover:bg-gray-50"
          >
            <Lock class="h-4 w-4" />
            Change Password
          </button>
          <div
            class="flex h-9 w-9 items-center justify-center rounded-xl text-xs font-semibold text-white"
            style="background-color: #162340; font-family: Sora, sans-serif"
          >
            {{ auth.userName.split(' ').map((name) => name[0]).join('').slice(0, 2).toUpperCase() }}
          </div>
        </div>
      </header>

      <div v-if="studentsStore.loading" class="h-0.5 animate-pulse bg-[#B8966A]" />

      <main class="flex-1 overflow-y-auto p-8">
        <div v-if="view === 'dashboard'" class="space-y-6">
          <div class="grid grid-cols-4 gap-5">
            <StatCard label="Total Students" :value="studentsStore.students.length" :icon="Users" icon-bg="bg-[#162340]/10" icon-color="text-[#162340]" />
            <StatCard label="Managers" :value="managers.length" :icon="ShieldCheck" icon-bg="bg-[#162340]/10" icon-color="text-[#162340]" sublabel="University CRM managers" />
            <StatCard label="Employees" :value="employees.length" :icon="UserCheck" icon-bg="bg-[#B8966A]/15" icon-color="text-[#B8966A]" sublabel="Admissions advisors" />
            <StatCard label="Enrolled" :value="enrolledCount" :icon="GraduationCap" icon-bg="bg-green-50" icon-color="text-green-600" sublabel="Successful enrollments" />
          </div>

          <div class="grid grid-cols-5 gap-5">
            <div class="col-span-3 rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
              <div class="mb-5 flex items-center justify-between">
                <div>
                  <h3 class="text-base font-semibold text-[#162340]" style="font-family: Sora, sans-serif">Staff Overview</h3>
                  <p class="mt-0.5 text-xs text-gray-500">Review the team structure and role distribution across the CRM.</p>
                </div>
                <button
                  @click="view = 'team'"
                  class="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition-all hover:bg-gray-50"
                >
                  Manage Roles
                </button>
              </div>

              <div class="space-y-4">
                <div class="rounded-2xl border border-gray-100 bg-[#F7F5F0] p-4">
                  <div class="mb-2 flex items-center justify-between">
                    <span class="text-sm font-semibold text-[#162340]">Managers</span>
                    <span class="rounded-full bg-white px-2.5 py-1 text-xs text-gray-600">{{ managers.length }} total</span>
                  </div>
                  <div class="flex flex-wrap gap-2">
                    <span
                      v-for="manager in managers"
                      :key="manager.id"
                      class="rounded-full border border-[#162340]/10 bg-white px-3 py-1 text-xs font-medium text-[#162340]"
                    >
                      {{ manager.name }}
                    </span>
                  </div>
                </div>

                <div class="rounded-2xl border border-gray-100 bg-[#F7F5F0] p-4">
                  <div class="mb-2 flex items-center justify-between">
                    <span class="text-sm font-semibold text-[#162340]">Employees</span>
                    <span class="rounded-full bg-white px-2.5 py-1 text-xs text-gray-600">{{ employees.length }} total</span>
                  </div>
                  <div class="grid gap-2 md:grid-cols-2">
                    <div
                      v-for="employee in employees"
                      :key="employee.id"
                      class="rounded-xl border border-gray-100 bg-white px-3 py-2"
                    >
                      <div class="text-sm font-medium text-[#162340]">{{ employee.name }}</div>
                      <div class="text-xs text-gray-400">{{ employee.studentsTotal || 0 }} students · {{ employee.studentsEnrolled || 0 }} enrolled</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="col-span-2 rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
              <div class="mb-5">
                <h3 class="text-base font-semibold text-[#162340]" style="font-family: Sora, sans-serif">Archived Activity</h3>
                <p class="mt-0.5 text-xs text-gray-500">Track how many archived records are currently stored.</p>
              </div>
              <div class="rounded-2xl border border-dashed border-[#B8966A]/30 bg-[#B8966A]/5 p-5">
                <div class="text-xs uppercase tracking-[0.2em] text-[#B8966A]">Archive Records</div>
                <div class="mt-3 text-4xl font-bold text-[#162340]" style="font-family: Sora, sans-serif">
                  {{ studentsStore.archivedStudents.length }}
                </div>
                <p class="mt-2 text-sm text-gray-500">Use the archived section to restore students or audit deletions.</p>
              </div>
            </div>
          </div>

          <StudentTable
            :students="activeStudents"
            title="All Active Students"
            :show-assigned-to="true"
            :on-create="() => (showCreateModal = true)"
            :on-refresh="refreshAll"
          />
        </div>

        <StudentTable
          v-else-if="view === 'students'"
          :students="studentsStore.students"
          title="All Students"
          :show-assigned-to="true"
          empty-message="No students found."
          :on-create="() => (showCreateModal = true)"
          :on-refresh="refreshAll"
        />

        <div v-else-if="view === 'team'" class="space-y-5">
          <div class="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
            <div class="mb-5">
              <h3 class="text-base font-semibold text-[#162340]" style="font-family: Sora, sans-serif">Team & Role Management</h3>
              <p class="mt-0.5 text-xs text-gray-500">View managers and employees, then promote or demote users inside the University CRM security groups.</p>
            </div>

            <div class="overflow-x-auto">
              <table class="w-full">
                <thead>
                  <tr class="border-b border-gray-100">
                    <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">User</th>
                    <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Role</th>
                    <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Students</th>
                    <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Email</th>
                    <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Actions</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-50">
                  <tr v-for="user in studentsStore.users" :key="user.id" class="hover:bg-[#F7F5F0]/70">
                    <td class="px-4 py-4">
                      <div class="text-sm font-semibold text-[#162340]">{{ user.name }}</div>
                      <div class="text-xs text-gray-500">{{ user.login }}</div>
                    </td>
                    <td class="px-4 py-4">
                      <select
                        v-model="roleDrafts[user.id]"
                        :disabled="user.id === auth.uid"
                        class="rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 outline-none focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15 disabled:bg-gray-50 disabled:text-gray-400"
                      >
                        <option value="employee">Employee</option>
                        <option value="manager">Manager</option>
                      </select>
                    </td>
                    <td class="px-4 py-4 text-sm text-gray-600">{{ user.studentsTotal || 0 }} total · {{ user.studentsEnrolled || 0 }} enrolled</td>
                    <td class="px-4 py-4 text-sm text-gray-500">{{ user.email || user.login }}</td>
                    <td class="px-4 py-4">
                      <button
                        @click="saveRole(user)"
                        :disabled="savingUserId === user.id || roleDrafts[user.id] === user.role || user.id === auth.uid"
                        class="rounded-xl px-3 py-2 text-xs font-semibold text-white transition-all disabled:cursor-not-allowed disabled:opacity-40"
                        style="background-color: #162340"
                      >
                        {{ savingUserId === user.id ? 'Saving...' : user.id === auth.uid ? 'Current User' : 'Save Role' }}
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div v-else-if="view === 'archived'">
          <div v-if="studentsStore.archivedStudents.length === 0" class="rounded-2xl border border-gray-100 bg-white p-16 text-center shadow-sm">
            <div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full" style="background-color: #F7F5F0">
              <FileText class="h-7 w-7 text-gray-400" />
            </div>
            <h3 class="mb-2 text-[18px] font-semibold text-[#162340]" style="font-family: Sora, sans-serif">No Archived Students</h3>
            <p class="text-sm text-gray-500">Students removed from the pipeline will appear here.</p>
          </div>

          <div v-else class="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-sm">
            <div class="border-b border-gray-100 px-6 py-4">
              <h3 class="text-base font-semibold text-[#162340]" style="font-family: Sora, sans-serif">All Archived Students</h3>
            </div>
            <table class="w-full">
              <thead>
                <tr class="border-b border-gray-100">
                  <th class="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Student</th>
                  <th class="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Specialization</th>
                  <th class="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Deleted On</th>
                  <th class="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Reason</th>
                  <th class="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Deleted By</th>
                  <th class="px-6 py-3 text-center text-xs font-semibold uppercase tracking-wider text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-50">
                <tr v-for="archived in studentsStore.archivedStudents" :key="archived.id" class="hover:bg-[#F7F5F0]/70">
                  <td class="px-6 py-4">
                    <div class="text-sm font-semibold text-[#162340]">{{ archived.name }}</div>
                  </td>
                  <td class="px-6 py-4 text-sm text-gray-700">{{ archived.specialization_display || '—' }}</td>
                  <td class="px-6 py-4 text-sm text-gray-500">{{ archived.deleted_date?.slice(0, 10) || '—' }}</td>
                  <td class="px-6 py-4">
                    <span class="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-600">{{ archived.delete_reason || '—' }}</span>
                  </td>
                  <td class="px-6 py-4 text-sm text-gray-500">{{ Array.isArray(archived.deleted_by) ? archived.deleted_by[1] : '—' }}</td>
                  <td class="px-6 py-4 text-center">
                    <div class="inline-flex items-center gap-2">
                      <button
                        @click="studentsStore.restoreArchived(archived.id)"
                        class="inline-flex items-center gap-1 rounded-lg bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-600 transition-all hover:bg-blue-100"
                      >
                        ↺ Restore
                      </button>
                      <button
                        @click="confirmDeleteArchive(archived.id, archived.name)"
                        class="inline-flex items-center gap-1 rounded-lg bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-600 transition-all hover:bg-red-100"
                      >
                        ✕ Delete
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>

    <CreateStudentModal :open="showCreateModal" allow-assign @close="showCreateModal = false" @created="handleStudentCreated" />
    <CreateEmployeeModal :open="showCreateEmployeeModal" @close="showCreateEmployeeModal = false" @created="handleEmployeeCreated" />
    <PasswordChangeModal :is-open="showChangePasswordModal" @close="showChangePasswordModal = false" />
  </div>
</template>
