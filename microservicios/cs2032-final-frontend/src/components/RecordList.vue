<script setup>
defineProps({
  title: String, columns: Array, rowKey: String,
  list: { type: Object, required: true }, empty: String,
})
</script>

<template>
  <section class="records" :aria-label="title" :aria-busy="list.loading || list.moreBusy">
    <div v-if="list.loading" class="skeleton" role="status"><span class="sr">Cargando registros</span><i v-for="i in 5" :key="i"></i></div>
    <template v-else>
      <div v-if="list.error" class="feedback error" role="alert">{{ list.error }} <button class="text-btn" @click="list.cursor ? list.more() : list.reload()">Reintentar</button></div>
      <div v-if="list.rows.length" class="table-scroll" role="region" :aria-label="title" tabindex="0">
        <table><caption class="sr">{{ title }}</caption><thead><tr><th v-for="col in columns" :key="col" scope="col">{{ col }}</th></tr></thead>
          <tbody><tr v-for="item in list.rows" :key="item[rowKey]"><slot :item="item"></slot></tr></tbody>
        </table>
      </div>
      <p v-else-if="!list.error" class="empty">{{ empty || 'No hay registros para esta vista.' }}</p>
      <div v-if="list.rows.length || list.cursor" class="table-foot">
        <span>{{ list.rows.length.toLocaleString('es-PE') }} {{ list.rows.length === 1 ? 'registro visible' : 'registros visibles' }}</span>
        <button v-if="list.cursor" class="btn small" :disabled="list.moreBusy" @click="list.more()">{{ list.moreBusy ? 'Cargando…' : 'Cargar más' }}</button>
      </div>
    </template>
  </section>
</template>
