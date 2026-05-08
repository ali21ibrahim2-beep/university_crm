<!-- ManagerDashboard — sees all students + employees overview +
     archive (with restore). No role editing; that's admin-only. -->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { FileText, GraduationCap, UserCheck, Users, Lock } from 'lucide-vue-next'
import AppSidebar from '../components/AppSidebar.vue'
import CreateStudentModal from '../components/CreateStudentModal.vue'
import PasswordChangeModal from '../components/PasswordChangeModal.vue'
import StatCard from '../components/StatCard.vue'
import StudentTable from '../components/StudentTable.vue'
import { useAuthStore } from '../stores/auth'
import { useStudentsStore } from '../stores/students'
import { STATUS_LABELS } from '../types/odoo'

// ── VIEW STATE ───────────────────────────────────────────────
type View = 'dashboard' | 'students' | 'employees' | 'archived'

const view = ref<View>('dashboard')
const showCreateModal = ref(false)
const showChangePasswordModal = ref(false)
const studentsStore = useStudentsStore()
const auth = useAuthStore()

// Load everything up-front in parallel to avoid waterfall latency.
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

// Restore = undo a soft-delete via student.archive.action_restore.
async function handleRestoreArchived(archiveId: number) {
  const confirmed = confirm('Are you sure you want to restore this student record?')
  if (!confirmed) return

  try {
    await studentsStore.restoreArchived(archiveId)
    alert('✓ Student successfully restored!')
  } catch (err) {
    console.error('Error restoring archive:', err)
    alert(`✗ Error restoring student: ${err instanceof Error ? err.message : 'Unknown error'}`)
  }
}

// ── DASHBOARD KPI COMPUTEDS ──────────────────────────────────
const employees = computed(() => studentsStore.employees)
const activeStudents = computed(() => studentsStore.students.filter((student) => student.status !== 'lost'))
const enrolledCount = computed(() => studentsStore.students.filter((student) => student.status === 'enrolled').length)
const docsCount = computed(() => studentsStore.students.filter((student) => student.status === 'docs').length)
</script>

