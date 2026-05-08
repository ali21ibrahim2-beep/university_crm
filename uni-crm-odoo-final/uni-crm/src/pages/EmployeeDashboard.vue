<!-- EmployeeDashboard — advisor view. Shows only students assigned
     to the current user, plus that user's personal archive. -->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { FileText, GraduationCap, TrendingUp, Users, Lock } from 'lucide-vue-next'
import AppSidebar from '../components/AppSidebar.vue'
import CreateStudentModal from '../components/CreateStudentModal.vue'
import PasswordChangeModal from '../components/PasswordChangeModal.vue'
import StatCard from '../components/StatCard.vue'
import StatusBadge from '../components/StatusBadge.vue'
import StudentTable from '../components/StudentTable.vue'
import { useAuthStore } from '../stores/auth'
import { useStudentsStore } from '../stores/students'
import { STATUS_STEPS } from '../types/odoo'
import { callKw } from '../services/odoo'

// ── VIEW STATE ───────────────────────────────────────────────
type View = 'my-students' | 'my-archive'

const view = ref<View>('my-students')
const showCreateModal = ref(false)
const showChangePasswordModal = ref(false)
const studentsStore = useStudentsStore()
const auth = useAuthStore()

// Countries for filters + student list on mount.
onMounted(async () => {
  await studentsStore.fetchCountries()
  if (auth.uid) {
    await studentsStore.fetchMyStudents(auth.uid)
  }
})

async function refreshStudents() {
  if (auth.uid) {
    await studentsStore.fetchMyStudents(auth.uid)
  }
  if (view.value === 'my-archive') {
    await studentsStore.fetchArchived()
  }
}

// Lazy-load archived students the first time the Archive view opens.
async function handleViewChange(nextView: string) {
  view.value = nextView as View
  if (view.value === 'my-archive') {
    await studentsStore.fetchArchived()
  }
}

async function handleStudentCreated() {
  await refreshStudents()
}

// Calls student.archive → action_restore (undoes a soft-delete).
async function restoreArchived(archiveId: number) {
  const confirmed = confirm('Are you sure you want to restore this student record?')
  if (!confirmed) return

  try {
    // Call the action_restore method on the student.archive model
    // Pass the archive ID in a list as the first argument
    await callKw('student.archive', 'action_restore', [[archiveId]])
    
    alert('✓ Student successfully restored!')
    // Refresh the archive list and active students
    await studentsStore.fetchArchived()
    if (auth.uid) {
      await studentsStore.fetchMyStudents(auth.uid)
    }
  } catch (err) {
    console.error('Error restoring archive:', err)
    alert(`✗ Error restoring student: ${err instanceof Error ? err.message : 'Unknown error'}`)
  }
}

// ── DERIVED DATA ─────────────────────────────────────────────
// Employees only see archives they themselves deleted.
const myArchived = computed(() =>
  studentsStore.archivedStudents.filter((archived) => Array.isArray(archived.deleted_by) && archived.deleted_by[0] === auth.uid)
)
const enrolledCount = computed(() => studentsStore.students.filter((student) => student.status === 'enrolled').length)
const docsCount = computed(() => studentsStore.students.filter((student) => student.status === 'docs').length)
const newCount = computed(() => studentsStore.students.filter((student) => student.status === 'new').length)
</script>

