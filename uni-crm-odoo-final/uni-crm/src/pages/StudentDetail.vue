<!-- StudentDetail — full record view with inline edit, status change,
     attachments upload, portal-link copy, and a delete wizard.
     Polls the record every 1h to pick up external changes. -->
<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Mail, Phone, Globe, GraduationCap, Calendar, DollarSign, Award, FileText, Download, Copy, CheckCheck, ExternalLink, User, BookOpen, MessageCircle, Trash2, Edit3, X, Check, Upload, RotateCw } from 'lucide-vue-next'
import AppSidebar from '../components/AppSidebar.vue'
import StatusBadge from '../components/StatusBadge.vue'
import ProgressSteps from '../components/ProgressSteps.vue'
import { useStudentsStore } from '../stores/students'
import { useAuthStore } from '../stores/auth'
import { attachmentUrl, uploadAttachment, odoo } from '../services/odoo'
import { odooVal, odooM2o, DEGREE_LABELS, SPECIALIZATION_LABELS } from '../types/odoo'

// ── ROUTE + STORES ───────────────────────────────────────────
const route = useRoute()
const router = useRouter()
const studentsStore = useStudentsStore()
const auth = useAuthStore()
const copied = ref(false)
const refreshing = ref(false)
// Sidebar highlight depends on which dashboard the user came from.
const sidebarView = ref(auth.isSuperAdmin ? 'students' : auth.isManager ? 'students' : 'my-students')
const studentId = Number(route.params.id)

// ── EDIT MODE ────────────────────────────────────────────────
// Toggled by the pencil icon. editForm stages changes until Save.
const editing = ref(false)
const editForm = ref<Record<string, any>>({})
const saving = ref(false)
const degreeOptions = Object.entries(DEGREE_LABELS)
const specializationOptions = Object.entries(SPECIALIZATION_LABELS)
const advisorOptions = computed(() => studentsStore.employees)

// ── PHONE VALIDATION ─────────────────────────────────────────
// Live-checks editForm.phone against the phone.country.format rule for
// the selected country. Mirrors the Python _check_phone constraint so
// the user sees the same message before hitting Save.
const phoneCheck = computed(() => {
  const cid = Number(editForm.value.phoneCountryId)
  const raw = (editForm.value.phone || '').toString()
  const digits = raw.replace(/\D/g, '')
  if (!cid) {
    return { ok: true, level: 'info', msg: raw ? 'Select a phone country code.' : '' }
  }
  const fmt = studentsStore.phoneFormats[cid]
  const country = studentsStore.countries.find((c: any) => c.id === cid)
  const cname = country?.name || 'this country'
  if (!fmt) {
    return { ok: true, level: 'info', msg: '' }
  }
  if (!digits) {
    const hint = fmt.leading_digit
      ? `Enter ${fmt.digit_count} digits starting with ${fmt.leading_digit}.`
      : `Enter ${fmt.digit_count} digits.`
    return { ok: true, level: 'info', msg: hint }
  }
  if (fmt.leading_digit && !digits.startsWith(fmt.leading_digit)) {
    return {
      ok: false,
      level: 'error',
      msg: `${cname} numbers must start with ${fmt.leading_digit} (you entered ${digits[0]}).`,
    }
  }
  if (digits.length !== fmt.digit_count) {
    const diff = fmt.digit_count - digits.length
    const note = diff > 0 ? `${diff} more` : `${-diff} too many`
    return {
      ok: false,
      level: 'error',
      msg: `${cname} numbers need ${fmt.digit_count} digits — you have ${digits.length} (${note}).`,
    }
  }
  return { ok: true, level: 'success', msg: `Valid ${cname} number.` }
})

// ── DELETE WIZARD ────────────────────────────────────────────
// Two-step soft-delete: pick a reason, confirm, then archive the record.
const showDeleteModal = ref(false)
const deleteReason = ref('')
const deleteOtherReason = ref('')
const deleting = ref(false)

// ── FILE UPLOAD ──────────────────────────────────────────────
// Inputs flow through uploadAttachment (ir.attachment create).
const uploadInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const uploadSuccess = ref(false)

