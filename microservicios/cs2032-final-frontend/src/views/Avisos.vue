<script setup>
import Brand from '../components/Brand.vue'
defineProps({ page: String, back: String })
</script>
<template>
  <div class="public-page">
    <header class="public-header"><Brand/><a class="plain-link" :href="'#/' + back">Volver al CRM</a></header>
    <main id="contenido" class="legal">
      <template v-if="page === 'privacidad'">
        <h1>Política de privacidad</h1>
        <h2>Datos que usa el CRM</h2><p>El equipo de selección registra los datos de contacto y de experiencia de candidatos, sus currículums, postulaciones y entrevistas. Los usa para gestionar la selección dentro de su empresa.</p>
        <h2>Acceso y archivos</h2><p>La cuenta identifica a la empresa en cada solicitud. Los administradores pueden crear usuarios en su empresa. Los currículums en PDF se envían a Amazon S3 mediante un enlace temporal.</p>
        <h2>Sesión del navegador</h2><p>Esta aplicación guarda en la pestaña los datos de sesión, la empresa, el rol y algunos identificadores recientes. Cerrar sesión borra esa información de la pestaña.</p>
        <h2>Consultas sobre tus datos</h2><p>Dirige las solicitudes de acceso, corrección o eliminación al equipo de tu empresa que gestiona el proceso de selección.</p>
      </template>
      <template v-else>
        <h1>Términos de uso</h1>
        <h2>Uso del espacio de trabajo</h2><p>Usa la cuenta asignada por tu equipo para gestionar los procesos de selección de tu empresa. En el laboratorio utiliza perfiles y currículums de prueba.</p>
        <h2>Archivos y registros</h2><p>Sube únicamente documentos que tengas permiso para utilizar. Antes de cambiar una etapa, cancelar una entrevista o eliminar un registro, comprueba el candidato y la vacante.</p>
        <h2>Tu cuenta</h2><p>Mantén tus credenciales en privado. Si compartes un equipo, cierra la sesión al terminar. Para solicitar acceso o comunicar un problema, contacta al administrador de tu empresa.</p>
      </template>
    </main>
    <footer class="public-footer"><span>EmpleaCRM</span><div><a href="#/terminos">Términos de uso</a><a href="#/privacidad">Privacidad</a></div></footer>
  </div>
</template>
