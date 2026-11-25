<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../lib/api.js'
import { notify } from '../lib/dialogs.js'
import { date, label, number, stages } from '../lib/records.js'

const report = ref(null)
const loading = ref(false)
const error = ref('')
const missing = ref(false)
const metrics = [
  ['Candidatos', 'total_candidatos', 'candidatos'], ['Vacantes', 'total_vacantes', 'vacantes'],
  ['Postulaciones', 'total_postulaciones', 'pipeline'], ['Entrevistas', 'total_entrevistas', 'entrevistas'],
]
const scale = computed(() => Math.max(1, ...Object.values(report.value?.postulaciones_por_estado || {}).map(Number)))

async function read(generate = false) {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    const data = generate ? await api('reportes', 'POST', '/reportes/generar', {}) : await api('reportes', 'GET', '/reportes/resumen_general')
    if (!data.reporte) throw new Error('No se recibió el resumen de selección.')
    report.value = data.reporte
    missing.value = false
    if (generate) notify('Reporte actualizado.')
  } catch (e) {
    if (!generate && e.status === 404) missing.value = true
    else error.value = e.message
  } finally { loading.value = false }
}
onMounted(() => read())
</script>
<template>
  <header class="view-title"><div><h1>Resumen de <em>selección</em></h1>
    <p v-if="report?.fecha_actualizacion" class="dim">Actualizado el {{ date(report.fecha_actualizacion) }} · Lima</p></div>
    <button class="btn primary" :disabled="loading" @click="read(true)">{{ loading && report ? 'Actualizando…' : 'Recalcular reporte' }}</button>
  </header>
  <p v-if="error" class="feedback error" role="alert">{{ error }} <button class="text-btn" @click="read()">Volver a consultar</button></p>
  <div v-if="loading && !report" class="skeleton large" role="status"><span class="sr">Cargando reporte</span><i v-for="i in 4" :key="i"></i></div>
  <p v-else-if="missing && !report" class="empty">Tu empresa aún no tiene un resumen. Selecciona «Recalcular reporte» para generarlo.</p>
  <template v-if="report">
    <div class="metric-strip"><a v-for="[name,key,route] in metrics" :key="key" :href="'#/' + route">
      <span>{{ name }}</span><strong>{{ number(report[key]) }}</strong>
    </a></div>
    <div class="report-layout">
      <section class="report-flow"><div class="section-title"><h2>Etapas de postulación</h2><a href="#/pipeline" class="plain-link">Ver postulaciones</a></div>
        <ul class="bars"><li v-for="stage in stages" :key="stage">
          <span>{{ label(stage) }}</span><span class="track" aria-hidden="true"><i :style="{ width: (Number(report.postulaciones_por_estado?.[stage] || 0) / scale * 100) + '%' }"></i></span>
          <strong>{{ number(report.postulaciones_por_estado?.[stage]) }}</strong>
        </li></ul>
      </section>
      <section class="conversion"><h2>Contratación</h2><strong>{{ number(report.tasa_contratacion) }}<small> %</small></strong>
        <p>{{ number(report.total_contratados) }} contratados de {{ number(report.total_postulaciones) }} postulaciones.</p></section>
    </div>
    <div class="breakdowns">
      <section v-for="[title,field,order] in [
        ['Estado de vacantes','vacantes_por_estado',['abierta','cerrada']],
        ['Estado de entrevistas','entrevistas_por_estado',['agendada','realizada','cancelada']]
      ]" :key="field"><h2>{{ title }}</h2>
        <dl class="inline-stats"><div v-for="key in new Set([...order, ...Object.keys(report[field] || {})])" :key="key">
          <dt>{{ label(key) }}</dt><dd>{{ number(report[field]?.[key]) }}</dd></div></dl>
      </section>
    </div>
    <p class="report-note">{{ number(report.total_usuarios) }} usuarios en esta empresa.</p>
  </template>
</template>
