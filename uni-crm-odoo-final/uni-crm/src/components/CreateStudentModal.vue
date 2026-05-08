<!-- CreateStudentModal — creates a student.lead record.
     allowAssign=true (admin/manager) shows the "Assigned Employee" field. -->
<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { LoaderCircle, UserPlus, X } from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'
import { useStudentsStore } from '../stores/students'
import { DEGREE_LABELS, SPECIALIZATION_LABELS } from '../types/odoo'

// ── PROPS / EMITS ────────────────────────────────────────────
const props = withDefaults(defineProps<{
  open: boolean
  allowAssign?: boolean
}>(), {
  allowAssign: false,
})

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'created', studentId: number): void
}>()

const auth = useAuthStore()
const studentsStore = useStudentsStore()
const saving = ref(false)
const formError = ref('')

// ── FORM MODEL ───────────────────────────────────────────────
// Mirrors the create payload. Empty strings => omitted on submit.
const form = reactive({
  name: '',
  email: '',
  phoneCountryId: '',
  phone: '',
  countryId: '',
  degreeLevel: '',
  specialization: '',
  followUpDate: '',
  notes: '',
  userId: '',
  status: '',
  budget_amount: '',
  budget_min: '',
  budget_max: '',
})

// ── SELECT OPTIONS ───────────────────────────────────────────
const degreeOptions = Object.entries(DEGREE_LABELS)
const specializationOptions = Object.entries(SPECIALIZATION_LABELS)
const advisorOptions = computed(() => studentsStore.employees)

// Preload countries + phone formats (always) and users (assign-only).
onMounted(async () => {
  await Promise.all([
    studentsStore.fetchCountries(),
    studentsStore.fetchPhoneFormats(),
  ])
  if (props.allowAssign) {
    await studentsStore.fetchUsers()
  }
})