// ── STATUS OPTIONS ───────────────────────────────────────────
// Values match the `status` selection on student.lead.
const STATUS_OPTIONS = [
  { value: 'new', label: 'New Inquiry' },
  { value: 'options_sent', label: 'Options Sent' },
  { value: 'chosen', label: 'University Chosen' },
  { value: 'docs', label: 'Collecting Documents' },
  { value: 'enrolled', label: 'Enrolled' },
  { value: 'lost', label: 'Lost' },
]

const DELETE_REASONS = [
  { value: 'enrolled', label: 'Completed Enrollment' },
  { value: 'paid', label: 'Paid Fees' },
  { value: 'documents', label: 'Completed Document Upload' },
  { value: 'other', label: 'Other' },
]

// ── LIFECYCLE ────────────────────────────────────────────────
// Initial load + hourly background refresh.
onMounted(async () => {
  await Promise.all([
    studentsStore.fetchStudent(studentId),
    studentsStore.fetchCountries(),
    studentsStore.fetchPhoneFormats(),
  ])
  const pollInterval = setInterval(async () => {
    await studentsStore.fetchStudent(studentId)
  }, 3600000) // 1 hour
  onUnmounted(() => clearInterval(pollInterval))
})

// Manual refresh button — same fetch path as the onMounted call.
async function refreshStudent() {
  refreshing.value = true
  try {
    await studentsStore.fetchStudent(studentId)
  } catch (e) {
    // errors surfaced via store
  } finally {
    refreshing.value = false
  }
}

const student = computed(() => studentsStore.currentStudent)
const attachments = computed(() => studentsStore.attachments)

// Full portal URL we show students. Uses the current origin so it
// works whether the app is served by Vite (dev) or Odoo on :8069.
const portalUrl = computed(() => {
  if (!student.value) return ''
  return `${window.location.origin}/app/portal/${odooVal(student.value.portal_token)}`
})

// ── COPY LINK ────────────────────────────────────────────────
// Works on insecure origins where navigator.clipboard is unavailable.
function handleCopyLink() {
  try {
    const el = document.createElement('textarea')
    el.value = portalUrl.value
    document.body.appendChild(el)
    el.select()
    document.execCommand('copy')
    document.body.removeChild(el)
  } catch {}
  copied.value = true
  setTimeout(() => copied.value = false, 2000)
}

// ── EDIT ─────────────────────────────────────────────────────
// startEdit seeds editForm from the currently displayed record.
function startEdit() {
  if (!student.value) return
  editForm.value = {
    name: student.value.name || '',
    email: student.value.email || '',
    phoneCountryId: Array.isArray(student.value.phone_country_id) ? student.value.phone_country_id[0] : student.value.phone_country_id || '',
    phone: student.value.phone || '',
    countryId: Array.isArray(student.value.country_id) ? student.value.country_id[0] : student.value.country_id || '',
    degreeLevel: student.value.degree_level || '',
    specialization: student.value.specialization || '',
    followUpDate: student.value.follow_up_date || '',
    notes: student.value.notes || '',
    userId: Array.isArray(student.value.user_id) ? student.value.user_id[0] : student.value.user_id || '',
    status: student.value.status,
    budget_amount: student.value.budget_amount || 0,
    budget_min: student.value.budget_min || 0,
    budget_max: student.value.budget_max || 0,
  }
  editing.value = true
}

// Persists edit via the store (writes + re-reads the record).
// Translate camelCase form keys to the snake_case field names that
// Odoo expects on student.lead before sending the payload.
async function saveEdit() {
  if (!phoneCheck.value.ok) {
    alert(phoneCheck.value.msg)
    return
  }
  saving.value = true
  try {
    const f = editForm.value
    const values: Record<string, unknown> = {
      name: (f.name ?? '').toString().trim(),
      email: (f.email ?? '').toString().trim(),
      phone: (f.phone ?? '').toString().trim(),
      phone_country_id: f.phoneCountryId ? Number(f.phoneCountryId) : false,
      country_id: f.countryId ? Number(f.countryId) : false,
      degree_level: f.degreeLevel || false,
      specialization: f.specialization || false,
      follow_up_date: f.followUpDate || false,
      notes: f.notes ?? '',
      user_id: f.userId ? Number(f.userId) : false,
      status: f.status,
      budget_amount: Number(f.budget_amount) || 0,
      budget_min: Number(f.budget_min) || 0,
      budget_max: Number(f.budget_max) || 0,
    }
    await studentsStore.updateStudent(studentId, values)
    editing.value = false
  } catch (e: any) {
    alert(e.message || 'Failed to save')
  }
  saving.value = false
}

