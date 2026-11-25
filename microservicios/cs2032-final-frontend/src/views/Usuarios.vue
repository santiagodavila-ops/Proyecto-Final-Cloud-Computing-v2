<script setup>
import { reactive, ref } from 'vue'
import { api, company } from '../lib/api.js'

const blank = () => ({ nombre: '', email: '', password: '', rol: 'reclutador' })
const form = reactive(blank())
const error = ref('')
const success = ref('')
const busy = ref(false)
async function submit() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  success.value = ''
  try {
    await api('usuarios', 'POST', '/usuarios', { ...form, nombre: form.nombre.trim(), email: form.email.trim() })
    success.value = 'Se creó el usuario ' + form.email + '.'
    Object.assign(form, blank())
  } catch (e) { error.value = e.message }
  finally { busy.value = false }
}
</script>
<template>
  <header class="view-title"><h1>Usuarios</h1></header>
  <section class="user-form"><h2>Crear usuario</h2><p class="dim">La cuenta tendrá acceso a {{ company }}.</p>
    <form class="form" @submit.prevent="submit">
      <label>Nombre completo<input v-model="form.nombre" name="nombre" required></label>
      <label>Correo electrónico<input v-model="form.email" type="email" name="email" required></label>
      <label>Contraseña <input v-model="form.password" type="password" name="password" minlength="6" required autocomplete="new-password" aria-describedby="password-help"></label>
      <small id="password-help" class="field-help">Mínimo 6 caracteres.</small>
      <label>Rol<select v-model="form.rol" name="rol"><option value="reclutador">Reclutador</option><option value="administrador">Administrador</option></select></label>
      <p v-if="error" class="feedback error" role="alert">{{ error }}</p><p v-if="success" class="feedback" role="status">{{ success }}</p>
      <button class="btn primary" :disabled="busy">{{ busy ? 'Creando…' : 'Crear usuario' }}</button>
    </form>
  </section>
</template>
