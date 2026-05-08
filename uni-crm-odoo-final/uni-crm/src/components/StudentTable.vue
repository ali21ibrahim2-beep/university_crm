<!-- StudentTable — reusable student list with search, filters and sort.
     Used by every dashboard. Purely presentational: data + Create/Refresh
     handlers are passed in by the parent page. -->
<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Search, SlidersHorizontal, Eye, ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-vue-next'
import type { OdooStudent, OdooStatus } from '../types/odoo'
import { STATUS_LABELS } from '../types/odoo'
import StatusBadge from './StatusBadge.vue'

// ── PROPS ────────────────────────────────────────────────────
const props = defineProps<{
  students: OdooStudent[]
  title?: string
  showAssignedTo?: boolean
  emptyMessage?: string
  onCreate?: () => void
  onRefresh?: () => void
}>()

const router = useRouter()
// ── FILTER + SORT STATE ──────────────────────────────────────
const search = ref('')
const statusFilter = ref<OdooStatus | 'all'>('all')
const nationalityFilter = ref('')
const specializationFilter = ref('')
const nameFilter = ref('')
const phoneFilter = ref('')
const emailFilter = ref('')
const sortField = ref('name')
const sortDir = ref<'asc' | 'desc' | null>('asc')
const showFilters = ref(false)

// ── DROPDOWN OPTIONS (from current dataset) ──────────────────
const allNationalities = computed(() => {
  const set = new Set<string>()
  props.students.forEach(s => { if (Array.isArray(s.country_id)) set.add(s.country_id[1]) })
  return [...set].sort()
})

const allSpecializations = computed(() => {
  const set = new Set<string>()
  props.students.forEach(s => { if (s.specialization_display) set.add(s.specialization_display) })
  return [...set].sort()
})

const ALL_STATUSES: OdooStatus[] = ['new', 'options_sent', 'chosen', 'docs', 'enrolled', 'lost']

// ── SORTING ──────────────────────────────────────────────────
// Cycles the same column: asc → desc → none.
function handleSort(field: string) {
  if (sortField.value === field) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : sortDir.value === 'desc' ? null : 'asc'
  } else {
    sortField.value = field
    sortDir.value = 'asc'
  }
}

// Helper: get string value from Odoo field
function strVal(val: string | false | null): string { return val || '' }
function m2oName(val: [number, string] | false | null): string { return Array.isArray(val) ? val[1] : '' }

// ── FILTER + SORT PIPELINE ───────────────────────────────────
// `filtered` applies every user-chosen filter to props.students.
const filtered = computed(() => props.students.filter(s => {
  const q = search.value.toLowerCase()
  const matchSearch = !q ||
    strVal(s.name).toLowerCase().includes(q) ||
    strVal(s.email).toLowerCase().includes(q) ||
    strVal(s.phone_full).toLowerCase().includes(q) ||
    strVal(s.phone).toLowerCase().includes(q) ||
    strVal(s.specialization_display).toLowerCase().includes(q) ||
    m2oName(s.country_id).toLowerCase().includes(q)
  const matchStatus = statusFilter.value === 'all' || s.status === statusFilter.value
  const matchNationality = !nationalityFilter.value || m2oName(s.country_id) === nationalityFilter.value
  const matchSpec = !specializationFilter.value || strVal(s.specialization_display) === specializationFilter.value
  const matchName = !nameFilter.value || strVal(s.name).toLowerCase().includes(nameFilter.value.toLowerCase())
  const matchPhone = !phoneFilter.value || strVal(s.phone).toLowerCase().includes(phoneFilter.value.toLowerCase()) || strVal(s.phone_full).toLowerCase().includes(phoneFilter.value.toLowerCase())
  const matchEmail = !emailFilter.value || strVal(s.email).toLowerCase().includes(emailFilter.value.toLowerCase())
  return matchSearch && matchStatus && matchNationality && matchSpec && matchName && matchPhone && matchEmail
}))

// `sorted` runs after filtering; direction=null means "original order".
const sorted = computed(() => {
  return [...filtered.value].sort((a, b) => {
    if (!sortDir.value) return 0
    let valA = '', valB = ''
    if (sortField.value === 'name') { valA = strVal(a.name); valB = strVal(b.name) }
    else if (sortField.value === 'specialization') { valA = strVal(a.specialization_display); valB = strVal(b.specialization_display) }
    else if (sortField.value === 'status') { valA = a.status; valB = b.status }
    else if (sortField.value === 'assignedTo') { valA = m2oName(a.user_id); valB = m2oName(b.user_id) }
    else if (sortField.value === 'date') { valA = strVal(a.date_contacted); valB = strVal(b.date_contacted) }
    const cmp = valA.localeCompare(valB)
    return sortDir.value === 'asc' ? cmp : -cmp
  })
})