function cancelEdit() {
  editing.value = false
  editForm.value = {}
}

// ── STATUS CHANGE ────────────────────────────────────────────
async function handleStatusChange(newStatus: string) {
  await studentsStore.updateStatus(studentId, newStatus as any)
}

// ── DELETE ───────────────────────────────────────────────────
async function confirmDelete() {
  if (!deleteReason.value) return
  if (deleteReason.value === 'other' && !deleteOtherReason.value.trim()) return
  deleting.value = true
  try {
    // Create archive record then delete
    await odoo.create('student.archive', {
      name: student.value?.name,
      email: student.value?.email,
      phone: student.value?.phone,
      phone2: student.value?.phone2,
      phone_full: student.value?.phone_full,
      phone_country_id: safeM2oId(student.value?.phone_country_id),
      country_id: safeM2oId(student.value?.country_id),
      degree_level: student.value?.degree_level,
      specialization: student.value?.specialization,
      specialization_other: student.value?.specialization_other,
      status: student.value?.status,
      currency_id: safeM2oId(student.value?.currency_id),
      budget_amount: student.value?.budget_amount || 0,
      budget_min: student.value?.budget_min || 0,
      budget_max: student.value?.budget_max || 0,
      date_contacted: student.value?.date_contacted,
      follow_up_date: student.value?.follow_up_date,
      notes: student.value?.notes,
      user_id: safeM2oId(student.value?.user_id),
      delete_reason: deleteReason.value,
      delete_reason_text: deleteOtherReason.value,
    })
    await odoo.unlink('student.lead', [studentId])
    showDeleteModal.value = false
    router.push(auth.isSuperAdmin ? '/admin' : auth.isManager ? '/manager' : '/employee')
  } catch (e: any) {
    alert(e.message || 'Failed to delete')
  }
  deleting.value = false
}

// ── FILE UPLOAD ──────────────────────────────────────────────
async function handleFileUpload(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files?.length) return
  uploading.value = true
  try {
    for (const file of Array.from(input.files)) {
      await uploadAttachment(file, 'student.lead', studentId)
    }
    await studentsStore.fetchStudent(studentId)
    uploadSuccess.value = true
    setTimeout(() => uploadSuccess.value = false, 3000)
  } catch (err: any) {
    alert(err.message || 'Upload failed')
  }
  uploading.value = false
  if (uploadInput.value) uploadInput.value.value = ''
}

// ── FILE DELETE ──────────────────────────────────────────────
async function deleteAttachment(attachmentId: number) {
  if (!confirm('Delete this file?')) return
  try {
    await odoo.unlink('ir.attachment', [attachmentId])
    await studentsStore.fetchStudent(studentId)
  } catch (e: any) {
    alert(e.message || 'Failed to delete file')
  }
}

