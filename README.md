# Career Intelligence AI

MVP local para comparar un CV con una vacante y explicar las coincidencias con evidencia. Un flujo pequeño, medible y operable: ingestión limitada, extracción determinista, revisión humana, contratos versionados y evaluación con etiquetas manuales.

## Ejecutar la interfaz local

Python 3.11+ y Node.js 24 LTS. Desde esta carpeta:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -c requirements.lock -e '.[api,test]'
npm --prefix frontend ci
npm --prefix frontend run build
uvicorn career_ai.api:app --host 127.0.0.1 --port 8000 --no-access-log --log-config logging.json
```

Abre **http://127.0.0.1:8000**. Carga un PDF/DOCX o pega el texto del CV, corrige la extracción, desmarca habilidades que no te representen y confirma la revisión. Pega la vacante y compara. La pantalla separa requisitos obligatorios, deseables y menciones sin clasificación; muestra fragmentos de ambos textos y experiencia que puedes destacar. Si editas el CV, debes actualizar la extracción y revisarlo otra vez.

No se guarda el CV ni el perfil. **Borrar sesión** limpia la página y cancela solicitudes pendientes. Sin autenticación: solo uso local. No publiques la API abierta en internet. El parser no hace OCR; un PDF escaneado requiere conversión local o pegar su texto.

## Frontend: React 19 + TypeScript + Tailwind CSS 4

SPA compilada con Vite 8, organizada por funcionalidades. `frontend/src/app` compone la aplicación; `features/comparison` contiene los componentes del flujo, su estado y contratos; `shared` contiene el cliente HTTP y los componentes reutilizables. TypeScript estricto, respuestas validadas con Zod y estado efímero con `useReducer`. La [arquitectura del frontend](docs/frontend.md) explica responsabilidades, pruebas y criterios para crecer.

Para desarrollar, deja FastAPI en la primera terminal y ejecuta `npm --prefix frontend run dev` en otra. Abre **http://127.0.0.1:5173**. Vite ofrece recarga de componentes y un proxy local a la API; no se amplía CORS en el backend. El build genera `career_ai/static/`, que FastAPI sirve en el puerto 8000. Ese directorio es generado y está ignorado: recompila después de cambiar el frontend. La API funciona sin build; `/` devuelve 503 con instrucciones si falta.

## Validar

```bash
npm --prefix frontend run lint
npm --prefix frontend test
npm --prefix frontend run build
python -m unittest discover -s tests -v
python -m career_ai.evaluation data/evaluation_smoke.json \
  --min-precision 1 --min-recall 1 --min-match-exact 1 \
  --min-requirement-accuracy 1 --max-errors 0
```

El reporte se escribe en `out/evaluation-report.json`. El conjunto incluido contiene **8 casos sintéticos y 3 comparaciones**; solo comprueba regresiones. No demuestra calidad sobre CV o vacantes reales. Para esa validación, usa >=3 CV anonimizados, 20–30 vacantes autorizadas y >=20 comparaciones etiquetadas en `private/`. Consulta [el protocolo de evaluación](docs/evaluation.md).

Las pruebas cubren contratos, offsets de evidencia, revisión, negaciones simples, documentos vacíos/cifrados/dañados, límites, archivos ZIP expandidos, timeout, origen/host y logs sin texto personal. El frontend añade pruebas de flujo, estado, errores de contrato y cancelación. Playwright verifica el flujo real contra FastAPI y la vista móvil; consulta [cómo ejecutarlo](docs/frontend.md). CI configura Node 24, pruebas frontend, build, Python 3.11/3.14 y pruebas de navegador; todavía no se ha ejecutado en GitHub. `frontend/package-lock.json` fija las dependencias npm; `requirements.lock` fija las versiones Python probadas localmente, sin hashes.

## Contratos HTTP

| Endpoint | Entrada | Resultado |
| --- | --- | --- |
| `GET /health` | — | Estado y versiones del extractor/diccionario |
| `POST /documents/extract` | Bytes originales; header `X-Document-Format: pdf` o `docx` | Texto, habilidades, evidencia y advertencias |
| `POST /profile/review` | JSON: `text` | Extracción del texto corregido |
| `POST /compare` | JSON: `cv_text`, `vacancy_text`, `selected_skills` opcional | Evidencia, grupos de cobertura y experiencia relevante |
| `POST /analyze` | JSON: `jobs`, `profile_skills` | Pipeline original de vacantes; solo menciones de palabras clave |

En `/compare`, omitir `selected_skills` usa las habilidades detectadas; `[]` no selecciona ninguna. Solo se permiten habilidades presentes en el texto revisado. Los fragmentos del CV provienen de ese texto corregido, no constituyen verificación del documento original. Los esquemas están en `/openapi.json`; la interfaz no necesita Swagger ni servicios externos.

## Operación y límites

- PDF/DOCX: 5 MiB, hasta 40 páginas PDF y 100.000 caracteres extraídos; lectura aislada con timeout de 12 segundos y hasta dos lectores simultáneos por proceso de API. ZIP: hasta 20 MiB expandidos y 1.000 entradas. Solicitudes HTTP: hasta 6 MiB, incluso sin `Content-Length`.
- Logs JSON: ruta del contrato, método, status y duración; sin cuerpos, nombres de archivos ni query strings. Usa el comando indicado para desactivar access logs y activar esta configuración.
- Las reglas reconocen un diccionario de tecnologías y títulos explícitos en español/inglés. Años, dominio, inglés, seniority, requisitos desconocidos, alternativas y negaciones complejas requieren revisión manual. Las menciones son evidencia textual, no prueba de competencia.
- Cobertura = habilidades reconocidas y seleccionadas / habilidades reconocidas en cada grupo de la vacante. Sin habilidades reconocidas devuelve `null`. **No es una probabilidad de contratación.**
- Solo se incluyen ejemplos ficticios. `private/`, PDF, DOCX, `.env` y reportes están ignorados; no copies CV ni datos personales a archivos del código. La evaluación offline sí lee un corpus que guardas tú y genera un reporte privado. Revisa también IDs y etiquetas para evitar información personal.

La limpieza libera referencias de la aplicación; no garantiza borrado forense de RAM, swap, copias del navegador o archivos originales en tu disco. Para detalles de privacidad, límites y decisiones, consulta [la arquitectura](docs/architecture.md).

## Pipeline anterior y cloud

El CLI original sigue disponible sin dependencias externas: `python3 -m career_ai.cli` escribe `out/analysis.json` con vacantes/perfil ficticios. Para usarlo con datos reales, apunta `--input` y `--profile` a `private/`; no reemplaces los ejemplos del repositorio con información personal.

Databricks queda como prototipo posterior de analítica agregada sobre vacantes, separado de los CV privados. [Instrucciones del notebook](databricks/README.md). No hay integración cloud, RAG, agente ni persistencia de usuarios implementados.

Docker opcional: `docker build -t career-ai .` y `docker run --rm -p 127.0.0.1:8000:8000 career-ai`. No se ha validado el contenedor en este entorno.
