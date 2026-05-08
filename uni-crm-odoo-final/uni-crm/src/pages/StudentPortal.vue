<!-- StudentPortal — token-based self-service for the student.
     Three views: login, set-password (first visit), dashboard.
     Uses pure-JS SHA-256 so it works on plain HTTP. -->
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'

// Token comes from /portal/:token route param.
const route = useRoute()
const token = computed(() => route.params.token as string)

// ── STATE ────────────────────────────────────────────────────
type View = 'login' | 'set-password' | 'dashboard'
const view = ref<View>('login')
const loading = ref(true)
const error = ref('')
const student = ref<any>(null)
const attachments = ref<any[]>([])

// Login form
const email = ref('')
const password = ref('')
const password2 = ref('')
const showPassword = ref(false)
const showPassword2 = ref(false)

// Upload
const selectedFiles = ref<File[]>([])
const uploading = ref(false)
const uploadSuccess = ref(false)

const ODOO = ''

// ── HELPERS ──────────────────────────────────────────────────
function hashPassword(pw: string): Promise<string> {
  // Pure JS SHA-256 — works on HTTP (no crypto.subtle needed)
  const salted = `univ_crm_salt_${pw}`
  return Promise.resolve(sha256(salted))
}

function sha256(str: string): string {
  function rightRotate(value: number, amount: number) {
    return (value >>> amount) | (value << (32 - amount))
  }
  const mathPow = Math.pow
  const maxWord = mathPow(2, 32)
  let result = ''
  const words: number[] = []
  const asciiBitLength = str.length * 8
  let hash = sha256.h = sha256.h || []
  const k = sha256.k = sha256.k || []
  let primeCounter = k.length
  const isComposite: Record<number, boolean> = {}
  for (let candidate = 2; primeCounter < 64; candidate++) {
    if (!isComposite[candidate]) {
      for (let i = 0; i < 313; i += candidate) isComposite[i] = true
      hash[primeCounter] = (mathPow(candidate, 0.5) * maxWord) | 0
      k[primeCounter++] = (mathPow(candidate, 1 / 3) * maxWord) | 0
    }
  }
  str += '\x80'
  while (str.length % 64 - 56) str += '\x00'
  for (let i = 0; i < str.length; i++) {
    const j = str.charCodeAt(i)
    if (j >> 8) return ''
    words[i >> 2] |= j << ((3 - i) % 4) * 8
  }
  words[words.length] = ((asciiBitLength / maxWord) | 0)
  words[words.length] = (asciiBitLength | 0)
  for (let j = 0; j < words.length;) {
    const w = words.slice(j, j += 16)
    const oldHash = hash.slice(0)
    for (let i = 0; i < 64; i++) {
      const w15 = w[i - 15], w2 = w[i - 2]
      const a = hash[0], e = hash[4]
      const temp1 = hash[7] +
        (rightRotate(e, 6) ^ rightRotate(e, 11) ^ rightRotate(e, 25)) +
        ((e & hash[5]) ^ (~e & hash[6])) + k[i] +
        (w[i] = (i < 16) ? w[i] : (
          w[i - 16] +
          (rightRotate(w15, 7) ^ rightRotate(w15, 18) ^ (w15 >>> 3)) +
          w[i - 7] +
          (rightRotate(w2, 17) ^ rightRotate(w2, 19) ^ (w2 >>> 10))
        ) | 0)
      const temp2 = (rightRotate(a, 2) ^ rightRotate(a, 13) ^ rightRotate(a, 22)) +
        ((a & hash[1]) ^ (a & hash[2]) ^ (hash[1] & hash[2]))
      hash = [temp1 + temp2, a, hash[1], hash[2], e + temp1, hash[4], hash[5], hash[6]]  // eslint-disable-line
    }
    hash = hash.map((x, i) => (x + oldHash[i]) | 0)  // eslint-disable-line
  }
  for (let i = 0; i < 8; i++) {
    for (let j = 3; j + 1; j--) {
      const b = (hash[i] >> (j * 8)) & 255
      result += ((b < 16) ? '0' : '') + b.toString(16)
    }
  }
  return result
}
sha256.h = [] as number[]
sha256.k = [] as number[]