<template>
  <div class="flex h-screen" style="background-color: #F7F5F0; min-width: 1200px">
    <AppSidebar :current-view="view" @view-change="handleViewChange" />

    <div class="flex flex-1 flex-col overflow-hidden" style="margin-left: 260px">
      <header class="flex flex-shrink-0 items-center justify-between border-b border-gray-100 bg-white px-8 py-4">
        <div>
          <h1 class="text-[22px] font-bold text-[#162340]" style="font-family: Sora, sans-serif">
            {{ view === 'my-students' ? 'My Students' : 'My Archive' }}
          </h1>
          <p class="mt-0.5 text-sm text-gray-500">
            Logged in as <span class="font-medium text-[#162340]">{{ auth.userName }}</span>
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
            style="background-color: #B8966A; font-family: Sora, sans-serif"
          >
            {{ auth.userName.split(' ').map((name) => name[0]).join('').slice(0, 2).toUpperCase() }}
          </div>
        </div>
      </header>

      <div v-if="studentsStore.loading" class="h-0.5 animate-pulse bg-[#B8966A]" />

      <main class="flex-1 overflow-y-auto p-8">
        <div v-if="view === 'my-students'" class="space-y-6">
          <div class="flex items-center justify-between rounded-2xl p-6" style="background-color: #162340">
            <div>
              <h2 class="mb-1 text-[20px] font-bold text-white" style="font-family: Sora, sans-serif">
                Welcome back, {{ auth.userName.split(' ')[0] }}!
              </h2>
              <p class="text-sm text-white/60">
                You currently have <span class="font-semibold text-white">{{ newCount }}</span> new inquiries and
                <span class="font-semibold text-white">{{ docsCount }}</span> students collecting documents.
              </p>
            </div>
            <div
              class="flex h-16 w-16 items-center justify-center rounded-2xl text-xl font-bold text-white"
              style="background-color: #B8966A; font-family: Sora, sans-serif"
            >
              {{ auth.userName.split(' ').map((name) => name[0]).join('').slice(0, 2).toUpperCase() }}
            </div>
          </div>

          <div class="grid grid-cols-4 gap-5">
            <StatCard label="My Students" :value="studentsStore.students.length" :icon="Users" icon-bg="bg-[#162340]/10" icon-color="text-[#162340]" />
            <StatCard
              label="Enrolled"
              :value="enrolledCount"
              :icon="GraduationCap"
              icon-bg="bg-green-50"
              icon-color="text-green-600"
              :change="`${studentsStore.students.length ? Math.round((enrolledCount / studentsStore.students.length) * 100) : 0}% rate`"
              change-type="up"
            />
            <StatCard label="Collecting Docs" :value="docsCount" :icon="FileText" icon-bg="bg-orange-50" icon-color="text-orange-600" sublabel="Action needed" />
            <StatCard label="New Inquiries" :value="newCount" :icon="TrendingUp" icon-bg="bg-blue-50" icon-color="text-blue-600" sublabel="Follow up today" />
          </div>

          <div class="grid grid-cols-3 gap-5">
            <div class="col-span-2">
              <StudentTable
                :students="studentsStore.students"
                title="My Students"
                :show-assigned-to="false"
                empty-message="No students assigned to you yet."
                :on-create="() => (showCreateModal = true)"
                :on-refresh="refreshStudents"
              />
            </div>
            <div class="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
              <h3 class="mb-4 text-[15px] font-semibold text-[#162340]" style="font-family: Sora, sans-serif">Status Breakdown</h3>
              <div class="space-y-2">
                <div
                  v-for="step in STATUS_STEPS"
                  :key="step"
                  class="flex items-center justify-between border-b border-gray-50 py-2 last:border-0"
                >
                  <StatusBadge :status="step" size="sm" />
                  <span class="text-xs font-semibold text-[#162340]" style="font-family: Sora, sans-serif">
                    {{ studentsStore.students.filter((student) => student.status === step).length }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="view === 'my-archive'">
          <div v-if="myArchived.length === 0" class="rounded-2xl border border-gray-100 bg-white p-16 text-center shadow-sm">
            <div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full" style="background-color: #F7F5F0">
              <FileText class="h-7 w-7 text-gray-400" />
            </div>
            <h3 class="mb-2 text-[18px] font-semibold text-[#162340]" style="font-family: Sora, sans-serif">No Archived Students</h3>
            <p class="text-sm text-gray-500">Students you remove from the pipeline will appear here.</p>
          </div>

          <div v-else class="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-sm">
            <div class="border-b border-gray-100 px-6 py-4">
              <h3 class="text-base font-semibold text-[#162340]" style="font-family: Sora, sans-serif">My Archived Students</h3>
            </div>
            <table class="w-full">
              <thead>
                <tr class="border-b border-gray-100">
                  <th class="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Student</th>
                  <th class="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Specialization</th>
                  <th class="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Deleted On</th>
                  <th class="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">Reason</th>
                  <th class="px-6 py-3 text-center text-xs font-semibold uppercase tracking-wider text-gray-500">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-50">
                <tr v-for="archived in myArchived" :key="archived.id" class="hover:bg-[#F7F5F0]/70">
                  <td class="px-6 py-4">
                    <div class="text-sm font-semibold text-[#162340]">{{ archived.name }}</div>
                  </td>
                  <td class="px-6 py-4 text-sm text-gray-700">{{ archived.specialization_display || '—' }}</td>
                  <td class="px-6 py-4 text-sm text-gray-500">{{ archived.deleted_date?.slice(0, 10) || '—' }}</td>
                  <td class="px-6 py-4">
                    <span class="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-600">{{ archived.delete_reason || '—' }}</span>
                  </td>
                  <td class="px-6 py-4 text-center">
                    <button
                      @click="restoreArchived(archived.id)"
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

    <CreateStudentModal :open="showCreateModal" @close="showCreateModal = false" @created="handleStudentCreated" />
    <PasswordChangeModal :is-open="showChangePasswordModal" @close="showChangePasswordModal = false" />
  </div>
</template>