// ── PHONE VALIDATION ─────────────────────────────────────────
// Live-checks the phone against the phone.country.format rule of the
// currently-selected phone country. Returns a hint shown under the input
// and an `ok` flag the submit handler uses to block save.
const phoneCheck = computed(() => {
  const cid = Number(form.phoneCountryId)
  const raw = (form.phone || '').toString()
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

// ── HANDLERS ─────────────────────────────────────────────────
function closeModal() {
  if (saving.value) return
  emit('close')
}

function resetForm() {
  form.name = ''
  form.email = ''
  form.phoneCountryId = ''
  form.phone = ''
  form.countryId = ''
  form.degreeLevel = ''
  form.specialization = ''
  form.followUpDate = ''
  form.notes = ''
  form.userId = ''
  form.status = ''
  form.budget_amount = ''
  form.budget_min = ''
  form.budget_max = ''
  formError.value = ''
}

// Build the Odoo payload lazily — only include fields the user filled.
async function handleSubmit() {
  formError.value = ''
  saving.value = true

  try {
    if (!phoneCheck.value.ok) {
      formError.value = phoneCheck.value.msg
      saving.value = false
      return
    }
    const values: Record<string, unknown> = {
      name: form.name.trim(),
      status: form.status || 'new',
    }

    if (form.email.trim()) values.email = form.email.trim()
    if (form.phone.trim()) values.phone = form.phone.trim()
    if (form.phoneCountryId) values.phone_country_id = Number(form.phoneCountryId)
    if (form.countryId) values.country_id = Number(form.countryId)
    if (form.degreeLevel) values.degree_level = form.degreeLevel
    if (form.specialization) values.specialization = form.specialization
    if (form.followUpDate) values.follow_up_date = form.followUpDate
    if (form.notes.trim()) values.notes = form.notes.trim()
    if (form.budget_amount) values.budget_amount = Number(form.budget_amount)
    if (form.budget_min) values.budget_min = Number(form.budget_min)
    if (form.budget_max) values.budget_max = Number(form.budget_max)
    if (props.allowAssign && form.userId) values.user_id = Number(form.userId)

    const id = await studentsStore.createStudent(values)
    resetForm()
    emit('created', id)
    emit('close')
  } catch (e: any) {
    formError.value = e.message || 'Unable to create student.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-[80] flex items-center justify-center bg-[#162340]/45 px-4 py-8">
    <div class="w-full max-w-3xl rounded-[28px] border border-white/60 bg-[#FAFAF8] shadow-2xl flex flex-col max-h-[90vh]">
      <div class="flex items-start justify-between border-b border-gray-200 px-7 py-5 flex-shrink-0">
        <div class="flex items-center gap-3">
          <div class="flex h-11 w-11 items-center justify-center rounded-2xl text-white" style="background-color: #162340">
            <UserPlus class="h-5 w-5" />
          </div>
          <div>
            <h2 class="text-[22px] font-bold text-[#162340]" style="font-family: Sora, sans-serif">Create Student</h2>
            <p class="mt-0.5 text-sm text-gray-500">
              Add a new lead using the same admissions flow your Odoo module uses.
            </p>
          </div>
        </div>
        <button
          type="button"
          @click="closeModal"
          class="flex h-10 w-10 items-center justify-center rounded-xl border border-gray-200 text-gray-500 transition-all hover:bg-white hover:text-[#162340]"
        >
          <X class="h-4 w-4" />
        </button>
      </div>

      <form class="flex flex-col flex-1 overflow-hidden" @submit.prevent="handleSubmit">
        <div class="overflow-y-auto flex-1 px-7 py-6">
        <div class="space-y-6">
          <!-- Student Name (Full Width) -->
          <div class="grid grid-cols-1">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Student Name</label>
              <input
                v-model="form.name"
                required
                type="text"
                placeholder="Enter the student's full name"
                class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15"
              />
            </div>
          </div>

          <!-- Email & Nationality -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Email</label>
              <input
                v-model="form.email"
                type="email"
                placeholder="student@example.com"
                class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15"
              />
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Nationality</label>
              <select
                v-model="form.countryId"
                class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15"
              >
                <option value="">Select nationality</option>
                <option v-for="country in studentsStore.countries" :key="country.id" :value="country.id">
                  {{ country.name }}
                </option>
              </select>
            </div>
          </div>

          <!-- Phone Country Code & Phone Number -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Phone Country Code</label>
              <select
                v-model="form.phoneCountryId"
                class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15"
              >
                <option value="">Select code</option>
                <option v-for="country in studentsStore.countries" :key="country.id" :value="country.id">
                  {{ country.name }}<span v-if="country.code"> ({{ country.code }})</span>
                </option>
              </select>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Phone Number</label>
              <input
                v-model="form.phone"
                type="text"
                placeholder="Student phone number"
                :class="[
                  'w-full rounded-2xl border bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:ring-2',
                  phoneCheck.level === 'error'
                    ? 'border-red-300 focus:border-red-400 focus:ring-red-100'
                    : phoneCheck.level === 'success'
                    ? 'border-emerald-300 focus:border-emerald-400 focus:ring-emerald-100'
                    : 'border-gray-200 focus:border-[#162340]/40 focus:ring-[#162340]/15',
                ]"
              />
              <p
                v-if="phoneCheck.msg"
                :class="[
                  'mt-1.5 text-xs',
                  phoneCheck.level === 'error'
                    ? 'text-red-600'
                    : phoneCheck.level === 'success'
                    ? 'text-emerald-600'
                    : 'text-gray-500',
                ]"
              >
                {{ phoneCheck.msg }}
              </p>
            </div>
          </div>

          <!-- Degree Level & Specialization -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Degree Level</label>
              <select
                v-model="form.degreeLevel"
                class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15"
              >
                <option value="">Select degree</option>
                <option v-for="[value, label] in degreeOptions" :key="value" :value="value">{{ label }}</option>
              </select>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Specialization</label>
              <select
                v-model="form.specialization"
                class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15"
              >
                <option value="">Select specialization</option>
                <option v-for="[value, label] in specializationOptions" :key="value" :value="value">{{ label }}</option>
              </select>
            </div>
          </div>

          <!-- Assigned Employee & Status -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div v-if="allowAssign">
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Assigned Employee</label>
              <select
                v-model="form.userId"
                class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15"
              >
                <option value="">Assign automatically</option>
                <option v-for="advisor in advisorOptions" :key="advisor.id" :value="advisor.id">
                  {{ advisor.name }}
                </option>
              </select>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Status</label>
              <select
                v-model="form.status"
                class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15"
              >
                <option value="new">New Inquiry</option>
                <option value="options_sent">Options Sent</option>
                <option value="chosen">University Chosen</option>
                <option value="docs">Collecting Documents</option>
                <option value="enrolled">Enrolled</option>
                <option value="lost">Lost</option>
              </select>
            </div>
          </div>

          <!-- Budget Amount & Budget From -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Exact Budget</label>
              <input
                v-model="form.budget_amount"
                type="number"
                min="0"
                placeholder="0"
                class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15"
              />
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Budget From</label>
              <input
                v-model="form.budget_min"
                type="number"
                min="0"
                placeholder="0"
                class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15"
              />
            </div>
          </div>

          <!-- Budget To & Follow-up Date -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Budget To</label>
              <input
                v-model="form.budget_max"
                type="number"
                min="0"
                placeholder="0"
                class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15"
              />
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Follow-up Date</label>
              <input
                v-model="form.followUpDate"
                type="date"
                class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15"
              />
            </div>
          </div>

          <!-- Notes (Full Width) -->
          <div class="grid grid-cols-1">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Notes</label>
              <textarea
                v-model="form.notes"
                rows="4"
                placeholder="Add any context for the admissions team"
                class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15"
              />
            </div>
          </div>

          <!-- Error Message -->
          <p v-if="formError" class="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{{ formError }}</p>
        </div>
        </div>

        <!-- Footer (Sticky) -->
        <div class="flex items-center justify-between border-t border-gray-200 px-7 py-5 flex-shrink-0 bg-[#FAFAF8]">
          <p class="text-xs text-gray-400">
            Signed in as {{ auth.userName }}. New students will be created directly in Odoo.
          </p>
          <div class="flex items-center gap-3">
            <button
              type="button"
              @click="closeModal"
              class="rounded-xl border border-gray-200 px-4 py-2.5 text-sm font-medium text-gray-600 transition-all hover:bg-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="saving"
              class="inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white transition-all disabled:opacity-70"
              style="background-color: #162340"
            >
              <LoaderCircle v-if="saving" class="h-4 w-4 animate-spin" />
              {{ saving ? 'Creating...' : 'Create Student' }}
            </button>
          </div>
        </div>
      </form>
    </div>
  </div>
</template>
