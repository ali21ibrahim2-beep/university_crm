// services/odoo.ts — JSON-RPC bridge to Odoo. Auth, generic ORM
// (callKw), CRUD helpers, attachments. Session is cookie-based.

// ── ODOO CONFIG ─────────────────────────────────────────────
// Empty ODOO_URL = same origin (works in dev via Vite proxy and
// in prod when Odoo serves the bundle).
export const ODOO_URL = ''
export const ODOO_DB = 'ali_dev'

// ── RAW JSON-RPC CALL ────────────────────────────────────────
// Every helper below funnels through here. Surfaces Odoo's Python
// exception message via error.data.message when present.
export async function jsonrpcCall(endpoint: string, params: object) {
  const res = await fetch(`${ODOO_URL}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include', // sends session cookie automatically
    body: JSON.stringify({ jsonrpc: '2.0', method: 'call', id: 1, params }),
  })
  
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${res.statusText}`)
  }
  
  const text = await res.text()
  if (!text) {
    throw new Error('Empty response from server')
  }
  
  let data
  try {
    data = JSON.parse(text)
  } catch (e) {
    throw new Error(`Invalid JSON response: ${text.substring(0, 100)}`)
  }
  
  if (data.error) throw new Error(data.error.data?.message || data.error.message)
  return data.result
}

// Alias for backwards compatibility.
async function jsonrpc(endpoint: string, params: object) {
  return jsonrpcCall(endpoint, params)
}

// ── AUTH ─────────────────────────────────────────────────────
// Thin wrappers over /web/session/*. Used by stores/auth.ts.
export async function odooLogin(login: string, password: string) {
  return jsonrpc('/web/session/authenticate', { db: ODOO_DB, login, password })
}

export async function odooLogout() {
  return jsonrpc('/web/session/destroy', {})
}

export async function getSessionInfo() {
  return jsonrpc('/web/session/get_session_info', {})
}

// ── GENERIC MODEL CALL ───────────────────────────────────────
// Odoo's ORM endpoint. `args` = positional, `kwargs` = keyword args
// passed to the Python method (has_group, action_restore, etc.).
export async function callKw(model: string, method: string, args: any[] = [], kwargs: object = {}) {
  return jsonrpc('/web/dataset/call_kw', { model, method, args, kwargs })
}

// ── HELPERS ──────────────────────────────────────────────────
// Ergonomic facade over callKw for the standard CRUD operations.
export const odoo = {
  search: (model: string, domain: any[] = [], fields: string[] = [], limit = 200, order = '') =>
    callKw(model, 'search_read', [domain], { fields, limit, order }),

  read: (model: string, ids: number[], fields: string[] = []) =>
    callKw(model, 'read', [ids], { fields }),

  create: (model: string, values: object) =>
    callKw(model, 'create', [values]),

  write: (model: string, ids: number[], values: object) =>
    callKw(model, 'write', [ids, values]),

  unlink: (model: string, ids: number[]) =>
    callKw(model, 'unlink', [ids]),

  count: (model: string, domain: any[] = []) =>
    callKw(model, 'search_count', [domain]),
}

// ── ATTACHMENT UPLOAD ────────────────────────────────────────
// Creates an ir.attachment linked to resModel:resId. Uses callKw
// (CSRF-exempt) rather than /web/binary/upload, which needs a token.
export async function uploadAttachment(file: File, resModel: string, resId: number) {
  // Convert file to base64
  const base64 = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve((reader.result as string).split(',')[1])
    reader.onerror = () => reject(new Error('Failed to read file'))
    reader.readAsDataURL(file)
  })

  // Use JSON-RPC create — CSRF exempt, works from Vue
  const attachmentId = await callKw('ir.attachment', 'create', [{
    name: file.name,
    datas: base64,
    res_model: resModel,
    res_id: resId,
    mimetype: file.type || 'application/octet-stream',
  }])

  return attachmentId
}
  
// ── ATTACHMENT DOWNLOAD URL ──────────────────────────────────
// Standard /web/content URL; the session cookie authorises it.
export function attachmentUrl(attachmentId: number) {
  return `${ODOO_URL}/web/content/${attachmentId}?download=true`
}