function initials(name: string) { return name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() }
</script>

<template>
  <div class="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
    <!-- Header: title, count, Create / Refresh buttons, search, filter toggle -->
    <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between gap-4">
      <div>
        <h3 class="font-semibold text-[#162340]" style="font-family: Sora, sans-serif; font-size: 16px">{{ title || 'Students' }}</h3>
        <p class="text-xs text-gray-500 mt-0.5">{{ filtered.length }} of {{ students.length }} students</p>
      </div>
      <div class="flex items-center gap-2">
        <button v-if="onCreate"
          @click="onCreate?.()"
          class="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-white transition-all hover:opacity-90"
          style="background-color: #B8966A">
          <span class="text-base leading-none">+</span>
          Create Student
        </button>
        <button v-if="onRefresh"
          @click="onRefresh?.()"
          class="flex items-center gap-1.5 px-3 py-2 text-xs rounded-xl border border-gray-200 text-gray-600 hover:bg-gray-50">
          Refresh
        </button>
        <div class="relative">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input v-model="search" type="text" placeholder="Search students..."
            class="pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-xl bg-[#F7F5F0] focus:outline-none focus:ring-2 focus:ring-[#162340]/20 w-52 transition-all" />
        </div>
        <button @click="showFilters = !showFilters"
          class="flex items-center gap-1.5 px-3 py-2 text-sm rounded-xl border transition-all"
          :class="showFilters ? 'bg-[#162340] text-white border-[#162340]' : 'border-gray-200 text-gray-600 hover:bg-gray-50'">
          <SlidersHorizontal class="w-4 h-4" /> Filter
        </button>
      </div>
    </div>

    <!-- Filters panel (collapsible): status pills + dropdowns + text fields + clear -->
    <div v-if="showFilters" class="px-6 py-5 border-b border-gray-100 bg-[#F7F5F0]/50 space-y-5">
      <!-- Status Row -->
      <div>
        <div class="text-xs text-gray-500 font-medium mb-2">Status</div>
        <div class="flex items-center gap-2 flex-wrap">
          <button @click="statusFilter = 'all'"
            class="px-3 py-1 rounded-full text-xs font-medium transition-all"
            :class="statusFilter === 'all' ? 'bg-[#162340] text-white' : 'bg-white border border-gray-200 text-gray-600'">
            All
          </button>
          <button v-for="s in ALL_STATUSES" :key="s" @click="statusFilter = s"
            class="px-3 py-1 rounded-full text-xs font-medium transition-all"
            :class="statusFilter === s ? 'bg-[#162340] text-white' : 'bg-white border border-gray-200 text-gray-600'">
            {{ STATUS_LABELS[s] }}
          </button>
        </div>
      </div>

      <!-- Dropdown Filters Row -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-xs text-gray-500 font-medium mb-2">Nationality</label>
          <select v-model="nationalityFilter"
            class="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg text-[#162340] focus:outline-none focus:ring-2 focus:ring-[#162340]/20 bg-white transition-all">
            <option value="">All Nationalities</option>
            <option v-for="n in allNationalities" :key="n" :value="n">{{ n }}</option>
          </select>
        </div>
        <div>
          <label class="block text-xs text-gray-500 font-medium mb-2">Specialization</label>
          <select v-model="specializationFilter"
            class="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg text-[#162340] focus:outline-none focus:ring-2 focus:ring-[#162340]/20 bg-white transition-all">
            <option value="">All Specializations</option>
            <option v-for="sp in allSpecializations" :key="sp" :value="sp">{{ sp }}</option>
          </select>
        </div>
      </div>

      <!-- Text Filters Row -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-xs text-gray-500 font-medium mb-2">Name</label>
          <input v-model="nameFilter" type="text" placeholder="Filter by name..."
            class="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg text-[#162340] focus:outline-none focus:ring-2 focus:ring-[#162340]/20 bg-white transition-all" />
        </div>
        <div>
          <label class="block text-xs text-gray-500 font-medium mb-2">Phone Number</label>
          <input v-model="phoneFilter" type="text" placeholder="Filter by phone..."
            class="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg text-[#162340] focus:outline-none focus:ring-2 focus:ring-[#162340]/20 bg-white transition-all" />
        </div>
      </div>

      <!-- Email Filter Row -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-xs text-gray-500 font-medium mb-2">Email</label>
          <input v-model="emailFilter" type="text" placeholder="Filter by email..."
            class="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg text-[#162340] focus:outline-none focus:ring-2 focus:ring-[#162340]/20 bg-white transition-all" />
        </div>
        <div class="flex items-end">
          <button @click="statusFilter = 'all'; nationalityFilter = ''; specializationFilter = ''; nameFilter = ''; phoneFilter = ''; emailFilter = ''; search = ''"
            class="w-full px-3 py-2 rounded-lg text-xs font-medium border border-gray-200 text-gray-600 hover:bg-white transition-all">
            Clear All Filters
          </button>
        </div>
      </div>
    </div>

    <!-- Results table (sortable headers; "View" link per row) -->
    <div class="overflow-x-auto">
      <table class="w-full">
        <thead>
          <tr class="border-b border-gray-100">
            <th v-for="col in [
              { label: 'Student', field: 'name' },
              { label: 'Specialization', field: 'specialization' },
              { label: 'Status', field: 'status' },
              ...(showAssignedTo ? [{ label: 'Assigned To', field: 'assignedTo' }] : []),
              { label: 'Date Contacted', field: 'date' },
              { label: 'Actions', field: null },
            ]" :key="col.label"
              class="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider"
              :class="col.field ? 'cursor-pointer hover:text-[#162340] select-none' : ''"
              @click="col.field && handleSort(col.field)">
              <div class="flex items-center gap-1">
                {{ col.label }}
                <template v-if="col.field">
                  <ChevronUp v-if="sortField === col.field && sortDir === 'asc'" class="w-3 h-3 text-[#162340]" />
                  <ChevronDown v-else-if="sortField === col.field && sortDir === 'desc'" class="w-3 h-3 text-[#162340]" />
                  <ChevronsUpDown v-else class="w-3 h-3 text-gray-400" />
                </template>
              </div>
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50">
          <tr v-if="sorted.length === 0">
            <td :colspan="showAssignedTo ? 6 : 5" class="px-6 py-12 text-center text-gray-400 text-sm">
              <div class="flex flex-col items-center gap-2">
                <div class="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center">
                  <Search class="w-5 h-5 text-gray-400" />
                </div>
                <span>{{ emptyMessage || 'No students found.' }}</span>
              </div>
            </td>
          </tr>
          <tr v-for="student in sorted" :key="student.id" class="hover:bg-[#F7F5F0]/70 transition-colors group">
            <!-- Student -->
            <td class="px-6 py-4">
              <div class="flex items-center gap-3">
                <div class="w-9 h-9 rounded-xl flex items-center justify-center text-xs font-semibold text-white flex-shrink-0"
                  style="background-color: #162340; font-family: Sora, sans-serif">
                  {{ initials(student.name) }}
                </div>
                <div>
                  <div class="text-sm font-semibold text-[#162340]">{{ student.name }}</div>
                  <div class="text-xs text-gray-500">{{ student.email || '—' }}</div>
                </div>
              </div>
            </td>
            <!-- Specialization -->
            <td class="px-6 py-4">
              <div class="text-sm text-gray-700 font-medium">{{ student.specialization_display || '—' }}</div>
              <div class="text-xs text-gray-400 mt-0.5">
                {{ student.degree_level || '' }}
                {{ student.country_id ? ' · ' + (Array.isArray(student.country_id) ? student.country_id[1] : '') : '' }}
              </div>
            </td>
            <!-- Status -->
            <td class="px-6 py-4">
              <StatusBadge :status="student.status" />
            </td>
            <!-- Assigned To -->
            <td v-if="showAssignedTo" class="px-6 py-4">
              <div v-if="student.user_id && Array.isArray(student.user_id)" class="flex items-center gap-2">
                <div class="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-semibold text-white flex-shrink-0"
                  style="background-color: #B8966A; font-family: Sora, sans-serif">
                  {{ student.user_id[1]?.split(' ').map((n: string) => n[0]).join('').slice(0, 2) }}
                </div>
                <span class="text-sm text-gray-700">{{ student.user_id[1] }}</span>
              </div>
              <span v-else class="text-gray-400 text-sm">—</span>
            </td>
            <!-- Date -->
            <td class="px-6 py-4">
              <span class="text-sm text-gray-500">{{ student.date_contacted || '—' }}</span>
            </td>
            <!-- Actions -->
            <td class="px-6 py-4">
              <button @click="router.push(`/student/${student.id}`)"
                class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 text-gray-600 hover:bg-[#162340] hover:text-white hover:border-[#162340] transition-all opacity-0 group-hover:opacity-100">
                <Eye class="w-3.5 h-3.5" /> View
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
