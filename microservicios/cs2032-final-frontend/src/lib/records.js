import { computed, onScopeDispose, reactive, ref, watch } from 'vue'
import { api, session } from './api.js'

const sets = {
  candidatos: { service: 'candidatos', one: 'candidato', id: 'candidato_id', cursor: 'ultimo_id' },
  vacantes: { service: 'vacantes', one: 'vacante', id: 'vacante_id', cursor: 'cursor' },
  entrevistas: { service: 'entrevistas', one: 'entrevista', id: 'entrevista_id', cursor: 'cursor' },
  postulaciones: { service: 'vacantes', one: 'postulacion', id: 'postulacion_id', cursor: 'cursor' },
}
export const stages = ['postulado', 'preseleccionado', 'entrevista', 'oferta', 'contratado', 'rechazado']
const labels = {
  hibrido: 'Híbrido', preseleccionado: 'Preselección', postulado: 'Postulado',
  oferta: 'Oferta', contratado: 'Contratado', rechazado: 'Rechazado', entrevista: 'Entrevista',
}
export const label = value => value ? labels[value] || value[0].toUpperCase() + value.slice(1) : 'Sin dato'
export const number = n => Number(n ?? 0).toLocaleString('es-PE')
export const money = n => n == null ? 'Sin indicar' : 'S/ ' + number(n)
export function date(value) {
  if (!value) return 'Sin fecha'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('es-PE', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Lima' })
}
export function limaInput(value) {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return ''
  return new Date(d.getTime() - 5 * 3600000).toISOString().slice(0, 16)
}

export function stored(key, fallback) {
  try { return JSON.parse(sessionStorage.getItem(key)) ?? fallback } catch { return fallback }
}
function recentIds(name) {
  const ids = stored('recientes_' + name, [])
  return Array.isArray(ids) ? ids : []
}
export function markRecent(name, id, remove = false) {
  if (!id) return
  const rest = recentIds(name).filter(value => value !== id)
  sessionStorage.setItem('recientes_' + name, JSON.stringify(remove ? rest : [id, ...rest].slice(0, 10)))
}
export const itemPath = (name, id) => '/' + name + '/' + encodeURIComponent(id)
export async function getItem(name, id) {
  const { service, one } = sets[name]
  return (await api(service, 'GET', itemPath(name, id)))[one]
}
export async function page(name, filters = {}, cursor = '') {
  const spec = sets[name]
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) if (value) params.set(key, value)
  if (cursor) params.set(spec.cursor, cursor)
  const query = params.toString()
  const result = await api(spec.service, 'GET', '/' + name + (query ? '?' + query : ''))
  if (!Array.isArray(result[name])) throw new Error('El servicio devolvió una lista incompleta.')
  return { items: result[name], cursor: result[spec.cursor] || '' }
}
export async function recentItems(name) {
  const tenant = session.value?.tenant_id
  const ids = recentIds(name)
  const results = await Promise.allSettled(ids.map(id => getItem(name, id)))
  if (tenant !== session.value?.tenant_id) return []
  return results.flatMap((r, i) => {
    if (r.status === 'fulfilled' && r.value) return [r.value]
    if (r.reason?.status === 404) markRecent(name, ids[i], true)
    return []
  })
}
function distinct(items, id) {
  const map = new Map()
  for (const item of items) if (item && !map.has(item[id])) map.set(item[id], item)
  return [...map.values()]
}
export async function firstPage(name, filters = {}) {
  const [recent, first] = await Promise.all([recentItems(name), page(name, filters)])
  const matches = item => Object.entries(filters).every(([key, value]) => !value || item[key] === value)
  return { items: distinct([...recent.filter(matches), ...first.items], sets[name].id), cursor: first.cursor }
}
export function useList(name, filters = () => ({})) {
  const rows = ref([])
  const cursor = ref('')
  const loading = ref(false)
  const moreBusy = ref(false)
  const error = ref('')
  let revision = 0
  let disposed = false
  async function read(append) {
    if (disposed || (append && (moreBusy.value || loading.value || !cursor.value))) return
    const mine = append ? revision : ++revision
    if (append) moreBusy.value = true
    else {
      loading.value = true
      moreBusy.value = false
      rows.value = []
      cursor.value = ''
    }
    error.value = ''
    try {
      const result = append ? await page(name, filters(), cursor.value) : await firstPage(name, filters())
      if (mine !== revision) return
      rows.value = distinct([...(append ? rows.value : []), ...result.items], sets[name].id)
      cursor.value = result.cursor
    } catch (e) {
      if (mine === revision) error.value = e.message
    } finally {
      if (mine === revision) { loading.value = false; moreBusy.value = false }
    }
  }
  watch(() => JSON.stringify(filters()), () => read(false), { immediate: true })
  onScopeDispose(() => { disposed = true; revision++ })
  return reactive({ rows, cursor, loading, moreBusy, error, more: () => read(true), reload: () => read(false) })
}
export function useFilter(name) {
  const value = ref(sessionStorage.getItem('filtro_' + name) || '')
  return computed({
    get: () => value.value,
    set: next => { value.value = next; sessionStorage.setItem('filtro_' + name, next) },
  })
}
