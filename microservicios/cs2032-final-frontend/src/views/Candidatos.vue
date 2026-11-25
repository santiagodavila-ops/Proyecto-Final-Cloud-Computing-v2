<script setup>
import { ref } from 'vue'
import RecordList from '../components/RecordList.vue'
import { api, uploadPdf } from '../lib/api.js'
import { copyId, notify, openPanel, removeRecord, showCandidate } from '../lib/dialogs.js'
import { itemPath, label, markRecent, useList } from '../lib/records.js'

const list = useList('candidatos')
const id = ref('')
const fields = [
  { key: 'nombre', label: 'Nombre completo', required: true },
  { key: 'email', label: 'Correo electrónico', type: 'email', required: true },
  { key: 'telefono', label: 'Teléfono', type: 'tel', required: true },
  { key: 'profesion', label: 'Profesión', required: true },
]
function edit(c) {
  openPanel({
    title: c ? 'Editar candidato' : 'Nuevo candidato', values: c,
    fields: c ? [...fields, { key: 'estado', label: 'Estado', type: 'select', options: ['activo', 'inactivo'] }] : fields,
    submitLabel: c ? 'Guardar cambios' : 'Crear candidato',
    async submit(data) {
      if (c) await api('candidatos', 'PUT', itemPath('candidatos', c.candidato_id), data)
      else {
        const { candidato } = await api('candidatos', 'POST', '/candidatos', data)
        markRecent('candidatos', candidato.candidato_id)
      }
      notify(c ? 'Candidato actualizado.' : 'Candidato creado.')
      void list.reload()
    },
  })
}
function attach(c) {
  const path = itemPath('candidatos', c.candidato_id) + '/cv-url'
  let sent = null
  openPanel({
    title: 'Subir currículum', description: c.nombre, fields: [
      { key: 'pdf', label: 'Archivo PDF', type: 'file', required: true, accept: '.pdf,application/pdf' },
    ], submitLabel: 'Subir PDF',
    async submit({ pdf }) {
      if (!pdf || (!pdf.name.toLowerCase().endsWith('.pdf') && pdf.type !== 'application/pdf')) throw new Error('Selecciona un archivo PDF.')
      if (pdf !== sent) {
        const { url_subida } = await api('candidatos', 'POST', path, {})
        if (!url_subida) throw new Error('No se recibió el enlace para subir el archivo.')
        await uploadPdf(url_subida, pdf)
        sent = pdf
      }
      try { await api('candidatos', 'POST', path, { confirmar: true }) }
      catch (e) { throw new Error('El PDF se envió. Pulsa «Subir PDF» para reintentar la confirmación. ' + e.message) }
      notify('Currículum guardado.')
      void list.reload()
    },
  })
}
function manage(c) {
  openPanel({
    title: c.nombre, details: [['Profesión', c.profesion], ['Correo', c.email], ['Teléfono', c.telefono],
      ['Estado', label(c.estado)], ['Currículum', c.cv_url ? 'Cargado' : 'Pendiente'], ['ID del candidato', c.candidato_id]],
    actions: [
      { label: 'Editar', class: 'primary', run: () => edit(c) },
      { label: 'Subir CV', run: () => attach(c) },
      { label: 'Ver ficha completa', run: () => showCandidate(c.candidato_id) },
      { label: 'Eliminar', class: 'danger-text', run: () => removeRecord({
        name: 'candidatos', service: 'candidatos', id: c.candidato_id, title: 'Eliminar candidato',
        message: 'Se eliminará el registro de ' + c.nombre + '.', success: 'Candidato eliminado.', reload: list.reload,
      }) },
    ],
  })
}
</script>
<template>
  <header class="view-title"><h1>Candidatos</h1><button class="btn primary" @click="edit(null)">Nuevo candidato</button></header>
  <div class="toolbar"><form class="search" @submit.prevent="id.trim() && showCandidate(id.trim())">
    <label for="candidate-id">Buscar por ID</label><div class="inline-field"><input id="candidate-id" v-model="id" placeholder="ID del candidato" required><button class="btn">Buscar</button></div>
  </form></div>
  <RecordList title="Directorio de candidatos" row-key="candidato_id" :list="list" :columns="['Candidato','Contacto','Estado','Currículum','Acciones']" empty="Todavía no hay candidatos. Puedes crear el primero.">
    <template #default="{ item: c }">
      <td><button class="row-name" @click="manage(c)">{{ c.nombre }}</button><span class="cell-sub">{{ c.profesion }}</span>
        <button class="id-btn" :title="c.candidato_id" @click="copyId(c.candidato_id)">ID {{ c.candidato_id.slice(0, 8) }}</button></td>
      <td>{{ c.email }}<span class="cell-sub">{{ c.telefono }}</span></td>
      <td><span class="state" :class="{ positive: c.estado === 'activo' }">{{ label(c.estado) }}</span></td>
      <td>{{ c.cv_url ? 'Cargado' : 'Pendiente' }}</td>
      <td><button class="text-btn" @click="manage(c)">Gestionar</button></td>
    </template>
  </RecordList>
</template>
