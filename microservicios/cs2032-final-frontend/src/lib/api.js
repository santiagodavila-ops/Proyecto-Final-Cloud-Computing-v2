import { computed, ref, shallowRef } from 'vue'

const storage = window.sessionStorage
const keys = ['token_acceso', 'token_refresh', 'tenant_id', 'email', 'rol']
const restored = Object.fromEntries(keys.map(key => [key, storage.getItem(key)]))
export const session = shallowRef(restored.token_acceso && restored.tenant_id ? restored : null)
export const company = computed(() => window.TENANTS?.[session.value?.tenant_id]?.nombre || session.value?.tenant_id || '')
export const activity = shallowRef([])
export const callCount = ref(0)
export const loginNotice = ref('')
let generation = 0
let refreshing = null

function ensureCurrent(expected) {
  if (generation !== expected) throw new Error('La sesión ha cambiado.')
}

function remember(data) {
  for (const key of keys) {
    if (data[key]) storage.setItem(key, data[key])
    else storage.removeItem(key)
  }
  session.value = data
}

export function logout(message = '') {
  generation++
  refreshing = null
  for (const key of Object.keys(storage)) {
    if (keys.includes(key) || key.startsWith('recientes_') || key.startsWith('filtro_') || key === 'pipeline_vacante') {
      storage.removeItem(key)
    }
  }
  session.value = null
  activity.value = []
  callCount.value = 0
  loginNotice.value = message
}

function log(method, service, path, status, start, expected) {
  if (generation !== expected) return
  const entry = { id: ++callCount.value, method, service, path, status, ms: Math.round(performance.now() - start) }
  activity.value = [entry, ...activity.value].slice(0, 80)
}

async function request(service, method, path, body, token, expected) {
  ensureCurrent(expected)
  const base = window.CONFIG?.[service]
  if (!base) throw new Error('Falta configurar la dirección del servicio ' + service + '.')
  const headers = {}
  if (token) headers.Authorization = 'Bearer ' + token
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const start = performance.now()
  let response
  try {
    response = await fetch(base + path, {
      method, headers, body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    log(method, service, path, 0, start, expected)
    throw new Error('No se pudo conectar con el servicio de ' + service + '.')
  }
  log(method, service, path, response.status, start, expected)
  ensureCurrent(expected)
  const data = await response.json().catch(() => ({}))
  ensureCurrent(expected)
  if (!response.ok) {
    const failure = new Error(data.error || data.message || 'La solicitud falló (' + response.status + ').')
    failure.status = response.status
    throw failure
  }
  return data
}

export async function login(email, password) {
  const expected = generation
  loginNotice.value = ''
  let result
  try {
    result = await request('usuarios', 'POST', '/usuarios/login', { email, password }, null, expected)
  } catch (error) {
    if (error.status === 401) throw new Error('El correo o la contraseña son incorrectos.')
    throw error
  }
  ensureCurrent(expected)
  const token = result.token_acceso || result.token
  if (!result.tenant_id || !token) throw new Error('El servicio no devolvió una sesión completa.')
  generation++
  remember({
    token_acceso: token, token_refresh: result.token_refresh || '',
    tenant_id: result.tenant_id, rol: result.rol || 'reclutador', email,
  })
}

function renew(expected) {
  if (refreshing) return refreshing
  refreshing = request('usuarios', 'POST', '/usuarios/refresh',
    { token_refresh: session.value.token_refresh }, null, expected)
    .then(result => {
      ensureCurrent(expected)
      if (!result.token_acceso) throw new Error('No se recibió el nuevo acceso.')
      remember({ ...session.value, token_acceso: result.token_acceso })
    }).finally(() => {
      if (expected === generation) refreshing = null
    })
  return refreshing
}

export async function api(service, method, path, body) {
  const expected = generation
  const firstToken = session.value?.token_acceso
  if (!firstToken) throw new Error('Inicia sesión para continuar.')
  try {
    return await request(service, method, path, body, firstToken, expected)
  } catch (error) {
    if (error.status !== 401) throw error
  }
  ensureCurrent(expected)
  try {
    if (session.value.token_acceso === firstToken) {
      if (!session.value.token_refresh) throw Object.assign(new Error('Sesión vencida.'), { status: 401 })
      await renew(expected)
    }
    return await request(service, method, path, body, session.value.token_acceso, expected)
  } catch (error) {
    if (expected === generation && error.status === 401) logout('Tu sesión venció. Vuelve a ingresar.')
    throw error
  }
}

export async function uploadPdf(url, file) {
  const expected = generation
  const start = performance.now()
  let response
  try {
    response = await fetch(url, { method: 'PUT', headers: { 'Content-Type': 'application/pdf' }, body: file })
  } catch {
    throw new Error('No se pudo enviar el PDF a S3.')
  } finally {
    log('PUT', 'S3', '/cv.pdf', response?.status || 0, start, expected)
  }
  ensureCurrent(expected)
  if (!response.ok) throw new Error('S3 rechazó el archivo (' + response.status + '). Vuelve a intentarlo.')
}
