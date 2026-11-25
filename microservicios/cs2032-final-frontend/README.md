# EmpleaCRM en Vue

Interfaz del CRM de Empleabilidad Nacional. Usa Vue 3 y Vite. El frontend consume las cinco API del proyecto y se publica en la aplicación Amplify `cs2032-crm-empleabilidad`, rama `main`, en `us-east-1`.

## Desarrollo local

Desde `microservicios/cs2032-final-frontend/`, usa Node 22.12 o posterior de la rama 22, o Node 24.

```bash
npm ci
npm run dev
```

Abre la dirección que indique Vite. El navegador usa las API de `config.js`, también en desarrollo local. Para revisar la compilación de producción, ejecuta ambos comandos.

```bash
npm run build
npm run preview
```

## Pantallas y datos

| Pantalla | Operaciones |
| --- | --- |
| Acceso | Inicio de sesión por correo y contraseña. La empresa y el rol provienen de la respuesta del servicio Usuarios. |
| Resumen | Consulta y recálculo del reporte de la empresa. Métricas de contratación y desglose por etapa. |
| Candidatos | Alta, búsqueda por ID, edición, eliminación y carga de CV. El PDF se envía a S3 y el servicio de Candidatos confirma la carga. |
| Vacantes | Alta y edición, cierre y reapertura, postulación de candidatos y acceso a las postulaciones de una vacante. |
| Postulaciones | Seis etapas, filtro por vacante, cambio de etapa, ficha del candidato y programación de entrevistas. |
| Entrevistas | Agenda, edición en hora de Lima, cambio de estado y eliminación. |
| Usuarios | Creación de cuentas de la misma empresa por un administrador. |

Las funciones de cada fila están en **Gestionar**. **Actividad de la API** muestra el método, el servicio, la ruta, el resultado y el tiempo de las llamadas recientes de la pestaña. Las tablas permiten cargar la siguiente página. Los registros creados durante la sesión aparecen primero cuando cumplen el filtro aplicado.

La sesión utiliza las mismas claves de `sessionStorage` que la versión anterior. Las solicitudes de negocio envían el token de acceso en `Authorization`. El backend identifica la empresa. Las solicitudes concurrentes comparten la renovación del token. La interfaz muestra el nombre de la empresa que corresponde al `tenant_id` de la cuenta.

## Configuración del laboratorio

`config.js` conserva las cinco direcciones API y los nombres de las empresas. El archivo se sirve por separado y se copia a `dist/` con cada compilación. Al cambiar de laboratorio o de etapa, revisa también los servidores declarados en `scripts/generar_openapi.py` y vuelve a generar la documentación.

```bash
python3 scripts/generar_openapi.py
```

`docs.html` y `docs/openapi/` conservan sus rutas. Swagger mantiene la dependencia de CDN que tenía el proyecto original.

## Despliegue en Amplify

Desde la carpeta del frontend, el comando habitual compila, comprime el **contenido** de `dist/` y lo publica mediante AWS CLI. Requiere acceso al laboratorio desde el entorno que ejecute el script.

```bash
bash scripts/desplegar_amplify.sh
```

Para publicar un ZIP ya compilado, el mismo script acepta su ruta. En esta modalidad bastan Bash, AWS CLI y curl.

```bash
bash scripts/desplegar_amplify.sh --zip /ruta/al/EmpleaCRM-Amplify.zip
```

El script reutiliza la aplicación y la rama por nombre, y espera el resultado de Amplify. El archivo para publicación contiene `index.html` en la raíz. Las rutas de página usan `#/`, por lo que se conservan los enlaces del CRM.

## Diseño y recursos

Los títulos usan Instrument Serif. Los formularios y las tablas usan Work Sans. Los archivos de fuente y la fotografía se sirven con la aplicación. La compilación incluye los avisos de licencia en `licencias/`.

- Fotografía de la portada por Gökhan Aytaç. [Fotografía en Unsplash](https://unsplash.com/photos/modern-concrete-staircase-with-minimalist-interior-lighting-MeIfmBXiSNo) y [licencia de Unsplash](https://unsplash.com/license).
- Referencias de implementación. [Componentes de Vue](https://vuejs.org/guide/scaling-up/sfc.html), [tablas del sistema de diseño GOV.UK](https://design-system.service.gov.uk/components/table/) y [despliegues manuales de Amplify](https://docs.aws.amazon.com/amplify/latest/userguide/manual-deploys.html).
