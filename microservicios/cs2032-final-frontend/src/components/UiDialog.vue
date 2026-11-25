<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, shallowRef } from 'vue'
import { closePanel, copyId, panel } from '../lib/dialogs.js'
import { label, limaInput } from '../lib/records.js'

const props = defineProps({ model: { type: Object, required: true } })
const box = ref(null)
const prepared = shallowRef({})
const spec = computed(() => ({ ...props.model, ...prepared.value }))
const values = reactive({})
const busy = ref(false)
const preparing = ref(Boolean(props.model.prepare))
const preparationError = ref('')
const error = ref('')
const optionValue = option => Array.isArray(option) ? option[0] : option
const optionText = option => Array.isArray(option) ? option[1] : label(option)

function defaults() {
  for (const field of spec.value.fields || []) {
    const initial = spec.value.values?.[field.key]
    if (field.type === 'datetime-local') values[field.key] = limaInput(initial)
    else if (initial != null) values[field.key] = initial
    else if (field.type === 'select') values[field.key] = optionValue(field.options[0] ?? '')
    else values[field.key] = ''
  }
}
async function prepare() {
  preparing.value = true
  preparationError.value = ''
  try {
    prepared.value = await props.model.prepare()
    defaults()
  } catch (e) { preparationError.value = e.message }
  finally { preparing.value = false }
}
onMounted(() => {
  box.value.showModal()
  defaults()
  if (props.model.prepare) void prepare()
})
onBeforeUnmount(() => { if (box.value?.open) box.value.close() })
function cancel() { if (!busy.value) closePanel() }
async function perform(action) {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    await action()
    if (panel.value?.key === props.model.key) closePanel()
  } catch (e) { error.value = e.message }
  finally { busy.value = false }
}
function submit() {
  const body = {}
  for (const field of spec.value.fields || []) {
    let value = values[field.key]
    if (typeof value === 'string' && field.type !== 'password') value = value.trim()
    if ((value === '' || value == null) && !field.allowEmpty) {
      if (field.required) { error.value = 'Completa el campo ' + field.label + '.'; return }
      continue
    }
    if (field.type === 'number') value = Number(value)
    if (field.type === 'datetime-local') value = value + ':00-05:00'
    body[field.key] = value
  }
  void perform(() => spec.value.submit(body))
}
</script>

<template>
  <dialog ref="box" class="dialog" aria-labelledby="dialog-title" @cancel.prevent="cancel">
    <div class="dialog-top">
      <h2 id="dialog-title">{{ spec.title }}</h2>
      <button class="text-btn" type="button" :disabled="busy" @click="cancel">Cerrar</button>
    </div>
    <p v-if="spec.description" class="dim">{{ spec.description }}</p>
    <div v-if="preparing" class="skeleton" role="status"><span class="sr">Cargando opciones</span><i></i><i></i></div>
    <div v-else-if="preparationError" class="feedback error" role="alert">
      {{ preparationError }} <button class="text-btn" @click="prepare">Reintentar</button>
    </div>
    <p v-else-if="spec.unavailable" class="feedback" role="status">{{ spec.unavailable }}</p>
    <template v-else>
      <dl v-if="spec.details" class="details-list">
        <div v-for="[key, value] in spec.details" :key="key">
          <dt>{{ key }}</dt><dd>{{ value ?? 'Sin dato' }} <button v-if="key.startsWith('ID') && value" class="text-btn" type="button" @click="copyId(value)">Copiar</button></dd>
        </div>
      </dl>
      <form v-if="spec.submit" class="form" @submit.prevent="submit">
        <label v-for="f in spec.fields" :key="f.key">{{ f.label }}
          <select v-if="f.type === 'select'" v-model="values[f.key]" :name="f.key" :required="f.required" :disabled="busy">
            <option v-for="o in f.options" :key="optionValue(o)" :value="optionValue(o)">{{ optionText(o) }}</option>
          </select>
          <textarea v-else-if="f.type === 'textarea'" v-model="values[f.key]" :name="f.key" :required="f.required" :disabled="busy" rows="3"></textarea>
          <input v-else-if="f.type === 'file'" type="file" :name="f.key" :accept="f.accept" :required="f.required" :disabled="busy"
            @change="values[f.key] = $event.target.files[0]">
          <input v-else v-model="values[f.key]" :name="f.key" :type="f.type || 'text'" :required="f.required"
            :autocomplete="f.autocomplete || 'off'" :min="f.type === 'number' ? 0 : undefined"
            :step="f.type === 'number' ? 'any' : undefined" :minlength="f.minlength" :disabled="busy">
        </label>
        <p v-if="spec.hint" class="dim">{{ spec.hint }}</p>
        <p v-if="error" class="feedback error" role="alert">{{ error }}</p>
        <div class="dialog-actions">
          <button type="button" class="btn" :disabled="busy" @click="cancel">Cancelar</button>
          <button class="btn" :class="spec.danger ? 'danger' : 'primary'" :disabled="busy">{{ busy ? 'Procesando…' : spec.submitLabel || 'Guardar' }}</button>
        </div>
      </form>
      <template v-else-if="spec.actions?.length">
        <p v-if="error" class="feedback error" role="alert">{{ error }}</p>
        <div class="dialog-actions"><button v-for="a in spec.actions" :key="a.label" class="btn" :class="a.class" :disabled="busy" @click="perform(a.run)">{{ a.label }}</button></div>
      </template>
    </template>
  </dialog>
</template>