// ── HELPERS ──────────────────────────────────────────────────
function formatSize(bytes: number) {
  if (!bytes) return '—'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function initials(name: string) {
  return name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
}

function safeM2oId(value: any) {
  if (Array.isArray(value) && value.length) return value[0]
  return false
}
function goHome() {
  router.push(auth.isSuperAdmin ? '/admin' : auth.isManager ? '/manager' : '/employee')
}
</script>

<template>
  <div class="flex h-screen" style="background-color: #F7F5F0; min-width: 1200px">
    <AppSidebar :current-view="sidebarView"
      @view-change="v => { sidebarView = v; goHome() }" />

    <div class="flex-1 flex flex-col overflow-hidden" style="margin-left: 260px">
      <!-- Top Bar -->
      <header class="bg-white border-b border-gray-100 px-8 py-4 flex items-center gap-4 flex-shrink-0">
        <button @click="goHome()" class="flex items-center gap-2 text-gray-500 hover:text-[#162340] transition-colors group">
          <div class="w-8 h-8 rounded-lg border border-gray-200 flex items-center justify-center group-hover:border-[#162340]/30 group-hover:bg-[#162340]/5 transition-all">
            <ArrowLeft class="w-4 h-4" />
          </div>
          <span class="text-sm font-medium">Back</span>
        </button>
        <div class="w-px h-6 bg-gray-200" />

        <div v-if="studentsStore.loading" class="flex-1 text-gray-400 text-sm">Loading...</div>
        <template v-else-if="student">
          <div class="flex items-center gap-3 flex-1">
            <div class="w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold text-white" style="background-color: #162340; font-family: Sora, sans-serif">
              {{ initials(student.name) }}
            </div>
            <div>
              <h1 class="text-[#162340] font-bold" style="font-family: Sora, sans-serif; font-size: 18px">{{ student.name }}</h1>
              <p class="text-xs text-gray-500 mt-0.5">ID #{{ student.id }} · {{ student.date_contacted || 'No date' }}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <!-- WhatsApp -->
            <a v-if="student.whatsapp_url" :href="student.whatsapp_url" target="_blank"
              class="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium bg-green-50 text-green-700 hover:bg-green-100 border border-green-200 transition-all">
              <MessageCircle class="w-3.5 h-3.5" /> WhatsApp
            </a>
            <!-- Email -->
            <a v-if="student.email" :href="`https://mail.google.com/mail/?view=cm&fs=1&to=${student.email}`" target="_blank"
              class="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 transition-all">
              <Mail class="w-3.5 h-3.5" /> Email
            </a>
            <!-- Refresh -->
            <button @click="refreshStudent" :disabled="refreshing"
              class="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium bg-gray-50 text-gray-700 hover:bg-gray-100 border border-gray-200 transition-all">
              <RotateCw class="w-3.5 h-3.5" />
              <span v-if="refreshing">Refreshing...</span>
              <span v-else>Refresh</span>
            </button>
            <!-- Edit -->
            <button v-if="!editing" @click="startEdit"
              class="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200 transition-all">
              <Edit3 class="w-3.5 h-3.5" /> Edit
            </button>
            <!-- Delete -->
            <button @click="showDeleteModal = true"
              class="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium bg-red-50 text-red-700 hover:bg-red-100 border border-red-200 transition-all">
              <Trash2 class="w-3.5 h-3.5" /> Delete
            </button>
            <StatusBadge :status="student.status" size="lg" />
          </div>
        </template>
      </header>

      <main v-if="student" class="flex-1 overflow-y-auto p-8 space-y-6">

        <!-- ── EDIT FORM ── -->
        <div v-if="editing" class="bg-white rounded-2xl border-2 border-amber-200 shadow-sm p-6">
          <div class="flex items-center justify-between mb-5">
            <h3 class="font-semibold text-[#162340]" style="font-family: Sora, sans-serif; font-size: 16px">Edit Student</h3>
            <div class="flex gap-2">
              <button @click="cancelEdit" class="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium border border-gray-200 text-gray-600 hover:bg-gray-50">
                <X class="w-4 h-4" /> Cancel
              </button>
              <button @click="saveEdit" :disabled="saving"
                class="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium bg-[#162340] text-white hover:opacity-90 disabled:opacity-60">
                <Check class="w-4 h-4" /> {{ saving ? 'Saving...' : 'Save Changes' }}
              </button>
            </div>
          </div>
          <div class="grid gap-4 md:grid-cols-2">
            <div class="md:col-span-2">
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Student Name</label>
              <input v-model="editForm.name" required type="text" placeholder="Enter the student's full name"
                class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15" />
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Email</label>
              <input v-model="editForm.email" type="email" placeholder="student@example.com"
                class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15" />
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Nationality</label>
              <select v-model="editForm.countryId"
                class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15">
                <option value="">Select nationality</option>
                <option v-for="country in studentsStore.countries" :key="country.id" :value="country.id">{{ country.name }}</option>
              </select>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Phone Country Code</label>
              <select v-model="editForm.phoneCountryId"
                class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15">
                <option value="">Select code</option>
                <option v-for="country in studentsStore.countries" :key="country.id" :value="country.id">{{ country.name }}<span v-if="country.code"> ({{ country.code }})</span></option>
              </select>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Phone Number</label>
              <input v-model="editForm.phone" type="text" placeholder="Student phone number"
                :class="[
                  'w-full rounded-2xl border bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:ring-2',
                  phoneCheck.level === 'error'
                    ? 'border-red-300 focus:border-red-400 focus:ring-red-100'
                    : phoneCheck.level === 'success'
                    ? 'border-emerald-300 focus:border-emerald-400 focus:ring-emerald-100'
                    : 'border-gray-200 focus:border-[#162340]/40 focus:ring-[#162340]/15',
                ]" />
              <p v-if="phoneCheck.msg"
                :class="[
                  'mt-1.5 text-xs',
                  phoneCheck.level === 'error'
                    ? 'text-red-600'
                    : phoneCheck.level === 'success'
                    ? 'text-emerald-600'
                    : 'text-gray-500',
                ]">
                {{ phoneCheck.msg }}
              </p>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Degree Level</label>
              <select v-model="editForm.degreeLevel"
                class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15">
                <option value="">Select degree</option>
                <option v-for="[value, label] in degreeOptions" :key="value" :value="value">{{ label }}</option>
              </select>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Specialization</label>
              <select v-model="editForm.specialization"
                class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15">
                <option value="">Select specialization</option>
                <option v-for="[value, label] in specializationOptions" :key="value" :value="value">{{ label }}</option>
              </select>
            </div>
            <div v-if="advisorOptions && advisorOptions.length">
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Assigned Employee</label>
              <select v-model="editForm.userId"
                class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15">
                <option value="">Assign automatically</option>
                <option v-for="advisor in advisorOptions" :key="advisor.id" :value="advisor.id">{{ advisor.name }}</option>
              </select>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Follow-up Date</label>
              <input v-model="editForm.followUpDate" type="date"
                class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Status</label>
              <select v-model="editForm.status"
                class="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm text-[#162340] focus:outline-none focus:border-[#B8966A]">
                <option v-for="s in STATUS_OPTIONS" :key="s.value" :value="s.value">{{ s.label }}</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Exact Budget</label>
              <input v-model="editForm.budget_amount" type="number" min="0"
                class="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm text-[#162340] focus:outline-none focus:border-[#B8966A]" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Budget From</label>
              <input v-model="editForm.budget_min" type="number" min="0"
                class="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm text-[#162340] focus:outline-none focus:border-[#B8966A]" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Budget To</label>
              <input v-model="editForm.budget_max" type="number" min="0"
                class="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm text-[#162340] focus:outline-none focus:border-[#B8966A]" />
            </div>
            <div class="md:col-span-2">
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Notes</label>
              <textarea v-model="editForm.notes" rows="4" placeholder="Add any context for the admissions team"
                class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15" />
            </div>
          </div>
        </div>

        <!-- Progress Steps -->
        <div class="bg-white rounded-2xl border border-gray-100 shadow-sm px-8 py-6">
          <div class="flex items-center justify-between mb-5">
            <h3 class="text-sm font-semibold text-gray-500 uppercase tracking-wider">Application Progress</h3>
            <!-- Quick status change -->
            <select @change="e => handleStatusChange((e.target as HTMLSelectElement).value)"
              :value="student.status"
              class="text-xs px-3 py-1.5 border border-gray-200 rounded-lg text-[#162340] focus:outline-none focus:border-[#B8966A] cursor-pointer">
              <option v-for="s in STATUS_OPTIONS" :key="s.value" :value="s.value">{{ s.label }}</option>
            </select>
          </div>
          <ProgressSteps :current-status="student.status" />
        </div>

        <!-- Info Cards -->
        <div class="grid grid-cols-3 gap-5">
          <!-- Contact -->
          <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
            <div class="flex items-center gap-2 mb-5">
              <div class="w-8 h-8 rounded-lg flex items-center justify-center" style="background-color: rgba(22,35,64,0.08)">
                <User class="w-4 h-4 text-[#162340]" />
              </div>
              <h3 class="font-semibold text-[#162340]" style="font-family: Sora, sans-serif; font-size: 14px">Contact Information</h3>
            </div>
            <div class="space-y-3.5">
              <div v-for="item in [
                { icon: Mail, label: 'Email', value: odooVal(student.email) },
                { icon: Phone, label: 'Phone', value: odooVal(student.phone_full) },
                { icon: Phone, label: 'Second Phone', value: odooVal(student.phone2) },
                { icon: Globe, label: 'Nationality', value: odooM2o(student.country_id) },
                { icon: User, label: 'Assigned To', value: odooM2o(student.user_id) },
              ].filter(i => i.value)" :key="item.label" class="flex items-start gap-3">
                <div class="w-7 h-7 rounded-lg bg-gray-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <component :is="item.icon" class="w-3.5 h-3.5 text-gray-500" />
                </div>
                <div>
                  <p class="text-xs text-gray-400">{{ item.label }}</p>
                  <p class="text-sm font-medium text-[#162340] mt-0.5">{{ item.value }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Academic -->
          <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
            <div class="flex items-center gap-2 mb-5">
              <div class="w-8 h-8 rounded-lg flex items-center justify-center" style="background-color: rgba(184,150,106,0.12)">
                <BookOpen class="w-4 h-4" style="color: #B8966A" />
              </div>
              <h3 class="font-semibold text-[#162340]" style="font-family: Sora, sans-serif; font-size: 14px">Academic Information</h3>
            </div>
            <div class="space-y-3.5">
              <div v-for="item in [
                { icon: GraduationCap, label: 'Degree Level', value: DEGREE_LABELS[odooVal(student.degree_level)] || odooVal(student.degree_level) },
                { icon: BookOpen, label: 'Specialization', value: odooVal(student.specialization_display) },
                { icon: Calendar, label: 'Date Contacted', value: odooVal(student.date_contacted) },
                { icon: Calendar, label: 'Follow-up Date', value: odooVal(student.follow_up_date) },
              ].filter(i => i.value)" :key="item.label" class="flex items-start gap-3">
                <div class="w-7 h-7 rounded-lg bg-gray-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <component :is="item.icon" class="w-3.5 h-3.5 text-gray-500" />
                </div>
                <div>
                  <p class="text-xs text-gray-400">{{ item.label }}</p>
                  <p class="text-sm font-medium text-[#162340] mt-0.5">{{ item.value }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Budget -->
          <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
            <div class="flex items-center gap-2 mb-5">
              <div class="w-8 h-8 rounded-lg flex items-center justify-center bg-green-50">
                <DollarSign class="w-4 h-4 text-green-600" />
              </div>
              <h3 class="font-semibold text-[#162340]" style="font-family: Sora, sans-serif; font-size: 14px">Budget & Finances</h3>
            </div>
            <div class="space-y-3.5">
              <div v-if="student.budget_display" class="flex items-start gap-3">
                <div class="w-7 h-7 rounded-lg bg-gray-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <DollarSign class="w-3.5 h-3.5 text-gray-500" />
                </div>
                <div>
                  <p class="text-xs text-gray-400">Budget</p>
                  <p class="text-sm font-medium text-[#162340] mt-0.5">{{ student.budget_display }}</p>
                </div>
              </div>
              <!-- Budget Range -->
              <div v-if="student.budget_min || student.budget_max" class="flex items-start gap-3">
                <div class="w-7 h-7 rounded-lg bg-gray-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <DollarSign class="w-3.5 h-3.5 text-gray-500" />
                </div>
                <div>
                  <p class="text-xs text-gray-400">Budget Range</p>
                  <p class="text-sm font-medium text-[#162340] mt-0.5">
                    {{ student.budget_min ? `$${Number(student.budget_min).toLocaleString()}` : '—' }}
                    →
                    {{ student.budget_max ? `$${Number(student.budget_max).toLocaleString()}` : '—' }}
                  </p>
                </div>
              </div>
              <div v-if="student.currency_id" class="flex items-start gap-3">
                <div class="w-7 h-7 rounded-lg bg-gray-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Award class="w-3.5 h-3.5 text-gray-500" />
                </div>
                <div>
                  <p class="text-xs text-gray-400">Currency</p>
                  <p class="text-sm font-medium text-[#162340] mt-0.5">{{ odooM2o(student.currency_id) }}</p>
                </div>
              </div>
              <div class="pt-3 border-t border-gray-100">
                <p class="text-xs text-gray-400 mb-1">Attachments</p>
                <span class="text-2xl font-bold text-[#162340]" style="font-family: Sora, sans-serif">{{ attachments.length }}</span>
                <span class="text-xs text-gray-500 ml-1">files uploaded</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Notes -->
        <div v-if="student.notes" class="bg-[#162340]/5 rounded-2xl border border-[#162340]/10 p-5">
          <div class="flex items-center gap-2 mb-2">
            <FileText class="w-4 h-4 text-[#162340]" />
            <span class="text-sm font-semibold text-[#162340]" style="font-family: Sora, sans-serif">Advisor Notes</span>
          </div>
          <p class="text-sm text-gray-600 leading-relaxed">{{ student.notes }}</p>
        </div>

        <!-- Documents -->
        <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
          <div class="flex items-center justify-between mb-5">
            <div>
              <h3 class="font-semibold text-[#162340]" style="font-family: Sora, sans-serif; font-size: 16px">Uploaded Documents</h3>
              <p class="text-xs text-gray-500 mt-0.5">{{ attachments.length }} file{{ attachments.length !== 1 ? 's' : '' }} from Odoo</p>
            </div>
            <!-- Upload button -->
            <label class="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium cursor-pointer transition-all"
              :style="{ backgroundColor: uploadSuccess ? '#22c55e' : '#162340', color: 'white' }">
              <Upload class="w-4 h-4" />
              {{ uploading ? 'Uploading...' : uploadSuccess ? 'Uploaded!' : 'Upload File' }}
              <input ref="uploadInput" type="file" multiple class="hidden" @change="handleFileUpload" :disabled="uploading"/>
            </label>
          </div>

          <div v-if="attachments.length === 0" class="text-center py-12 border-2 border-dashed border-gray-200 rounded-xl">
            <div class="w-12 h-12 bg-gray-100 rounded-xl mx-auto flex items-center justify-center mb-3">
              <FileText class="w-6 h-6 text-gray-400" />
            </div>
            <p class="text-gray-500 text-sm font-medium">No documents uploaded yet</p>
            <p class="text-gray-400 text-xs mt-1">Upload files or share the portal link with the student.</p>
          </div>
          <div v-else class="space-y-2">
            <div v-for="att in attachments" :key="att.id"
              class="flex items-center gap-4 px-4 py-3.5 rounded-xl border border-gray-100 hover:border-gray-200 hover:bg-gray-50/50 transition-all group">
              <div class="text-2xl flex-shrink-0">
                {{ att.mimetype?.includes('pdf') ? '📄' : att.mimetype?.includes('image') ? '🖼' : '📝' }}
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-[#162340] truncate">{{ att.name }}</p>
                <p class="text-xs text-gray-400 mt-0.5">{{ formatSize(att.file_size) }} · {{ att.create_date?.slice(0, 10) }}</p>
              </div>
              <div class="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-all">
                <a :href="attachmentUrl(att.id)" target="_blank"
                  class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 text-xs font-medium text-gray-600 hover:bg-[#162340] hover:text-white hover:border-[#162340] transition-all">
                  <Download class="w-3 h-3" /> Download
                </a>
                <button @click="deleteAttachment(att.id)"
                  class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-red-200 text-xs font-medium text-red-600 hover:bg-red-600 hover:text-white transition-all">
                  <Trash2 class="w-3 h-3" /> Delete
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Portal Link -->
        <div class="rounded-2xl border p-6" style="background-color: rgba(184,150,106,0.06); border-color: rgba(184,150,106,0.25)">
          <div class="flex items-center gap-2 mb-1">
            <ExternalLink class="w-4 h-4" style="color: #B8966A" />
            <h3 class="font-semibold" style="font-family: Sora, sans-serif; font-size: 14px; color: #162340">Student Portal Link</h3>
          </div>
          <p class="text-xs text-gray-500 mb-4">Share this link with the student so they can upload their documents.</p>
          <div class="flex items-center gap-3">
            <div class="flex-1 px-4 py-3 rounded-xl border font-mono text-sm text-gray-600 truncate bg-white" style="border-color: rgba(184,150,106,0.3)">
              {{ portalUrl }}
            </div>
            <button @click="handleCopyLink"
              class="flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium text-white transition-all flex-shrink-0"
              :style="{ backgroundColor: copied ? '#22c55e' : '#B8966A' }">
              <CheckCheck v-if="copied" class="w-4 h-4" /><Copy v-else class="w-4 h-4" />
              {{ copied ? 'Copied!' : 'Copy Link' }}
            </button>
            <a :href="portalUrl" target="_blank"
              class="flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium border border-gray-200 text-gray-600 hover:bg-gray-50 transition-all flex-shrink-0">
              <ExternalLink class="w-4 h-4" /> Open Portal
            </a>
          </div>
        </div>
      </main>

      <!-- Loading state -->
      <div v-else-if="studentsStore.loading" class="flex-1 flex items-center justify-center">
        <div class="text-center">
          <div class="w-12 h-12 border-4 border-[#B8966A] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p class="text-gray-500 text-sm">Loading student data...</p>
        </div>
      </div>
      <div v-else class="flex-1 flex items-center justify-center">
        <div class="text-center">
          <h2 class="text-[#162340] font-bold mb-2" style="font-family: Sora, sans-serif; font-size: 24px">Student Not Found</h2>
          <button @click="goHome()" class="text-sm text-[#B8966A] hover:underline">Go Home</button>
        </div>
      </div>
    </div>

    <!-- ── DELETE MODAL ── -->
    <div v-if="showDeleteModal" class="fixed inset-0 z-50 flex items-center justify-center" style="background: rgba(0,0,0,0.5)">
      <div class="bg-white rounded-2xl p-6 w-full max-w-md shadow-2xl">
        <div class="flex items-center gap-3 mb-5">
          <div class="w-10 h-10 rounded-xl bg-red-50 flex items-center justify-center">
            <Trash2 class="w-5 h-5 text-red-600" />
          </div>
          <div>
            <h3 class="font-bold text-[#162340]" style="font-family: Sora, sans-serif">Delete Student</h3>
            <p class="text-xs text-gray-500">This will archive the student record.</p>
          </div>
        </div>

        <div class="mb-4">
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Reason for Deletion</label>
          <select v-model="deleteReason"
            class="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm text-[#162340] focus:outline-none focus:border-red-400">
            <option value="">Select a reason...</option>
            <option v-for="r in DELETE_REASONS" :key="r.value" :value="r.value">{{ r.label }}</option>
          </select>
        </div>

        <div v-if="deleteReason === 'other'" class="mb-4">
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Please Specify</label>
          <textarea v-model="deleteOtherReason" rows="2"
            class="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm text-[#162340] focus:outline-none focus:border-red-400 resize-none"
            placeholder="Explain the reason..."/>
        </div>

        <div class="flex gap-3">
          <button @click="showDeleteModal = false; deleteReason = ''; deleteOtherReason = ''"
            class="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium border border-gray-200 text-gray-600 hover:bg-gray-50">
            Cancel
          </button>
          <button @click="confirmDelete" :disabled="!deleteReason || deleting || (deleteReason === 'other' && !deleteOtherReason.trim())"
            class="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium bg-red-600 text-white hover:bg-red-700 disabled:opacity-50">
            {{ deleting ? 'Deleting...' : 'Confirm Delete' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>