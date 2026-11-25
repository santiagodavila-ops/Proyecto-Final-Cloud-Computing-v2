import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Conserva las mismas rutas públicas que usan el laboratorio y Swagger.
const services = ['usuarios', 'candidatos', 'vacantes', 'entrevistas', 'reportes']
const files = ['config.js', 'docs.html', ...services.map(name => 'docs/openapi/' + name + '.json')]

export default defineConfig({
  base: './',
  plugins: [
    vue(),
    {
      name: 'archivos-del-laboratorio',
      generateBundle() {
        for (const [pkg, name] of [
          ['vue', 'vue'], ['@fontsource/work-sans', 'work-sans'], ['@fontsource/instrument-serif', 'instrument-serif'],
        ]) {
          const license = new URL('./node_modules/' + pkg + '/LICENSE', import.meta.url)
          this.emitFile({ type: 'asset', fileName: 'licencias/' + name + '.txt', source: readFileSync(license) })
        }
        for (const fileName of files) {
          const path = fileURLToPath(new URL(fileName, import.meta.url))
          this.emitFile({ type: 'asset', fileName, source: readFileSync(path) })
        }
      },
    },
  ],
})
