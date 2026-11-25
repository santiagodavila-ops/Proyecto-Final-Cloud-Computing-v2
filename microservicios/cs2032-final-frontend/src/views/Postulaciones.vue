<script setup>
import { computed, onScopeDispose, reactive, ref, watch } from 'vue'
import RecordList from '../components/RecordList.vue'
import { api } from '../lib/api.js'
import { notify, openPanel, schedule, showCandidate } from '../lib/dialogs.js'
import { date, itemPath, label, markRecent, page, recentItems, stages, stored } from '../lib/records.js'

const filter = ref(stored('pipeline_vacante', null))
const selected = ref('postulado')
const boards = reactive({})
const current = computed(() => boards[selected.value])
let revision = 0

function unite(items) {
  const byId = new Map()
  for (const item of items) if (!byId.has(item.postulacion_id)) byId.set(item.postulacion_id, item)
  return [...byId.values()]
}
function reset() {
  const mine = ++revision
  const recent = recentItems('postulaciones')
  for (const stage of stages) {
    boards[stage] = { rows: [], cursor: '', loading: true, moreBusy: false, error: '',
      more: () => load(stage, true, mine), reload: () => load(stage, false, mine, recent) }
    void load(stage, false, mine, recent)
  }
}
async function load(stage, append, mine, recent = Promise.resolve([])) {
  if (mine !== revision) return
  const board = boards[stage]
  if (append && (board.moreBusy || board.loading || !board.cursor)) return
  if (append) board.moreBusy = true
  else board.loading = true
  board.error = ''
  const id = filter.value?.id || ''
  try {
    const [chunk, pinned] = await Promise.all([
      page('postulaciones', { estado: stage, vacante_id: id }, append ? board.cursor : ''), recent,
    ])
    if (mine !== revision) return
    const previous = append ? board.rows : pinned.filter(p => p.estado === stage && (!id || p.vacante_id === id))
    board.rows = unite([...previous, ...chunk.items])
    board.cursor = chunk.cursor
  } catch (e) { if (mine === revision) board.error = e.message }
  finally { if (mine === revision) { board.loading = false; board.moreBusy = false } }
}
watch(filter, reset, { immediate: true })
onScopeDispose(() => { revision++ })
function clearFilter() { sessionStorage.removeItem('pipeline_vacante'); filter.value = null }
function moves(p) {
  const index = stages.indexOf(p.estado)
  if (index < 0 || p.estado === 'rechazado') return []
  const choices = []
  if (index < 4) choices.push(stages[index + 1])
  if (index > 0) choices.push(stages[index - 1])
  if (index < 4) choices.push('rechazado')
  return choices
}
function move(p) {
  openPanel({
    title: 'Cambiar etapa', description: p.titulo_vacante,
    fields: [{ key: 'estado', label: 'Nueva etapa', type: 'select', required: true, options: moves(p) }],
    submitLabel: 'Guardar etapa',
    async submit(data) {
      await api('vacantes', 'PUT', itemPath('postulaciones', p.postulacion_id), data)
      markRecent('postulaciones', p.postulacion_id)
      selected.value = data.estado
      reset()
      notify('Etapa actualizada a ' + label(data.estado) + '.')
    },
  })
}
function manage(p) {
  openPanel({
    title: p.titulo_vacante || 'Postulación',
    details: [['Etapa', label(p.estado)], ['ID del candidato', p.candidato_id], ['ID de vacante', p.vacante_id],
      ['ID de postulación', p.postulacion_id], ['Actualizada', date(p.fecha_actualizacion)], ['Notas', p.notas || 'Sin notas']],
    actions: [
      ...(moves(p).length ? [{ label: 'Cambiar etapa', class: 'primary', run: () => move(p) }] : []),
      { label: 'Ver candidato', run: () => showCandidate(p.candidato_id) },
      ...(p.estado === 'entrevista' ? [{ label: 'Agendar entrevista', run: () => schedule(p) }] : []),
    ],
  })
}
</script>
<template>
  <header class="view-title"><h1>Postulaciones</h1></header>
  <p v-if="filter" class="filter-summary">Vacante <strong>{{ filter.titulo }}</strong><button class="text-btn" @click="clearFilter">Ver todas las vacantes</button></p>
  <nav class="stages" aria-label="Filtrar por etapa">
    <button v-for="s in stages" :key="s" type="button" :aria-pressed="selected === s" @click="selected = s">
      <span>{{ label(s) }}</span><small>{{ boards[s].loading ? '…' : boards[s].error ? 'Sin dato' : boards[s].rows.length + (boards[s].cursor ? '+' : '') }}</small>
    </button>
  </nav>
  <div class="section-title"><h2>{{ label(selected) }}</h2></div>
  <RecordList v-if="current" :key="selected" :title="'Postulaciones en ' + label(selected)" row-key="postulacion_id" :list="current"
    :columns="['Vacante','Candidato','Última actualización','Acciones']" empty="No hay postulaciones en esta etapa.">
    <template #default="{ item: p }">
      <td><button class="row-name" @click="manage(p)">{{ p.titulo_vacante || 'Ver postulación' }}</button></td>
      <td><button class="text-btn" :title="p.candidato_id" @click="showCandidate(p.candidato_id)">ID {{ p.candidato_id.slice(0, 8) }}</button></td>
      <td>{{ date(p.fecha_actualizacion) }}</td><td><button class="text-btn" @click="manage(p)">Gestionar</button></td>
    </template>
  </RecordList>
</template>