async function apiFetch(path: string, opts: RequestInit = {}) {
  const res = await fetch(`${ODOO}${path}`, {
    credentials: 'include',
    ...opts,
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

// ── INIT ─────────────────────────────────────────────────────
onMounted(async () => {
  loading.value = true
  try {
    const data = await apiFetch(`/student/api/${token.value}`)
    if (data.error) {
      error.value = data.error
      loading.value = false
      return
    }
    student.value = data.student
    attachments.value = data.attachments || []
    email.value = student.value.email || ''

    // Check session
    const sessionToken = sessionStorage.getItem(`student_token_${token.value}`)
    if (sessionToken === token.value) {
      view.value = 'dashboard'
    } else {
      try {
        const pwCheck = await apiFetch(`/student/api/${token.value}/check-password`)
        if (pwCheck.has_password === false) {
          view.value = 'set-password'
        } else {
          view.value = 'login'
        }
      } catch {
        view.value = 'login'
      }
    }
  } catch (e: any) {
    error.value = e.message || 'Failed to load portal'
  }
  loading.value = false
})

// ── LOGIN ─────────────────────────────────────────────────────
async function handleLogin() {
  if (!email.value || !password.value) return
  error.value = ''
  loading.value = true
  try {
    const hash = await hashPassword(password.value)
    const res = await fetch(`/student/api/${token.value}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email: email.value, password_hash: hash }),
    })
    const data = await res.json()
    if (data.error) {
      error.value = data.error
    } else if (data.ok) {
      sessionStorage.setItem(`student_token_${token.value}`, token.value)
      student.value = data.student || student.value
      attachments.value = data.attachments || attachments.value
      view.value = 'dashboard'
    } else {
      error.value = 'Login failed. Please try again.'
    }
  } catch (e: any) {
    error.value = e.message || 'Login failed. Please try again.'
  }
  loading.value = false
}

// ── SET PASSWORD ──────────────────────────────────────────────
async function handleSetPassword() {
  if (!password.value || !password2.value) return
  if (password.value.length < 6) { error.value = 'Password must be at least 6 characters.'; return }
  if (password.value !== password2.value) { error.value = 'Passwords do not match.'; return }
  error.value = ''
  loading.value = true
  try {
    const hash = await hashPassword(password.value)
    const res = await fetch(`/student/api/${token.value}/set-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ password_hash: hash }),
    })
    const data = await res.json()
    if (data.error) {
      error.value = data.error
    } else if (data.ok) {
      sessionStorage.setItem(`student_token_${token.value}`, token.value)
      view.value = 'dashboard'
    } else {
      error.value = 'Failed to set password. Please try again.'
    }
  } catch (e: any) {
    error.value = e.message || 'Failed to set password. Please try again.'
  }
  loading.value = false
}

// ── UPLOAD ────────────────────────────────────────────────────
function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) selectedFiles.value = Array.from(input.files)
}

async function handleUpload() {
  if (!selectedFiles.value.length) return
  uploading.value = true
  uploadSuccess.value = false
  const form = new FormData()
  selectedFiles.value.forEach(f => form.append('files', f))
  try {
    const data = await apiFetch(`/student/api/${token.value}/upload`, {
      method: 'POST',
      body: form,
    })
    if (data.ok) {
      attachments.value = data.attachments || attachments.value
      selectedFiles.value = []
      uploadSuccess.value = true
      setTimeout(() => uploadSuccess.value = false, 3000)
    }
  } catch {
    error.value = 'Upload failed.'
  }
  uploading.value = false
}

function downloadUrl(id: number) {
  return `${ODOO}/student/api/${token.value}/attachment/${id}`
}

function formatSize(bytes: number) {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}

function formatDate(dt: string) {
  if (!dt) return ''
  return new Date(dt).toLocaleDateString()
}

function handleLogout() {
  sessionStorage.removeItem(`student_token_${token.value}`)
  view.value = 'login'
  password.value = ''
}



const STATUS_STEPS = [
  { key: 'new', label: 'New Inquiry' },
  { key: 'options_sent', label: 'Options Sent' },
  { key: 'chosen', label: 'University Chosen' },
  { key: 'docs', label: 'Collecting Docs' },
  { key: 'enrolled', label: 'Enrolled' },
]

function stepState(stepKey: string) {
  const keys = STATUS_STEPS.map(s => s.key)
  const cur = keys.indexOf(student.value?.status)
  const idx = keys.indexOf(stepKey)
  if (student.value?.status === stepKey) return 'current'
  if (idx < cur) return 'done'
  return ''
}
</script>

