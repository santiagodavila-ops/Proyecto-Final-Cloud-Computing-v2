<script setup>
import { ref } from 'vue'
import { login, loginNotice } from '../lib/api.js'
import Brand from '../components/Brand.vue'
import photo from '../assets/escalera.webp'

const email = ref('')
const password = ref('')
const visible = ref(false)
const busy = ref(false)
const error = ref('')
async function enter() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try { await login(email.value.trim(), password.value) }
  catch (e) { error.value = e.message }
  finally { busy.value = false }
}
</script>

<template>
  <div class="access">
    <header class="public-header"><Brand/><a class="plain-link" href="./docs.html" target="_blank" rel="noopener">Documentación API</a></header>
    <main class="access-layout" id="contenido">
      <section class="cover" aria-label="Selección de personal">
        <img :src="photo" alt="" fetchpriority="high" width="1440" height="2160">
        <div class="cover-caption"><p>CRM de empleabilidad</p><h2>Selección<br><em>de personal.</em></h2></div>
      </section>
      <section class="login-section">
        <div class="login-form">
          <h1>Iniciar sesión</h1>
          <p class="lead">Ingresa con el correo de tu empresa.</p>
          <form class="form" @submit.prevent="enter">
            <label>Correo electrónico<input v-model="email" type="email" name="email" autocomplete="username" required placeholder="nombre@empresa.pe"></label>
            <div class="password-field"><label for="login-password">Contraseña</label><div class="password-wrap">
              <input id="login-password" v-model="password" :type="visible ? 'text' : 'password'" name="password" autocomplete="current-password" required>
              <button type="button" :aria-pressed="visible" @click="visible = !visible">{{ visible ? 'Ocultar' : 'Mostrar' }}</button>
            </div></div>
            <p v-if="error || loginNotice" class="feedback error" role="alert">{{ error || loginNotice }}</p>
            <button class="btn primary enter" :disabled="busy">{{ busy ? 'Ingresando…' : 'Ingresar' }}</button>
          </form>
          <details class="practice"><summary>Acceso del laboratorio</summary>
            <p>Usa tu cuenta de práctica y la contraseña facilitada por tu equipo.</p>
            <button class="text-btn" type="button" @click="email = 'demo.tenant_1@cs2032.test'">Usar correo de práctica</button>
          </details>
        </div>
      </section>
    </main>
    <footer class="public-footer"><span>EmpleaCRM</span><div><a href="#/terminos">Términos de uso</a><a href="#/privacidad">Privacidad</a></div></footer>
  </div>
</template>
