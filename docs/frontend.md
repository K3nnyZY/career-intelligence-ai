# Arquitectura del frontend

React 19, TypeScript estricto y Tailwind CSS 4, compilados con Vite 8. La elección es una **SPA modular organizada por funcionalidades**. FastAPI mantiene el procesamiento de documentos y las reglas de negocio; React se encarga del flujo de revisión y presentación.

Esta estructura encaja con una aplicación privada que ya tiene una API Python: un flujo, sin SEO, SSR ni contenido público. React documenta Vite como opción para construir una aplicación con estas restricciones; si aparecen nuevas necesidades de renderizado, hay que reevaluar el framework. [React: aplicaciones desde cero](https://react.dev/learn/build-a-react-app-from-scratch). Tailwind usa su plugin oficial de Vite y configuración mediante CSS. [Tailwind CSS 4 con Vite](https://tailwindcss.com/docs/installation/using-vite).

## Estructura y responsabilidades

```text
frontend/
  src/
    app/                         # Composición, entrada y estilos globales
    features/comparison/
      ComparisonPage.tsx         # Composición del flujo CV–vacante
      api/                       # Contratos Zod, tipos y operaciones HTTP
      model/                     # Estado, invariantes y ciclo de peticiones
      components/                # Perfil, vacante y resultados
    shared/
      api/                       # Transporte fetch y errores uniformes
      ui/                        # Button, Panel y TextField
    test/                        # Setup y fixtures exclusivamente ficticios
  e2e/                           # Pruebas contra la API y build reales
```

Dirección de dependencias: `app → features → shared`. Dentro de la funcionalidad, los componentes consumen el modelo y los contratos; el modelo usa la API; la API usa el transporte compartido. `shared` no conoce funcionalidades ni la aplicación. ESLint bloquea esas dependencias inversas y que API/modelo dependan de componentes. Las pruebas se colocan junto al código que verifican. Añadir una funcionalidad debe crear su propio directorio, sin convertir `shared` en un contenedor de lógica de negocio.

## Estado y solicitudes

`sessionReducer` concentra las reglas: no se compara sin extracción revisada y confirmación; editar el CV invalida perfil, selección y resultados; cambiar habilidades exige confirmar otra vez; editar la vacante invalida el resultado. Seleccionar cero habilidades es válido y se envía `[]` explícitamente.

`useComparison` coordina carga, revisión y comparación. Usa `AbortController` y un identificador de generación para impedir que una respuesta antigua restaure datos después de borrar la sesión. Cancela al desmontarse; limpia en `pagehide` y al restaurar desde historial. Los campos y habilidades se bloquean mientras hay una petición; borrar sigue disponible. El archivo se envía como bytes y su nombre no llega a la API; el input libera su referencia inmediatamente.

Las respuestas se tratan como `unknown` y se validan con Zod antes de entrar en el estado. Los tipos se derivan de los esquemas y el cliente centraliza errores, `cache: no-store` y `credentials: omit`. Los contratos Python y TypeScript se sincronizan manualmente; las pruebas E2E contra respuestas reales detectan incompatibilidades. Los tipos no se generan desde OpenAPI.

Para estas operaciones POST por iniciativa del usuario, `useReducer` y un cliente acotado mantienen una sesión efímera. Si hay consultas compartidas, historial o múltiples pantallas, evaluar un router y TanStack Query con reglas explícitas para no retener CV.

## Estilos y accesibilidad

Tailwind CSS 4 se integra con `@tailwindcss/vite`; `app/styles.css` define tokens con `@theme` y estilos base. Los componentes usan utilidades estáticas y variantes pequeñas. Etiquetas de campos, estado anunciado con `aria-live`, controles nativos, foco en los resultados, contraste y distribución adaptable a móvil. React renderiza evidencia como texto, sin `dangerouslySetInnerHTML`.

## Desarrollo, build y distribución

Recomendado: Node 24 LTS, Python 3.11+. Desde la raíz:

```bash
npm --prefix frontend ci
npm --prefix frontend run dev
```

FastAPI debe estar ejecutándose en `127.0.0.1:8000`. Vite sirve la UI en `127.0.0.1:5173` y reenvía rutas API mediante proxy. Conserva Host y Origin del navegador para respetar la comprobación de origen de la API; no añade permisos CORS al backend. Ambos servidores escuchan en loopback.

```bash
npm --prefix frontend run build
```

El build comprueba tipos y escribe HTML, JS y CSS con nombres hash en `career_ai/static/`. FastAPI sirve `/` y `/static/assets/*`. El runtime del build necesita solo Python. CSP mantiene scripts y estilos del mismo origen, y las respuestas continúan con `no-store`. El wheel incluye los assets compilados; **compila antes de construirlo**. Docker construye el frontend en una etapa Node y lo copia a la etapa Python. No se ha validado Docker en este entorno.

`career_ai/static/` es un artefacto generado e ignorado. CI ejecuta `npm ci`, lint, pruebas y build antes de los tests Python. La API puede importarse sin el frontend compilado; `/health` y sus contratos siguen funcionando, mientras `/` devuelve 503 indicando cómo compilar.

## Verificación

```bash
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend test
npm --prefix frontend run build
.venv/bin/python -m unittest discover -s tests -v
```

Vitest y Testing Library verifican revisión/confirmación, selección vacía, invalidación, errores de contrato, borrado y respuestas tardías. Playwright verifica DOCX, corrección del texto, selección, evidencia, móvil y borrado contra la API real, usando únicamente documentos ficticios generados en memoria.

Para Playwright, activa el entorno Python y prepara Chromium una vez:

```bash
source .venv/bin/activate
cd frontend
npx playwright install chromium
npm run test:e2e
```

El runner inicia FastAPI si no está activo; exige que exista el build. En macOS puedes usar Chrome ya instalado y evitar descargar Chromium. Desde la raíz:

```bash
CAREER_AI_PYTHON="$PWD/.venv/bin/python" \
CAREER_AI_CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
npm --prefix frontend run test:e2e
```

Trazas, videos y capturas están desactivados; las pruebas usan datos ficticios. No ejecutes estos tests con CV personales. CI usa Chromium en Linux y todavía requiere validación en GitHub.
