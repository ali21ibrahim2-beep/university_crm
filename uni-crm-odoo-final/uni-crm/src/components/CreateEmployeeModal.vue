<!-- CreateEmployeeModal — admin-only. Creates a res.users record
     and assigns the chosen University CRM role (Employee / Manager). -->
<script setup lang="ts">
import { reactive, ref } from 'vue'
import { LoaderCircle, UserPlus2, X } from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'
import { useStudentsStore } from '../stores/students'

// ── PROPS / EMITS ────────────────────────────────────────────
defineProps<{ open: boolean }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'created', userId: number): void
}>()

const auth = useAuthStore()
const studentsStore = useStudentsStore()
const saving = ref(false)
const formError = ref('')

// ── FORM MODEL ───────────────────────────────────────────────
// Mirrors the res.users payload sent on submit.
const form = reactive({
  name: '',
  login: '',
  email: '',
  password: '',
  password2: '',
  phone: '',
  role: 'employee' as 'employee' | 'manager',
})

function closeModal() {
  if (saving.value) return
  emit('close')
}

function resetForm() {
  form.name = ''
  form.login = ''
  form.email = ''
  form.password = ''
  form.password2 = ''
  form.phone = ''
  form.role = 'employee'
  formError.value = ''
}

// ── SUBMIT ───────────────────────────────────────────────────
async function handleSubmit() {
  formError.value = ''
  if (!form.name.trim() || !form.login.trim()) {
    formError.value = 'Name and login are required.'
    return
  }
  if (form.password && form.password.length < 6) {
    formError.value = 'Password must be at least 6 characters.'
    return
  }
  if (form.password !== form.password2) {
    formError.value = 'Passwords do not match.'
    return
  }

  saving.value = true
  try {
    const id = await studentsStore.createEmployee({
      name: form.name.trim(),
      login: form.login.trim(),
      email: form.email.trim() || undefined,
      password: form.password || undefined,
      phone: form.phone.trim() || undefined,
      role: form.role,
    })
    resetForm()
    emit('created', id)
    emit('close')
  } catch (e: any) {
    formError.value = e.message || 'Unable to create employee.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-[80] flex items-center justify-center bg-[#162340]/45 px-4 py-8">
    <div class="w-full max-w-2xl rounded-[28px] border border-white/60 bg-[#FAFAF8] shadow-2xl flex flex-col max-h-[90vh]">
      <!-- Header -->
      <div class="flex items-start justify-between border-b border-gray-200 px-7 py-5 flex-shrink-0">
        <div class="flex items-center gap-3">
          <div class="flex h-11 w-11 items-center justify-center rounded-2xl text-white" style="background-color: #B8966A">
            <UserPlus2 class="h-5 w-5" />
          </div>
          <div>
            <h2 class="text-[22px] font-bold text-[#162340]" style="font-family: Sora, sans-serif">Create Employee</h2>
            <p class="mt-0.5 text-sm text-gray-500">
              Add a new internal user and assign them the Employee or Manager role.
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
            <!-- Name -->
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">Full Name <span class="text-red-500">*</span></label>
              <input
                v-model="form.name"
                required
                type="text"
                placeholder="e.g. Sara Khalil"
                class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15"
              />
            </div>

            <!-- Login & Email -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="mb-1.5 block text-sm font-medium text-gray-700">Login <span class="text-red-500">*</span></label>
                <input
                  v-model="form.login"
                  required
                  type="text"
                  placeholder="username or email"
                  class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15"
                />
              </div>
              <div>
                <label class="mb-1.5 block text-sm font-medium text-gray-700">Email</label>
                <input
                  v-model="form.email"
                  type="email"
                  placeholder="employee@example.com"
                  class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15"
                />
              </div>
            </div>

            <!-- Phone & Role -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="mb-1.5 block text-sm font-medium text-gray-700">Phone</label>
                <input
                  v-model="form.phone"
                  type="text"
                  placeholder="Optional"
                  class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15"
                />
              </div>
              <div>
                <label class="mb-1.5 block text-sm font-medium text-gray-700">Role <span class="text-red-500">*</span></label>
                <select
                  v-model="form.role"
                  class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15"
                >
                  <option value="employee">Employee</option>
                  <option value="manager">Manager</option>
                </select>
              </div>
            </div>

            <!-- Password & Confirm -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="mb-1.5 block text-sm font-medium text-gray-700">Password</label>
                <input
                  v-model="form.password"
                  type="password"
                  placeholder="At least 6 characters"
                  class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15"
                />
              </div>
              <div>
                <label class="mb-1.5 block text-sm font-medium text-gray-700">Confirm Password</label>
                <input
                  v-model="form.password2"
                  type="password"
                  placeholder="Repeat password"
                  class="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 outline-none transition-all focus:border-[#162340]/40 focus:ring-2 focus:ring-[#162340]/15"
                />
              </div>
            </div>

            <p class="text-xs text-gray-400">
              If you leave the password blank, the employee will need to set it via the first-time login flow.
            </p>

            <p v-if="formError" class="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{{ formError }}</p>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-between border-t border-gray-200 px-7 py-5 flex-shrink-0 bg-[#FAFAF8]">
          <p class="text-xs text-gray-400">Signed in as {{ auth.userName }}.</p>
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
              style="background-color: #B8966A"
            >
              <LoaderCircle v-if="saving" class="h-4 w-4 animate-spin" />
              {{ saving ? 'Creating...' : 'Create Employee' }}
            </button>
          </div>
        </div>
      </form>
    </div>
  </div>
</template>