<template>
  <div style="font-family: 'Plus Jakarta Sans', sans-serif; min-height: 100vh; background: #F7F5F0;">

    <!-- ── LOADING ── -->
    <div v-if="loading" style="min-height:100vh;display:flex;align-items:center;justify-content:center;">
      <div style="text-align:center;">
        <div style="width:40px;height:40px;border:3px solid #e5e0d8;border-top-color:#162340;border-radius:50%;animation:spin 0.8s linear infinite;margin:0 auto 16px;"></div>
        <p style="color:#6b7280;font-size:.9rem;">Loading your portal...</p>
      </div>
    </div>

    <!-- ── INVALID TOKEN ── -->
    <div v-else-if="error && !student" style="min-height:100vh;display:flex;align-items:center;justify-content:center;padding:32px;">
      <div style="text-align:center;max-width:400px;">
        <div style="font-size:3rem;margin-bottom:16px;">🔗</div>
        <h2 style="font-family:Sora,sans-serif;color:#162340;margin-bottom:8px;">Invalid Link</h2>
        <p style="color:#6b7280;">{{ error }}</p>
      </div>
    </div>

    <!-- ── LOGIN PAGE ── -->
    <div v-else-if="view === 'login'" style="min-height:100vh;display:grid;grid-template-columns:1fr 1fr;">
      <!-- Left -->
      <div style="background:#162340;display:flex;flex-direction:column;justify-content:space-between;padding:60px 48px;position:relative;overflow:hidden;">
        <div style="position:absolute;inset:0;background:radial-gradient(ellipse at 30% 50%,rgba(184,150,106,.18) 0%,transparent 70%),radial-gradient(ellipse at 80% 20%,rgba(184,150,106,.10) 0%,transparent 60%);"></div>
        <div style="position:relative;z-index:1;">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:48px;">
            <div style="width:44px;height:44px;background:#B8966A;border-radius:12px;display:flex;align-items:center;justify-content:center;font-family:Sora,sans-serif;font-weight:700;color:#162340;font-size:1.1rem;">U</div>
            <div>
              <div style="font-family:Sora,sans-serif;color:white;font-weight:600;">University CRM</div>
              <div style="color:#B8966A;font-size:.72rem;">Student Portal</div>
            </div>
          </div>
          <h1 style="font-family:Sora,sans-serif;color:white;font-size:2rem;font-weight:700;line-height:1.2;margin-bottom:12px;">
            Track your<br/><span style="color:#B8966A;">application.</span>
          </h1>
          <p style="color:rgba(255,255,255,.6);font-size:.9rem;line-height:1.7;max-width:300px;margin-bottom:48px;">Your personal portal to monitor progress and submit documents.</p>
          <div style="display:flex;flex-direction:column;gap:16px;">
            <div v-for="(step, i) in [['Sign In','Use the email your advisor registered'],['Track Progress','See where your application stands'],['Upload Documents','Submit passport, transcript & more']]" :key="i" style="display:flex;align-items:flex-start;gap:14px;">
              <div style="width:36px;height:36px;border-radius:50%;background:rgba(184,150,106,.2);border:1px solid rgba(184,150,106,.4);display:flex;align-items:center;justify-content:center;color:#B8966A;font-size:.85rem;flex-shrink:0;">{{ i+1 }}</div>
              <div>
                <div style="color:white;font-size:.9rem;font-weight:600;">{{ step[0] }}</div>
                <div style="color:rgba(255,255,255,.5);font-size:.8rem;">{{ step[1] }}</div>
              </div>
            </div>
          </div>
        </div>
        <div style="position:relative;z-index:1;border-left:2px solid #B8966A;padding-left:20px;">
          <p style="color:rgba(255,255,255,.7);font-size:.85rem;font-style:italic;line-height:1.6;margin-bottom:6px;">"Education is the most powerful weapon which you can use to change the world."</p>
          <p style="color:#B8966A;font-size:.78rem;font-weight:600;">— Nelson Mandela</p>
        </div>
      </div>

      <!-- Right -->
      <div style="display:flex;align-items:center;justify-content:center;padding:40px 32px;background:#FAFAF8;">
        <div style="width:100%;max-width:420px;">
          <div style="margin-bottom:32px;">
            <h2 style="font-family:Sora,sans-serif;font-size:1.8rem;font-weight:700;color:#162340;margin-bottom:6px;">Welcome back.</h2>
            <p style="color:#6b7280;font-size:.9rem;">Sign in to your student portal</p>
          </div>

          <div v-if="error" style="padding:12px 16px;background:#fef2f2;border:1px solid #fecaca;border-radius:8px;color:#dc2626;font-size:.88rem;margin-bottom:18px;">⚠ {{ error }}</div>

          <div style="margin-bottom:18px;">
            <label style="display:block;font-size:.82rem;font-weight:600;color:#162340;margin-bottom:6px;text-transform:uppercase;letter-spacing:.04em;">Email Address</label>
            <input v-model="email" type="email" placeholder="your@email.com"
              style="width:100%;padding:12px 16px;border:1.5px solid #e5e0d8;border-radius:10px;font-size:.95rem;color:#1a1a2e;background:white;outline:none;box-sizing:border-box;"
              @keyup.enter="handleLogin"/>
          </div>

          <div style="margin-bottom:24px;">
            <label style="display:block;font-size:.82rem;font-weight:600;color:#162340;margin-bottom:6px;text-transform:uppercase;letter-spacing:.04em;">Password</label>
            <div style="position:relative;">
              <input v-model="password" :type="showPassword ? 'text' : 'password'" placeholder="Your password"
                style="width:100%;padding:12px 48px 12px 16px;border:1.5px solid #e5e0d8;border-radius:10px;font-size:.95rem;color:#1a1a2e;background:white;outline:none;box-sizing:border-box;"
                @keyup.enter="handleLogin"/>
              <button @click="showPassword = !showPassword" type="button"
                style="position:absolute;right:12px;top:50%;transform:translateY(-50%);background:none;border:none;cursor:pointer;color:#6b7280;font-size:.85rem;">
                {{ showPassword ? '🙈' : '👁' }}
              </button>
            </div>
          </div>

          <button @click="handleLogin" :disabled="loading"
            style="width:100%;padding:13px;background:#162340;color:white;border:none;border-radius:10px;font-family:Sora,sans-serif;font-size:.95rem;font-weight:600;cursor:pointer;">
            {{ loading ? 'Signing in...' : 'Sign In →' }}
          </button>

          <p style="text-align:center;margin-top:20px;font-size:.82rem;color:#6b7280;">
            First time? Use the link your advisor sent you to set up your password.
          </p>
          <p style="text-align:center;margin-top:8px;font-size:.82rem;">
            <a href="#" @click.prevent="view = 'set-password'" style="color:#B8966A;font-weight:600;">Set up password for first time →</a>
          </p>

          <p style="text-align:center;margin-top:24px;font-size:.78rem;color:#9ca3af;">University CRM · Powered by Odoo · v2.4</p>
        </div>
      </div>
    </div>

    <!-- ── SET PASSWORD PAGE ── -->
    <div v-else-if="view === 'set-password'" style="min-height:100vh;display:grid;grid-template-columns:1fr 1fr;">
      <!-- Left (same as login) -->
      <div style="background:#162340;display:flex;flex-direction:column;justify-content:center;padding:60px 48px;position:relative;overflow:hidden;">
        <div style="position:absolute;inset:0;background:radial-gradient(ellipse at 30% 50%,rgba(184,150,106,.18) 0%,transparent 70%);"></div>
        <div style="position:relative;z-index:1;text-align:center;">
          <div style="width:64px;height:64px;background:#B8966A;border-radius:16px;display:flex;align-items:center;justify-content:center;font-family:Sora,sans-serif;font-weight:700;color:#162340;font-size:1.5rem;margin:0 auto 24px;">U</div>
          <h1 style="font-family:Sora,sans-serif;color:white;font-size:1.8rem;font-weight:700;margin-bottom:12px;">Create your password</h1>
          <p style="color:rgba(255,255,255,.6);font-size:.9rem;line-height:1.7;max-width:280px;margin:0 auto;">Set a secure password to access your application portal.</p>
        </div>
      </div>

      <!-- Right -->
      <div style="display:flex;align-items:center;justify-content:center;padding:40px 32px;background:#FAFAF8;">
        <div style="width:100%;max-width:420px;">
          <div style="margin-bottom:32px;">
            <h2 style="font-family:Sora,sans-serif;font-size:1.8rem;font-weight:700;color:#162340;margin-bottom:6px;">Set Your Password</h2>
            <p style="color:#6b7280;font-size:.9rem;">Welcome! Create a password to access your portal.</p>
          </div>

          <div v-if="student" style="background:#f8f7f4;border-radius:10px;padding:12px 16px;margin-bottom:24px;font-size:.88rem;">
            <span style="color:#6b7280;">Account: </span>
            <strong style="color:#162340;">{{ student.name }} ({{ student.email }})</strong>
          </div>

          <div v-if="error" style="padding:12px 16px;background:#fef2f2;border:1px solid #fecaca;border-radius:8px;color:#dc2626;font-size:.88rem;margin-bottom:18px;">⚠ {{ error }}</div>

          <div style="margin-bottom:18px;">
            <label style="display:block;font-size:.82rem;font-weight:600;color:#162340;margin-bottom:6px;text-transform:uppercase;letter-spacing:.04em;">New Password</label>
            <div style="position:relative;">
              <input v-model="password" :type="showPassword ? 'text' : 'password'" placeholder="At least 6 characters"
                style="width:100%;padding:12px 48px 12px 16px;border:1.5px solid #e5e0d8;border-radius:10px;font-size:.95rem;color:#1a1a2e;background:white;outline:none;box-sizing:border-box;"/>
              <button @click="showPassword = !showPassword" type="button"
                style="position:absolute;right:12px;top:50%;transform:translateY(-50%);background:none;border:none;cursor:pointer;color:#6b7280;">
                {{ showPassword ? '🙈' : '👁' }}
              </button>
            </div>
          </div>

          <div style="margin-bottom:24px;">
            <label style="display:block;font-size:.82rem;font-weight:600;color:#162340;margin-bottom:6px;text-transform:uppercase;letter-spacing:.04em;">Confirm Password</label>
            <div style="position:relative;">
              <input v-model="password2" :type="showPassword2 ? 'text' : 'password'" placeholder="Repeat password"
                style="width:100%;padding:12px 48px 12px 16px;border:1.5px solid #e5e0d8;border-radius:10px;font-size:.95rem;color:#1a1a2e;background:white;outline:none;box-sizing:border-box;"/>
              <button @click="showPassword2 = !showPassword2" type="button"
                style="position:absolute;right:12px;top:50%;transform:translateY(-50%);background:none;border:none;cursor:pointer;color:#6b7280;">
                {{ showPassword2 ? '🙈' : '👁' }}
              </button>
            </div>
          </div>

          <button @click="handleSetPassword" :disabled="loading"
            style="width:100%;padding:13px;background:#162340;color:white;border:none;border-radius:10px;font-family:Sora,sans-serif;font-size:.95rem;font-weight:600;cursor:pointer;">
            {{ loading ? 'Setting password...' : 'Create Password & Enter Portal →' }}
          </button>

          <p style="text-align:center;margin-top:16px;font-size:.82rem;">
            <a href="#" @click.prevent="view = 'login'" style="color:#B8966A;font-weight:600;">Already have a password? Sign in</a>
          </p>
        </div>
      </div>
    </div>

    <!-- ── DASHBOARD ── -->
    <div v-else-if="view === 'dashboard'">

      <!-- Navbar -->
      <nav style="background:#162340;height:62px;display:flex;align-items:center;justify-content:space-between;padding:0 32px;position:sticky;top:0;z-index:100;box-shadow:0 2px 16px rgba(0,0,0,.25);">
        <div style="display:flex;align-items:center;gap:12px;">
          <div style="width:36px;height:36px;background:#B8966A;border-radius:8px;display:flex;align-items:center;justify-content:center;font-family:Sora,sans-serif;font-weight:700;font-size:.9rem;color:#162340;">U</div>
          <div>
            <div style="font-family:Sora,sans-serif;color:white;font-weight:600;font-size:1rem;">University CRM</div>
            <div style="color:rgba(255,255,255,.4);font-size:.72rem;">Student Portal</div>
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:14px;">
          <span style="color:rgba(255,255,255,.75);font-size:.85rem;">{{ student?.name }}</span>
          <button @click="handleLogout"
            style="padding:6px 16px;border:1px solid rgba(255,255,255,.2);border-radius:6px;color:rgba(255,255,255,.65);font-size:.8rem;cursor:pointer;background:none;">
            Sign Out
          </button>
        </div>
      </nav>

      <div style="max-width:1060px;margin:0 auto;padding:32px 24px;">

        <!-- Progress -->
        <div style="background:white;border-radius:16px;padding:28px 32px;margin-bottom:24px;box-shadow:0 4px 24px rgba(22,35,64,.08);">
          <div style="font-size:.75rem;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:.08em;margin-bottom:20px;">Application Progress</div>
          <div style="display:flex;align-items:center;">
            <div v-for="(step, i) in STATUS_STEPS" :key="step.key" style="flex:1;display:flex;flex-direction:column;align-items:center;position:relative;">
              <!-- connector line -->
              <div v-if="i < STATUS_STEPS.length - 1"
                :style="{position:'absolute',top:'16px',left:'50%',right:'-50%',height:'2px',background: stepState(step.key)==='done' || stepState(step.key)==='current' ? '#B8966A' : '#e5e0d8',zIndex:0}">
              </div>
              <div :style="{
                width:'32px',height:'32px',borderRadius:'50%',
                background: stepState(step.key)==='current' ? '#162340' : stepState(step.key)==='done' ? '#B8966A' : '#e5e0d8',
                border: '2px solid ' + (stepState(step.key)==='current' ? '#162340' : stepState(step.key)==='done' ? '#B8966A' : '#e5e0d8'),
                display:'flex',alignItems:'center',justifyContent:'center',
                fontSize:'.75rem',fontWeight:'700',
                color: stepState(step.key)==='current' ? 'white' : stepState(step.key)==='done' ? '#162340' : '#6b7280',
                zIndex:1,position:'relative',
                boxShadow: stepState(step.key)==='current' ? '0 0 0 4px rgba(22,35,64,.12)' : 'none'
              }">
                {{ stepState(step.key) === 'done' ? '✓' : (i + 1) }}
              </div>
              <div :style="{marginTop:'8px',fontSize:'.68rem',fontWeight:'600',color: stepState(step.key) ? '#162340' : '#6b7280',textAlign:'center',textTransform:'uppercase',letterSpacing:'.03em',maxWidth:'70px'}">
                {{ step.label }}
              </div>
            </div>
          </div>
        </div>

        <!-- Info Cards -->
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:20px;margin-bottom:24px;">

          <!-- Contact -->
          <div style="background:white;border-radius:16px;padding:22px;box-shadow:0 4px 24px rgba(22,35,64,.08);">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid #e5e0d8;">
              <div style="width:34px;height:34px;border-radius:9px;background:rgba(184,150,106,.1);display:flex;align-items:center;justify-content:center;font-size:.9rem;">👤</div>
              <div style="font-family:Sora,sans-serif;font-size:.88rem;font-weight:600;color:#162340;">Contact Information</div>
            </div>
            <div v-for="[l,v] in [['Name',student?.name],['Email',student?.email],['Phone',student?.phone_full],['Nationality',student?.country_id?.[1]]]" :key="l"
              style="display:flex;justify-content:space-between;align-items:baseline;padding:6px 0;font-size:.85rem;border-bottom:1px solid #f5f3f0;">
              <span style="color:#6b7280;font-size:.8rem;">{{ l }}</span>
              <span style="font-weight:500;color:#162340;text-align:right;max-width:60%;">{{ v || '—' }}</span>
            </div>
          </div>

          <!-- Academic -->
          <div style="background:white;border-radius:16px;padding:22px;box-shadow:0 4px 24px rgba(22,35,64,.08);">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid #e5e0d8;">
              <div style="width:34px;height:34px;border-radius:9px;background:rgba(184,150,106,.1);display:flex;align-items:center;justify-content:center;font-size:.9rem;">🎓</div>
              <div style="font-family:Sora,sans-serif;font-size:.88rem;font-weight:600;color:#162340;">Academic Information</div>
            </div>
            <div v-for="[l,v] in [['Degree',student?.degree_level],['Specialization',student?.specialization_display],['Status',student?.status],['Follow-up',student?.follow_up_date]]" :key="l"
              style="display:flex;justify-content:space-between;align-items:baseline;padding:6px 0;font-size:.85rem;border-bottom:1px solid #f5f3f0;">
              <span style="color:#6b7280;font-size:.8rem;">{{ l }}</span>
              <span style="font-weight:500;color:#162340;text-align:right;max-width:60%;">{{ v || '—' }}</span>
            </div>
          </div>

          <!-- Budget -->
          <div style="background:white;border-radius:16px;padding:22px;box-shadow:0 4px 24px rgba(22,35,64,.08);">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid #e5e0d8;">
              <div style="width:34px;height:34px;border-radius:9px;background:rgba(184,150,106,.1);display:flex;align-items:center;justify-content:center;font-size:.9rem;">💰</div>
              <div style="font-family:Sora,sans-serif;font-size:.88rem;font-weight:600;color:#162340;">Budget & Timeline</div>
            </div>
            <div v-for="[l,v] in [['Budget',student?.budget_display],['Currency',student?.currency_id?.[1]],['Date Added',student?.date_contacted],['Advisor',student?.user_id?.[1]]]" :key="l"
              style="display:flex;justify-content:space-between;align-items:baseline;padding:6px 0;font-size:.85rem;border-bottom:1px solid #f5f3f0;">
              <span style="color:#6b7280;font-size:.8rem;">{{ l }}</span>
              <span style="font-weight:500;color:#162340;text-align:right;max-width:60%;">{{ v || '—' }}</span>
            </div>
          </div>
        </div>

        <!-- Documents -->
        <div style="background:white;border-radius:16px;padding:22px;box-shadow:0 4px 24px rgba(22,35,64,.08);">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;padding-bottom:12px;border-bottom:1px solid #e5e0d8;">
            <div style="display:flex;align-items:center;gap:8px;font-family:Sora,sans-serif;font-size:.95rem;font-weight:600;color:#162340;">
              📎 Documents
              <span style="background:#162340;color:white;border-radius:20px;padding:2px 9px;font-size:.72rem;font-weight:600;">{{ attachments.length }}</span>
            </div>
          </div>

          <!-- Upload zone -->
          <label style="display:block;border:2px dashed #e5e0d8;border-radius:12px;padding:24px;text-align:center;cursor:pointer;margin-bottom:16px;transition:border-color .2s;">
            <input type="file" multiple style="display:none;" @change="onFileChange"/>
            <div style="font-size:2rem;margin-bottom:8px;">☁</div>
            <div style="font-size:.88rem;color:#6b7280;"><strong style="color:#162340;">Click to choose files</strong><br/>or drag and drop here</div>
            <div v-if="selectedFiles.length" style="margin-top:8px;color:#B8966A;font-size:.82rem;font-weight:500;">
              {{ selectedFiles.map(f => f.name).join(', ') }}
            </div>
            <div v-else style="margin-top:6px;color:#9ca3af;font-size:.78rem;">No files selected</div>
          </label>

          <button @click="handleUpload" :disabled="!selectedFiles.length || uploading"
            style="width:100%;padding:11px;background:#162340;color:white;border:none;border-radius:8px;font-family:'Plus Jakarta Sans',sans-serif;font-size:.88rem;font-weight:600;cursor:pointer;margin-bottom:20px;opacity:1;"
            :style="{opacity: !selectedFiles.length ? '0.5' : '1'}">
            {{ uploading ? 'Uploading...' : uploadSuccess ? '✓ Uploaded!' : '↑ Upload Files' }}
          </button>

          <!-- File list -->
          <div v-if="attachments.length === 0" style="text-align:center;padding:28px;color:#6b7280;font-size:.88rem;">
            No documents uploaded yet.
          </div>
          <div v-else style="display:flex;flex-direction:column;gap:10px;">
            <div v-for="att in attachments" :key="att.id"
              style="display:flex;justify-content:space-between;align-items:center;padding:12px 14px;background:#fafaf9;border-radius:10px;border:1px solid #e5e0d8;">
              <div style="display:flex;align-items:center;gap:12px;">
                <div style="width:36px;height:36px;border-radius:8px;background:rgba(22,35,64,.05);display:flex;align-items:center;justify-content:center;font-size:1rem;">📄</div>
                <div>
                  <div style="font-weight:500;font-size:.86rem;color:#162340;">{{ att.name }}</div>
                  <div style="font-size:.73rem;color:#6b7280;margin-top:2px;">{{ formatSize(att.file_size) }} · {{ formatDate(att.create_date) }}</div>
                </div>
              </div>
              <a :href="downloadUrl(att.id)" target="_blank"
                style="padding:5px 14px;background:#162340;color:white;border-radius:6px;font-size:.78rem;font-weight:500;text-decoration:none;">
                ↓ Download
              </a>
            </div>
          </div>
        </div>

      </div>
    </div>

  </div>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;500;600&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
@keyframes spin { to { transform: rotate(360deg); } }
input:focus { border-color: #B8966A !important; box-shadow: 0 0 0 3px rgba(184,150,106,.12) !important; }
button:hover { opacity: 0.9; }
</style>