<template>
  <div class="flex h-screen" style="background-color: #F7F5F0; min-width: 1200px">
    <AppSidebar :current-view="view" @view-change="handleViewChange" />

    <div class="flex flex-1 flex-col overflow-hidden" style="margin-left: 260px">
      <header class="flex flex-shrink-0 items-center justify-between border-b border-gray-100 bg-white px-8 py-4">
        <div>
          <h1 class="text-[22px] font-bold text-[#162340]" style="font-family: Sora, sans-serif">
            {{ { dashboard: 'Manager Dashboard', students: 'All Students', employees: 'Employees', archived: 'Archived Students' }[view] }}
          </h1>
          <p class="mt-0.5 text-sm text-gray-500">
            Logged in as <span class="font-medium text-[#162340]">{{ auth.userName }}</span> · Manager
          </p>
        </div>

        <div class="flex items-center gap-3">

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
            <StatCard
              label="Enrolled"
              :value="enrolledCount"
              :icon="GraduationCap"
              icon-bg="bg-green-50"
              icon-color="text-green-600"
              :change="`${studentsStore.students.length ? Math.round((enrolledCount / studentsStore.students.length) * 100) : 0}% rate`"
              change-type="up"
            />
            <StatCard label="Collecting Docs" :value="docsCount" :icon="FileText" icon-bg="bg-orange-50" icon-color="text-orange-600" sublabel="Awaiting documents" />
            <StatCard label="Employees" :value="employees.length" :icon="UserCheck" icon-bg="bg-[#B8966A]/15" icon-color="text-[#B8966A]" sublabel="Active advisors" />
          </div>

          <div class="grid grid-cols-5 gap-5">
            <div class="col-span-3 rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
              <div class="mb-5 flex items-center justify-between">
                <div>
                  <h3 class="text-base font-semibold text-[#162340]" style="font-family: Sora, sans-serif">Employee Performance</h3>
                  <p class="mt-0.5 text-xs text-gray-500">See how each advisor is moving students through the pipeline.</p>
                </div>
                <button
                  @click="view = 'employees'"
                  class="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition-all hover:bg-gray-50"
                >
                  View Employees
                </button>
              </div>

              <div v-if="employees.length === 0" class="py-10 text-center text-sm text-gray-400">No employees found yet.</div>
              <div v-else class="space-y-5">
                <div v-for="user in employees" :key="user.id">
                  <div class="mb-2 flex items-center justify-between">
                    <div class="flex items-center gap-3">
                      <div
                        class="flex h-9 w-9 items-center justify-center rounded-xl text-xs font-semibold text-white"
                        style="background-color: #162340; font-family: Sora, sans-serif"
                      >
                        {{ user.name.split(' ').map((name) => name[0]).join('').slice(0, 2).toUpperCase() }}
                      </div>
                      <div>
                        <div class="text-sm font-medium text-[#162340]">{{ user.name }}</div>
                        <div class="text-xs text-gray-400">{{ user.studentsEnrolled || 0 }}/{{ user.studentsTotal || 0 }} enrolled</div>
                      </div>
                    </div>
                    <span class="text-sm font-bold text-[#162340]" style="font-family: Sora, sans-serif">
                      {{ user.studentsTotal ? Math.round(((user.studentsEnrolled || 0) / user.studentsTotal) * 100) : 0 }}%
                    </span>
                  </div>
                  <div class="h-2 overflow-hidden rounded-full bg-gray-100">
                    <div
                      class="h-full rounded-full"
                      style="background-color: #B8966A"
                      :style="{ width: `${user.studentsTotal ? Math.round(((user.studentsEnrolled || 0) / user.studentsTotal) * 100) : 0}%` }"
                    />
                  </div>
                </div>
              </div>
            </div>

            <div class="col-span-2 rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
              <div class="mb-5">
                <h3 class="text-base font-semibold text-[#162340]" style="font-family: Sora, sans-serif">Pipeline Overview</h3>
                <p class="mt-0.5 text-xs text-gray-500">Students grouped by their current status.</p>
              </div>
              <div class="space-y-3">
                <div
                  v-for="(label, key) in STATUS_LABELS"
                  :key="key"
                  class="flex items-center justify-between border-b border-gray-50 py-2 last:border-0"
                >
                  <div class="flex items-center gap-2">
                    <div
                      class="h-2 w-2 rounded-full"
                      :style="{ backgroundColor: key === 'enrolled' ? '#22c55e' : key === 'lost' ? '#ef4444' : '#B8966A' }"
                    />
                    <span class="text-sm text-gray-600">{{ label }}</span>
                  </div>
                  <span class="text-sm font-bold text-[#162340]" style="font-family: Sora, sans-serif">
                    {{ studentsStore.students.filter((student) => student.status === key).length }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <StudentTable
            :students="activeStudents"
            title="Active Students"
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

        <div v-else-if="view === 'employees'" class="grid grid-cols-2 gap-5">
          <div v-if="employees.length === 0" class="col-span-2 rounded-2xl border border-gray-100 bg-white p-16 text-center text-gray-400 shadow-sm">
            No employees available.
          </div>
          <div
            v-for="user in employees"
            :key="user.id"
            class="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm transition-shadow hover:shadow-md"
          >
            <div class="mb-5 flex items-start justify-between">
              <div class="flex items-center gap-3">
                <div
                  class="flex h-12 w-12 items-center justify-center rounded-xl text-base font-semibold text-white"
                  style="background-color: #162340; font-family: Sora, sans-serif"
                >
                  {{ user.name.split(' ').map((name) => name[0]).join('').slice(0, 2).toUpperCase() }}
                </div>
                <div>
                  <div class="text-base font-semibold text-[#162340]" style="font-family: Sora, sans-serif">{{ user.name }}</div>
                  <div class="text-xs text-gray-500">{{ user.login }}</div>
                </div>
              </div>
              <span class="rounded-full bg-[#162340]/10 px-3 py-1.5 text-xs font-semibold text-[#162340]">
                {{ user.studentsTotal || 0 }} students
              </span>
            </div>

            <div class="mb-5 grid grid-cols-2 gap-3">
              <div class="rounded-xl bg-[#F7F5F0] p-3 text-center">
                <div class="text-2xl font-bold text-[#162340]" style="font-family: Sora, sans-serif">{{ user.studentsTotal || 0 }}</div>
                <div class="mt-0.5 text-xs text-gray-500">Total</div>
              </div>
              <div class="rounded-xl bg-[#F7F5F0] p-3 text-center">
                <div class="text-2xl font-bold text-green-600" style="font-family: Sora, sans-serif">{{ user.studentsEnrolled || 0 }}</div>
                <div class="mt-0.5 text-xs text-gray-500">Enrolled</div>
              </div>
            </div>

            <div>
              <div class="mb-1.5 flex items-center justify-between">
                <span class="text-xs text-gray-500">Enrollment Rate</span>
                <span class="text-xs font-bold text-[#162340]" style="font-family: Sora, sans-serif">
                  {{ user.studentsTotal ? Math.round(((user.studentsEnrolled || 0) / user.studentsTotal) * 100) : 0 }}%
                </span>
              </div>
              <div class="h-2 overflow-hidden rounded-full bg-gray-100">
                <div
                  class="h-full rounded-full"
                  style="background-color: #B8966A"
                  :style="{ width: `${user.studentsTotal ? Math.round(((user.studentsEnrolled || 0) / user.studentsTotal) * 100) : 0}%` }"
                />
              </div>
            </div>

            <div class="mt-4 border-t border-gray-100 pt-4 text-xs text-gray-500">
              {{ user.email || user.login }}
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
              <h3 class="text-base font-semibold text-[#162340]" style="font-family: Sora, sans-serif">Archived Students</h3>
            </div>
            <table class="w-full">
              <thead>
                <tr class="border-b border-gray-100">
                  <th class="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Student</th>
                  <th class="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Specialization</th>
                  <th class="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Deleted On</th>
                  <th class="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Reason</th>
                  <th class="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Deleted By</th>
                  <th class="px-6 py-3 text-center text-xs font-semibold uppercase tracking-wider text-gray-500">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-50">
                <tr
                  v-for="archived in studentsStore.archivedStudents"
                  :key="archived.id"
                  class="hover:bg-[#F7F5F0]/70"
                >
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
                    <button
                      @click="handleRestoreArchived(archived.id)"
                      class="inline-flex items-center gap-1 rounded-lg bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-600 transition-all hover:bg-blue-100"
                    >
                      ↺ Restore
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>

    <CreateStudentModal :open="showCreateModal" allow-assign @close="showCreateModal = false" @created="handleStudentCreated" />
    <PasswordChangeModal :is-open="showChangePasswordModal" @close="showChangePasswordModal = false" />
  </div>
</template>
