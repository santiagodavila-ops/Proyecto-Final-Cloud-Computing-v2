<script setup>
import RecordList from '../components/RecordList.vue'
import { api } from '../lib/api.js'
import { notify, openPanel, removeRecord } from '../lib/dialogs.js'
import { date, firstPage, itemPath, label, markRecent, money, useFilter, useList } from '../lib/records.js'

const filter = useFilter('vacantes')
const list = useList('vacantes', () => ({ estado: filter.value }))
const fields = [
  { key: 'titulo', label: 'Título del puesto', required: true },
  { key: 'descripcion', label: 'Descripción', type: 'textarea', required: true },
  { key: 'area', label: 'Área' }, { key: 'ubicacion', label: 'Ubicación' },
  { key: 'modalidad', label: 'Modalidad', type: 'select', options: ['presencial', 'remoto', 'hibrido'] },
  { key: 'salario', label: 'Salario en soles', type: 'number' },
]
function edit(v) {
  openPanel({
    title: v ? 'Editar vacante' : 'Nueva vacante', values: v, fields, submitLabel: v ? 'Guardar cambios' : 'Publicar vacante',
    async submit(data) {
      if (v) await api('vacantes', 'PUT', itemPath('vacantes', v.vacante_id), data)
      else {
        const { vacante } = await api('vacantes', 'POST', '/vacantes', data)
        markRecent('vacantes', vacante.vacante_id)
      }
      notify(v ? 'Vacante actualizada.' : 'Vacante publicada.')
      if (!v && filter.value === 'cerrada') filter.value = ''
      else void list.reload()
    },
  })
}
function apply(v) {
  openPanel({
    title: 'Postular candidato', description: v.titulo, submitLabel: 'Crear postulación',
    async prepare() {
      const { items } = await firstPage('candidatos')
      return { fields: [
        { key: 'candidato_id', label: 'Candidato', type: 'select', options: [
          ['', 'Seleccionar candidato'], ...items.map(c => [c.candidato_id, c.nombre + ' · ' + c.profesion]),
        ] },
        { key: 'otro_id', label: 'O ingresa un ID de candidato' },
        { key: 'notas', label: 'Notas', type: 'textarea' },
      ] }
    },
    async submit(data) {
      const candidate = data.otro_id || data.candidato_id
      if (!candidate) throw new Error('Selecciona un candidato o ingresa su ID.')
      const { postulacion } = await api('vacantes', 'POST', '/postulaciones', {
        vacante_id: v.vacante_id, candidato_id: candidate, notas: data.notas || '',
      })
      if (postulacion) markRecent('postulaciones', postulacion.postulacion_id)
      notify('Postulación creada.')
    },
  })
}
function pipeline(v) {
  sessionStorage.setItem('pipeline_vacante', JSON.stringify({ id: v.vacante_id, titulo: v.titulo }))
  location.hash = '#/pipeline'
}
function manage(v) {
  const open = v.estado === 'abierta'
  openPanel({
    title: v.titulo, description: v.descripcion,
    details: [['Área', v.area], ['Modalidad', label(v.modalidad)], ['Ubicación', v.ubicacion], ['Salario', money(v.salario)],
      ['Estado', label(v.estado)], ['Publicada', date(v.fecha_publicacion)], ['ID de vacante', v.vacante_id]],
    actions: [
      ...(open ? [{ label: 'Postular candidato', class: 'primary', run: () => apply(v) }] : []),
      { label: 'Ver postulaciones', run: () => pipeline(v) }, { label: 'Editar', run: () => edit(v) },
      { label: open ? 'Cerrar vacante' : 'Reabrir vacante', run: async () => {
        await api('vacantes', 'PUT', itemPath('vacantes', v.vacante_id), { estado: open ? 'cerrada' : 'abierta' })
        notify(open ? 'Vacante cerrada.' : 'Vacante reabierta.')
        void list.reload()
      } },
      { label: 'Eliminar', class: 'danger-text', run: () => removeRecord({
        name: 'vacantes', service: 'vacantes', id: v.vacante_id, title: 'Eliminar vacante',
        message: 'Se eliminará la vacante «' + v.titulo + '».', success: 'Vacante eliminada.', reload: list.reload,
      }) },
    ],
  })
}
</script>
<template>
  <header class="view-title"><h1>Vacantes</h1><button class="btn primary" @click="edit(null)">Nueva vacante</button></header>
  <div class="toolbar"><label>Estado de la vacante<select v-model="filter"><option value="">Todas las vacantes</option><option value="abierta">Abiertas</option><option value="cerrada">Cerradas</option></select></label></div>
  <RecordList title="Vacantes de la empresa" row-key="vacante_id" :list="list" :columns="['Puesto','Ubicación','Salario','Estado','Acciones']" empty="No hay vacantes con este filtro.">
    <template #default="{ item: v }">
      <td><button class="row-name" @click="manage(v)">{{ v.titulo }}</button><span class="cell-sub">{{ v.area }}</span></td>
      <td>{{ v.ubicacion || 'Sin indicar' }}<span class="cell-sub">{{ label(v.modalidad) }}</span></td><td>{{ money(v.salario) }}</td>
      <td><span class="state" :class="{ positive: v.estado === 'abierta' }">{{ label(v.estado) }}</span></td>
      <td><button class="text-btn" @click="manage(v)">Gestionar</button></td>
    </template>
  </RecordList>
</template>
