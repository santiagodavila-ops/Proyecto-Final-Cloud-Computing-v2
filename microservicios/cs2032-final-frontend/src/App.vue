<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { activity, callCount, company, logout, session } from './lib/api.js'
import { closePanel, notice, panel } from './lib/dialogs.js'
import Brand from './components/Brand.vue'
import UiDialog from './components/UiDialog.vue'
import Acceso from './views/Acceso.vue'
import Avisos from './views/Avisos.vue'
import Resumen from './views/Resumen.vue'
import Candidatos from './views/Candidatos.vue'
import Vacantes from './views/Vacantes.vue'
import Postulaciones from './views/Postulaciones.vue'
import Entrevistas from './views/Entrevistas.vue'
import Usuarios from './views/Usuarios.vue'

const sections = [
  { id: 'dashboard', name: 'Resumen', view: Resumen },
  { id: 'candidatos', name: 'Candidatos', view: Candidatos },
  { id: 'vacantes', name: 'Vacantes', view: Vacantes },
  { id: 'pipeline', name: 'Postulaciones', view: Postulaciones },
  { id: 'entrevistas', name: 'Entrevistas', view: Entrevistas },
  { id: 'usuarios', name: 'Usuarios', view: Usuarios },
]
const available = computed(() => sections.filter(s => s.id !== 'usuarios' || session.value?.rol === 'administrador'))
const readRoute = () => location.hash.slice(2) || 'dashboard'
const route = ref(readRoute())
const lastView = ref('dashboard')
const legal = computed(() => ['terminos', 'privacidad'].includes(route.value))
const current = computed(() => available.value.find(s => s.id === route.value) || sections[0])
const mobileNav = ref(false)
const today = new Intl.DateTimeFormat('es-PE', { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'America/Lima' }).format(new Date())

function updateRoute() { route.value = readRoute() }
onMounted(() => window.addEventListener('hashchange', updateRoute))
onUnmounted(() => window.removeEventListener('hashchange', updateRoute))
watch([route, () => session.value?.tenant_id], () => {
  closePanel()
  notice.value = ''
  mobileNav.value = false
  if (!legal.value && session.value) lastView.value = current.value.id
  if (!session.value) lastView.value = 'dashboard'
  const title = legal.value ? (route.value === 'privacidad' ? 'Privacidad' : 'Términos de uso') : session.value ? current.value.name : 'Iniciar sesión'
  document.title = title + ' | EmpleaCRM' + (session.value ? ' · ' + company.value : '')
  window.scrollTo(0, 0)
}, { immediate: true })
function exit() { logout(); location.hash = '#/dashboard' }
function documentFocus() {
  const main = document.getElementById('contenido')
  if (main) { main.tabIndex = -1; main.focus() }
}
</script>

<template>
  <a class="skip" href="#contenido" @click.prevent="documentFocus">Saltar al contenido</a>
  <Avisos v-if="legal" :page="route" :back="lastView"/>
  <Acceso v-else-if="!session"/>
  <div v-else class="workspace">
    <aside class="sidebar">
      <div class="sidebar-mast"><a href="#/dashboard" aria-label="EmpleaCRM, resumen"><Brand/></a>
        <button class="mobile-toggle" type="button" :aria-expanded="mobileNav" aria-controls="workspace-nav" @click="mobileNav = !mobileNav">{{ mobileNav ? 'Cerrar menú' : 'Menú' }}</button>
      </div>
      <div id="workspace-nav" class="sidebar-inner" :class="{ opened: mobileNav }">
        <nav aria-label="Navegación principal" @click="mobileNav = false">
          <a v-for="s in available" :key="s.id" :href="'#/' + s.id" :aria-current="current.id === s.id ? 'page' : undefined">{{ s.name }}</a>
        </nav>
        <div class="sidebar-bottom"><a href="./docs.html" target="_blank" rel="noopener">Documentación API</a>
          <div class="account"><span>{{ session.email }}</span><small>{{ session.rol === 'administrador' ? 'Administrador' : 'Reclutador' }}</small></div>
          <button class="side-exit" @click="exit">Cerrar sesión</button>
        </div>
      </div>
    </aside>
    <div class="desk">
      <header class="desk-head"><span class="company-name">{{ company }}</span><span class="today">{{ today }}</span></header>
      <main id="contenido" class="work-main"><component :is="current.view" :key="current.id + ':' + session.tenant_id"/></main>
      <footer class="desk-foot">
        <details class="activity"><summary>Actividad de la API <span>{{ callCount }}</span></summary>
          <div v-if="activity.length" class="table-scroll" role="region" aria-label="Llamadas recientes" tabindex="0">
            <table><caption class="sr">Últimas llamadas de esta sesión</caption><thead><tr><th>Método</th><th>Servicio</th><th>Ruta</th><th>Estado</th><th>Tiempo</th></tr></thead>
              <tbody><tr v-for="a in activity" :key="a.id"><td>{{ a.method }}</td><td>{{ a.service }}</td><td class="path">{{ a.path }}</td><td>{{ a.status || 'Sin conexión' }}</td><td>{{ a.ms }} ms</td></tr></tbody>
            </table>
          </div><p v-else class="dim">Aún no hay llamadas en esta pestaña.</p>
        </details>
        <div class="foot-links"><span>{{ session.tenant_id }}</span><a href="#/terminos">Términos de uso</a><a href="#/privacidad">Privacidad</a></div>
      </footer>
    </div>
  </div>
  <UiDialog v-if="panel" :key="panel.key" :model="panel"/>
  <div class="announcer" role="status" aria-live="polite"><p v-if="notice">{{ notice }}</p></div>
</template>
