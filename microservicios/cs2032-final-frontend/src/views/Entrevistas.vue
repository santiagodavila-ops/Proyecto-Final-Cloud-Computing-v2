<script setup>
import RecordList from '../components/RecordList.vue'
import { api } from '../lib/api.js'
import { interviewFields, notify, openPanel, removeRecord, schedule } from '../lib/dialogs.js'
import { date, itemPath, label, useFilter, useList } from '../lib/records.js'

const filter = useFilter('entrevistas')
const list = useList('entrevistas', () => ({ estado: filter.value }))
async function update(row, data) {
  await api('entrevistas', 'PUT', itemPath('entrevistas', row.entrevista_id), data)
  notify('Entrevista actualizada.')
  void list.reload()
}
function edit(row) {
  openPanel({ title: 'Editar entrevista', fields: interviewFields, values: row,
    submitLabel: 'Guardar cambios', submit: data => update(row, data) })
}
function cancel(row) {
  openPanel({
    title: 'Cancelar entrevista', description: 'Entrevista con ' + row.entrevistador + ' el ' + date(row.fecha_hora) + '.',
    submitLabel: 'Confirmar cancelación', submit: () => update(row, { estado: 'cancelada' }),
  })
}
function manage(row) {
  openPanel({
    title: 'Ficha de entrevista',
    details: [['Entrevistador', row.entrevistador], ['Fecha y hora de Lima', date(row.fecha_hora)], ['Estado', label(row.estado)],
      ['Modalidad', label(row.modalidad)], ['ID del candidato', row.candidato_id], ['ID de vacante', row.vacante_id],
      ['ID de entrevista', row.entrevista_id], ['ID de postulación', row.postulacion_id || null], ['Notas', row.notas || 'Sin notas']],
    actions: [{ label: 'Editar', class: 'primary', run: () => edit(row) },
      ...(row.estado === 'agendada' ? [
        { label: 'Marcar realizada', run: () => update(row, { estado: 'realizada' }) },
        { label: 'Cancelar entrevista', run: () => cancel(row) },
      ] : []),
      { label: 'Eliminar', class: 'danger-text', run: () => removeRecord({
        name: 'entrevistas', service: 'entrevistas', id: row.entrevista_id, title: 'Eliminar entrevista',
        message: 'Se eliminará la entrevista del ' + date(row.fecha_hora) + '.', success: 'Entrevista eliminada.', reload: list.reload,
      }) },
    ],
  })
}
function create() {
  schedule(null, () => {
    if (filter.value && filter.value !== 'agendada') filter.value = ''
    else void list.reload()
  })
}
</script>
<template>
  <header class="view-title"><h1>Entrevistas</h1><button class="btn primary" @click="create">Agendar entrevista</button></header>
  <div class="toolbar"><label>Estado de la entrevista<select v-model="filter"><option value="">Todas las entrevistas</option>
    <option value="agendada">Agendadas</option><option value="realizada">Realizadas</option><option value="cancelada">Canceladas</option></select></label></div>
  <RecordList title="Agenda de entrevistas" row-key="entrevista_id" :list="list" :columns="['Fecha y hora de Lima','Entrevistador','Estado','Acciones']" empty="No hay entrevistas con este filtro.">
    <template #default="{ item: row }">
      <td><button class="row-name" @click="manage(row)">{{ date(row.fecha_hora) }}</button><span class="cell-sub">{{ label(row.modalidad) }}</span></td>
      <td>{{ row.entrevistador }}<span class="cell-sub" v-if="row.notas">{{ row.notas }}</span></td><td><span class="state" :class="{ positive: row.estado === 'agendada' }">{{ label(row.estado) }}</span></td>
      <td><button class="text-btn" @click="manage(row)">Gestionar</button></td>
    </template>
  </RecordList>
</template>
