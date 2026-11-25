import { ref, shallowRef } from 'vue'
import { api } from './api.js'
import { date, getItem, itemPath, label, markRecent, page } from './records.js'

export const panel = shallowRef(null)
export const notice = ref('')
let sequence = 0
let noticeTimer

export function notify(message) {
  clearTimeout(noticeTimer)
  notice.value = message
  noticeTimer = setTimeout(() => { notice.value = '' }, 5500)
}
export function openPanel(spec) { panel.value = { ...spec, key: ++sequence } }
export function closePanel() { panel.value = null }
export async function copyId(value) {
  try {
    await navigator.clipboard.writeText(String(value))
    notify('Identificador copiado.')
  } catch {
    openPanel({ title: 'Identificador completo', details: [['ID', value]] })
  }
}

const fieldsByKey = {
  candidato_id: 'ID del candidato', entrevista_id: 'ID de entrevista', vacante_id: 'ID de vacante',
  postulacion_id: 'ID de postulación', tenant_id: 'Empresa', nombre: 'Nombre', email: 'Correo',
  telefono: 'Teléfono', profesion: 'Profesión', estado: 'Estado', cv_url: 'Archivo del CV',
  fecha_creacion: 'Fecha de creación', fecha_registro: 'Fecha de registro',
  fecha_actualizacion: 'Última actualización', notas: 'Notas', titulo: 'Título',
  fecha_nacimiento: 'Fecha de nacimiento',
}
function candidateDetails(c) {
  return Object.entries(c).map(([key, raw]) => {
    let value = raw
    if (key.startsWith('fecha_') && raw && String(raw).includes('T')) value = date(raw)
    if (key === 'estado') value = label(raw)
    return [fieldsByKey[key] || key.replaceAll('_', ' '), value]
  })
}
export function showCandidate(id) {
  openPanel({
    title: 'Ficha del candidato',
    prepare: async () => ({ details: candidateDetails(await getItem('candidatos', id)) }),
  })
}
export function removeRecord({ name, service, id, title, message, success, reload }) {
  openPanel({
    title, description: message, submitLabel: 'Eliminar', danger: true,
    async submit() {
      await api(service, 'DELETE', itemPath(name, id))
      markRecent(name, id, true)
      notify(success)
      void reload()
    },
  })
}

export const interviewFields = [
  { key: 'entrevistador', label: 'Entrevistador', required: true },
  { key: 'fecha_hora', label: 'Fecha y hora de Lima', type: 'datetime-local', required: true },
  { key: 'modalidad', label: 'Modalidad', type: 'select', options: ['virtual', 'presencial'] },
  { key: 'notas', label: 'Notas', type: 'textarea', allowEmpty: true },
]
export function schedule(application = null, onSaved = () => {}) {
  let choices = []
  const fields = application ? interviewFields : [
    { key: 'postulacion_id', label: 'Postulación en etapa de entrevista', type: 'select', required: true, options: [] },
    ...interviewFields,
  ]
  openPanel({
    title: 'Agendar entrevista', description: application?.titulo_vacante || '',
    fields, submitLabel: 'Agendar entrevista',
    prepare: application ? undefined : async () => {
      const result = await page('postulaciones', { estado: 'entrevista' })
      choices = result.items
      if (!choices.length) return { unavailable: 'Todavía no hay postulaciones en etapa de entrevista.' }
      const options = choices.map(p => [p.postulacion_id, (p.titulo_vacante || 'Vacante') + ' · ' + p.candidato_id])
      return { fields: [{ ...fields[0], options }, ...interviewFields],
        hint: result.cursor ? 'Para agendar otra postulación, ábrela desde Postulaciones.' : '' }
    },
    async submit(data) {
      const p = application || choices.find(item => item.postulacion_id === data.postulacion_id)
      if (!p) throw new Error('Selecciona una postulación.')
      const { entrevista } = await api('entrevistas', 'POST', '/entrevistas', {
        ...data, postulacion_id: p.postulacion_id, candidato_id: p.candidato_id, vacante_id: p.vacante_id,
      })
      markRecent('entrevistas', entrevista.entrevista_id)
      notify('Entrevista agendada.')
      void onSaved()
    },
  })
}
