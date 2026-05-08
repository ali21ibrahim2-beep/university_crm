// stores/students.ts — Students, archives, users, countries.
// The single source of truth for data shown on every dashboard.
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { callKw, odoo } from '../services/odoo'
import type {
  OdooArchivedStudent,
  OdooCountry,
  OdooStatus,
  OdooStudent,
  OdooUser,
  OdooUserRole,
} from '../types/odoo'
import { STUDENT_DETAIL_FIELDS, STUDENT_LIST_FIELDS } from '../types/odoo'

type GroupMap = {
  employeeId: number | null
  managerId: number | null
}

export const useStudentsStore = defineStore('students', () => {
  // ── STATE ──────────────────────────────────────────────────
  const students = ref<OdooStudent[]>([])
  const archivedStudents = ref<OdooArchivedStudent[]>([])
  const users = ref<OdooUser[]>([])
  const countries = ref<OdooCountry[]>([])
  // Phone format rules keyed by country_id — used for live validation
  // in the edit + create forms. Mirrors phone.country.format on the backend.
  const phoneFormats = ref<Record<number, { digit_count: number; leading_digit: string }>>({})
  const currentStudent = ref<OdooStudent | null>(null)
  const attachments = ref<any[]>([])
  const loading = ref(false)
  const error = ref('')
  const groupMap = ref<GroupMap>({ employeeId: null, managerId: null })

  // ── DERIVED COUNTS ─────────────────────────────────────────
  // Used by StatCard KPIs on the dashboards.
  const activeStudents = computed(() => students.value)
  const enrolledCount = computed(() => students.value.filter((s) => s.status === 'enrolled').length)
  const newCount = computed(() => students.value.filter((s) => s.status === 'new').length)
  const docsCount = computed(() => students.value.filter((s) => s.status === 'docs').length)
  const employees = computed(() => users.value.filter((user) => user.role === 'employee'))
  const managers = computed(() => users.value.filter((user) => user.role === 'manager'))

  // ── LOADING WRAPPER ────────────────────────────────────────
  // Toggles loading + captures errors so pages don't repeat try/catch.
  async function withLoading<T>(action: () => Promise<T>) {
    loading.value = true
    error.value = ''
    try {
      return await action()
    } catch (e: any) {
      error.value = e.message || 'Unexpected error'
      throw e
    } finally {
      loading.value = false
    }
  }

  // ── STUDENT FETCHERS ───────────────────────────────────────
  // fetchStudents: all (admin/manager). fetchMyStudents: assigned-to-me.
  async function fetchStudents() {
    return withLoading(async () => {
      students.value = await odoo.search('student.lead', [], STUDENT_LIST_FIELDS, 500, 'date_contacted desc')
    })
  }

  async function fetchMyStudents(userId: number) {
    return withLoading(async () => {
      students.value = await odoo.search(
        'student.lead',
        [['user_id', '=', userId]],
        STUDENT_LIST_FIELDS,
        500,
        'date_contacted desc'
      )
    })
  }

  // Loads one record + its attachments (StudentDetail page).
  async function fetchStudent(id: number) {
    return withLoading(async () => {
      currentStudent.value = null
      attachments.value = []

      const results = await odoo.read('student.lead', [id], STUDENT_DETAIL_FIELDS)
      currentStudent.value = results[0] || null

      if (currentStudent.value) {
        attachments.value = await odoo.search(
          'ir.attachment',
          [['res_model', '=', 'student.lead'], ['res_id', '=', id]],
          ['id', 'name', 'mimetype', 'file_size', 'create_date'],
          100
        )
      }
    })
  }

  // Soft-deleted students from the archive model.
  async function fetchArchived() {
    return withLoading(async () => {
      archivedStudents.value = await odoo.search(
        'student.archive',
        [],
        [
          'id',
          'name',
          'email',
          'phone_full',
          'specialization_display',
          'degree_level',
          'status',
          'deleted_date',
          'delete_reason',
          'deleted_by',
          'user_id',
        ],
        500,
        'deleted_date desc'
      )
    })
  }

  // ── REFERENCE DATA ─────────────────────────────────────────
  // Countries list (cached). Used by nationality + phone-code pickers.
  async function fetchCountries() {
    if (countries.value.length > 0) return countries.value

    const result = await odoo.search('res.country', [], ['id', 'name', 'code'], 400, 'name asc')
    countries.value = result
    return countries.value
  }

  // Phone format rules (cached). Keyed by country_id so the forms can
  // tell the user the required length / leading digit before they submit.
  async function fetchPhoneFormats() {
    if (Object.keys(phoneFormats.value).length > 0) return phoneFormats.value
    const rows = await odoo.search(
      'phone.country.format',
      [],
      ['country_id', 'digit_count', 'leading_digit'],
      1000,
      ''
    )
    const map: Record<number, { digit_count: number; leading_digit: string }> = {}
    for (const r of rows) {
      const cid = Array.isArray(r.country_id) ? r.country_id[0] : r.country_id
      if (!cid) continue
      map[cid] = {
        digit_count: Number(r.digit_count) || 0,
        leading_digit: (r.leading_digit || '').toString(),
      }
    }
    phoneFormats.value = map
    return phoneFormats.value
  }

  // ── USERS + ROLES ──────────────────────────────────────────
  // Caches the res.groups ids for Employee/Manager so we can toggle
  // roles without re-querying on every change.
  async function ensureGroupMap() {
    if (groupMap.value.employeeId && groupMap.value.managerId) return groupMap.value

    const groups = await odoo.search(
      'res.groups',
      [['category_id.name', '=', 'University CRM'], ['name', 'in', ['Employee', 'Manager']]],
      ['id', 'name'],
      10
    )

    groupMap.value = {
      employeeId: groups.find((group: { id: number; name: string }) => group.name === 'Employee')?.id || null,
      managerId: groups.find((group: { id: number; name: string }) => group.name === 'Manager')?.id || null,
    }

    return groupMap.value
  }

  // Manager if in Manager group, otherwise employee.
  function resolveRole(user: OdooUser, groups: GroupMap): OdooUserRole {
    const ids = Array.isArray(user.groups_id) ? user.groups_id : []
    if (groups.managerId && ids.includes(groups.managerId)) return 'manager'
    return 'employee'
  }

  // Loads internal users + per-user student counts for Team views.
  async function fetchUsers() {
    const groups = await ensureGroupMap()
    const rawUsers = await odoo.search(
      'res.users',
      [['share', '=', false], ['groups_id.name', 'in', ['Employee', 'Manager']]],
      ['id', 'name', 'login', 'email', 'groups_id'],
      100,
      'name asc'
    )

    users.value = await Promise.all(rawUsers.map(async (user: OdooUser) => {
      const total = await odoo.count('student.lead', [['user_id', '=', user.id]])
      const enrolled = await odoo.count('student.lead', [['user_id', '=', user.id], ['status', '=', 'enrolled']])
      return {
        ...user,
        role: resolveRole(user, groups),
        studentsTotal: total,
        studentsEnrolled: enrolled,
      }
    }))

    return users.value
  }

  // ── MUTATIONS ──────────────────────────────────────────────
  // Patches status both on the server and in local cache for snappy UI.
  async function updateStatus(id: number, status: OdooStatus) {
    await odoo.write('student.lead', [id], { status })

    const record = students.value.find((student) => student.id === id)
    if (record) record.status = status
    if (currentStudent.value?.id === id) currentStudent.value.status = status
  }

  // Called from CreateStudentModal.
  async function createStudent(values: Record<string, unknown>) {
    const id = await odoo.create('student.lead', values)
    return id
  }

  // Inline-edit save on StudentDetail; refreshes the view afterwards.
  async function updateStudent(id: number, values: Record<string, unknown>) {
    await odoo.write('student.lead', [id], values)
    await fetchStudent(id)
  }

  // Creates a res.users record with the chosen University CRM role.
  async function createEmployee(values: {
    name: string
    login: string
    email?: string
    password?: string
    phone?: string
    role: OdooUserRole
  }) {
    const groups = await ensureGroupMap()
    if (!groups.employeeId || !groups.managerId) {
      throw new Error('University CRM groups are not configured correctly.')
    }

    const groupId = values.role === 'manager' ? groups.managerId : groups.employeeId
    // Resolve the base "Internal User" group so the new user is internal
    // (share=false). Without this, replacing groups_id would create a
    // portal/share user that the Staff Overview filter ignores.
    // ir.model.data._xmlid_to_res_id is private over RPC, so we look the
    // mapping up via a normal search instead.
    const dataRows = await odoo.search(
      'ir.model.data',
      [['module', '=', 'base'], ['name', '=', 'group_user']],
      ['res_id'],
      1
    )
    const internalUserGroupId = dataRows[0]?.res_id
    if (!internalUserGroupId) {
      throw new Error('Could not resolve base.group_user — Internal User group missing.')
    }
    const payload: Record<string, unknown> = {
      name: values.name,
      login: values.login,
      groups_id: [[6, 0, [internalUserGroupId, groupId]]],
    }
    if (values.email) payload.email = values.email
    if (values.password) payload.password = values.password
    if (values.phone) payload.phone = values.phone

    const id = await odoo.create('res.users', payload)
    await fetchUsers()
    return id
  }

  // Swaps a user between Employee and Manager via Odoo groups_id commands.
  async function updateUserRole(userId: number, role: OdooUserRole) {
    const groups = await ensureGroupMap()
    if (!groups.employeeId || !groups.managerId) {
      throw new Error('University CRM groups are not configured correctly.')
    }

    const commands = [
      [3, groups.employeeId],
      [3, groups.managerId],
      [4, role === 'manager' ? groups.managerId : groups.employeeId],
    ]

    await odoo.write('res.users', [userId], { groups_id: commands })
    await fetchUsers()
  }

  // Un-archives a record; refreshes both active + archive lists.
  async function restoreArchived(id: number) {
    return withLoading(async () => {
      await callKw('student.archive', 'action_restore', [[id]])
      // Refresh both lists to show the restored student in active list
      await Promise.all([fetchArchived(), fetchStudents()])
    })
  }

  // Permanently removes an archived record (admin/manager only).
  async function deleteArchived(id: number) {
    return withLoading(async () => {
      await odoo.unlink('student.archive', [id])
      await fetchArchived()
    })
  }

  return {
    attachments,
    archivedStudents,
    countries,
    phoneFormats,
    currentStudent,
    docsCount,
    employees,
    enrolledCount,
    error,
    loading,
    managers,
    newCount,
    students,
    users,
    activeStudents,
    createEmployee,
    createStudent,
    deleteArchived,
    fetchArchived,
    fetchCountries,
    fetchPhoneFormats,
    fetchMyStudents,
    fetchStudent,
    fetchStudents,
    fetchUsers,
    restoreArchived,
    updateStatus,
    updateStudent,
    updateUserRole,
  }
})
