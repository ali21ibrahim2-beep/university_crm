// types/odoo.ts — TS shapes + display maps for Odoo models used
// here: student.lead, student.archive, res.users, res.country,
// ir.attachment. Update when the Python models add/rename fields.

// ── TYPES MATCHING YOUR REAL ODOO student.lead MODEL ────────
// Status values as they are stored in Odoo. `lost` is terminal.
export type OdooStatus = 'new' | 'options_sent' | 'chosen' | 'docs' | 'enrolled' | 'lost'

// Labels used by StatusBadge, ProgressSteps and status dropdowns.
export const STATUS_LABELS: Record<OdooStatus, string> = {
  new:          'New Inquiry',
  options_sent: 'Options Sent',
  chosen:       'University Chosen',
  docs:         'Collecting Docs',
  enrolled:     'Enrolled',
  lost:         'Lost',
}

// Ordered happy-path for the ProgressSteps ribbon (lost is excluded).
export const STATUS_STEPS: OdooStatus[] = ['new', 'options_sent', 'chosen', 'docs', 'enrolled']

// Tailwind classes per status for pill bg / text / dot.
export const STATUS_COLORS: Record<OdooStatus, { bg: string; text: string; dot: string }> = {
  new:          { bg: 'bg-blue-50',   text: 'text-blue-700',   dot: 'bg-blue-500' },
  options_sent: { bg: 'bg-orange-50', text: 'text-orange-700', dot: 'bg-orange-500' },
  chosen:       { bg: 'bg-purple-50', text: 'text-purple-700', dot: 'bg-purple-500' },
  docs:         { bg: 'bg-yellow-50', text: 'text-yellow-700', dot: 'bg-yellow-500' },
  enrolled:     { bg: 'bg-green-50',  text: 'text-green-700',  dot: 'bg-green-500' },
  lost:         { bg: 'bg-red-50',    text: 'text-red-700',    dot: 'bg-red-500' },
}

// Degree-level picker options. Keys match Odoo selection values.
export const DEGREE_LABELS: Record<string, string> = {
  bachelor: 'Bachelor',
  master:   'Master',
  phd:      'PhD / Doctorate',
  diploma:  '2-Year Diploma',
}

// Specialization dropdown options. Keys match Odoo selection values.
export const SPECIALIZATION_LABELS: Record<string, string> = {
  medicine: 'Medicine',
  dentistry: 'Dentistry',
  pharmacy: 'Pharmacy',
  nursing: 'Nursing',
  veterinary: 'Veterinary Medicine',
  civil_eng: 'Civil Engineering',
  mechanical_eng: 'Mechanical Engineering',
  electrical_eng: 'Electrical Engineering',
  computer_eng: 'Computer Engineering',
  software_eng: 'Software Engineering',
  chemical_eng: 'Chemical Engineering',
  architecture: 'Architecture',
  business_admin: 'Business Administration',
  accounting: 'Accounting & Finance',
  economics: 'Economics',
  marketing: 'Marketing',
  law: 'Law',
  political_science: 'Political Science',
  psychology: 'Psychology',
  sociology: 'Sociology',
  computer_science: 'Computer Science',
  mathematics: 'Mathematics',
  physics: 'Physics',
  chemistry: 'Chemistry',
  biology: 'Biology',
  education: 'Education',
  english_lit: 'English Literature',
  translation: 'Translation',
  other: 'Other',
}

// ── RAW ODOO RECORD (as returned by search_read) ─────────────
// Many2one fields come as [id, display_name] or false when unset.
export interface OdooStudent {
  id: number
  name: string
  email: string | false
  phone: string | false
  phone2: string | false
  phone_full: string | false
  phone_country_id: [number, string] | false   // Many2one: [id, name]
  country_id: [number, string] | false          // Nationality
  user_id: [number, string] | false             // Assigned advisor
  degree_level: string | false
  specialization: string | false
  specialization_other: string | false
  specialization_display: string | false
  status: OdooStatus
  currency_id: [number, string] | false
  budget_amount: number
  budget_min: number
  budget_max: number
  budget_display: string | false
  date_contacted: string | false
  follow_up_date: string | false
  notes: string | false
  portal_token: string | false
  portal_url: string | false
  whatsapp_url: string | false
  attachment_count: number
}

// ── ARCHIVED STUDENT (student.archive model) ──────────────────
// Snapshot kept after a student.lead is soft-deleted.
export interface OdooArchivedStudent {
  id: number
  name: string
  email: string | false
  phone_full: string | false
  specialization_display: string | false
  degree_level: string | false
  status: OdooStatus | false
  deleted_date: string
  delete_reason: string
  deleted_by: [number, string] | false
  user_id: [number, string] | false
}

// App-level role derived from Odoo group membership.
export type OdooUserRole = 'employee' | 'manager'

// ── ODOO USER (res.users / employee) ─────────────────────────
// studentsTotal / studentsEnrolled are computed in stores/students.ts.
export interface OdooUser {
  id: number
  name: string
  login: string
  email: string | false
  groups_id?: number[]
  role?: OdooUserRole
  studentsTotal?: number
  studentsEnrolled?: number
}

export interface OdooCountry {
  id: number
  name: string
  code: string | false
}

// ── ATTACHMENT (ir.attachment) ────────────────────────────────
// Files uploaded through StudentDetail / StudentPortal.
export interface OdooAttachment {
  id: number
  name: string
  mimetype: string
  file_size: number
  create_date: string
  res_model: string
  res_id: number
}

// ── FIELDS TO FETCH for student list ─────────────────────────
// Projection used by StudentTable — keep it lean (fast list pages).
export const STUDENT_LIST_FIELDS = [
  'id', 'name', 'email', 'phone_full', 'country_id', 'user_id',
  'degree_level', 'specialization_display', 'status',
  'budget_display', 'follow_up_date', 'date_contacted',
  'portal_token', 'attachment_count',
]

// ── FIELDS TO FETCH for student detail ───────────────────────
// Full projection used by StudentDetail — includes budget + notes.
export const STUDENT_DETAIL_FIELDS = [
  'id', 'name', 'email', 'phone', 'phone2', 'phone_full',
  'phone_country_id', 'country_id', 'user_id',
  'degree_level', 'specialization', 'specialization_other', 'specialization_display',
  'status', 'currency_id', 'budget_amount', 'budget_min', 'budget_max', 'budget_display',
  'date_contacted', 'follow_up_date', 'notes',
  'portal_token', 'portal_url', 'whatsapp_url', 'attachment_count',
]

// ── HELPER: format Odoo false as empty string ─────────────────
// Odoo returns `false` (not null) for empty text fields.
export function odooVal(val: string | false | null): string {
  return val || ''
}

// ── HELPER: get display name from Many2one ────────────────────
// Pulls the label half of an [id, label] tuple.
export function odooM2o(val: [number, string] | false | null): string {
  if (!val || !Array.isArray(val)) return ''
  return val[1] || ''
}

// Pulls the id half of an [id, label] tuple.
export function odooM2oId(val: [number, string] | false | null): number | null {
  if (!val || !Array.isArray(val)) return null
  return val[0] || null
}
