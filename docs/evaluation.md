# Evaluar con datos reales

El conjunto incluido es sintético: sirve para detectar regresiones, no para anunciar precisión real. No se han recopilado vacantes de internet ni CV privados. La procedencia y el permiso deben quedar documentados por quien aporta los datos.

## Preparar el corpus

1. Guarda >=3 CV anonimizados y 20–30 vacantes que tengas permiso de usar en `private/benchmark/`. Evita nombres, contactos, fotos, empresas identificables y otros datos personales. No subas el directorio al repositorio; `.gitignore` también excluye PDF/DOCX.
2. Incluye variedad: PDF con texto, DOCX, tablas, idiomas, títulos explícitos, negaciones y habilidades poco frecuentes. Guarda algunos documentos problemáticos para medir errores; no mezcles fallos de lectura con aciertos semánticos.
3. Anota manualmente habilidades que aparecen afirmativamente en cada texto. Usa etiquetas canónicas en minúsculas; incluye habilidades fuera del diccionario para contabilizar sus omisiones. Una mención negada no es una habilidad afirmativa. No infieras competencias que no aparecen.
4. Para vacantes, etiqueta cada habilidad como `required`, `desirable` o `unspecified` según evidencia explícita. Marca ambigüedades para revisión humana; no fuerces un requisito cuando el texto no lo sostiene.
5. Etiqueta >=20 pares CV–vacante con coincidencias esperadas y habilidades de la vacante sin evidencia en el CV. No generar automáticamente el gold con el extractor que estás evaluando. Otra persona debe revisar una muestra y resolver desacuerdos.
6. Separa un conjunto para desarrollar reglas de otro reservado para validación. No ajustes el diccionario mirando los errores del conjunto reservado y luego anuncies su puntuación como independiente. Conserva versión, fecha de anotación y criterio de etiquetado.

## Contrato de dataset

Ejemplo **sintético** del formato; `file` es relativo al directorio del dataset y puede sustituirse por `text`, nunca ambos:

```json
{
  "schema_version": "1.0",
  "dataset_id": "synthetic_example_v1",
  "cases": [
    {"case_id": "cv_001", "kind": "cv", "file": "cv_001.docx",
     "expected_skills": ["python"], "source": {"type": "synthetic"}},
    {"case_id": "job_001", "kind": "vacancy", "text": "Python required. Docker preferred.",
     "expected_skills": ["python", "docker"],
     "expected_requirements": {"python": "required", "docker": "desirable"},
     "source": {"type": "synthetic"}}
  ],
  "comparisons": [
    {"comparison_id": "pair_001", "cv_id": "cv_001", "vacancy_id": "job_001",
     "expected_matched": ["python"], "expected_missing": ["docker"]}
  ]
}
```

Para cada caso real, `source` debe contener `type: "real"`, `permission: "authorized"`, `reference` y `captured_at` (fecha ISO, por ejemplo `2026-10-08`). Registra allí la URL o referencia privada y el fundamento del permiso; conserva la prueba aparte. Declarar `authorized` no concede permisos ni anonimiza el contenido. Usa IDs impersonales. Una comparación debe etiquetar todas las habilidades del gold de su vacante.

Puedes añadir metadatos de anotación/split al dataset; el reporte incorpora el hash del JSON completo. Para archivos, ese hash no cubre sus bytes: si cambias un documento, crea una nueva versión de dataset y conserva su checksum en metadatos privados. El evaluador comprueba rutas confinadas al directorio del corpus, contratos, fuentes y etiquetas; no valida el contenido jurídico del permiso.

## Ejecutar y leer resultados

```bash
python -m career_ai.evaluation private/benchmark/holdout.json \
  --require-real --output out/evaluation-report-real.json \
  --min-precision 0.90 --min-recall 0.85 \
  --min-match-exact 0.80 --min-requirement-accuracy 0.85 --max-errors 0
```

Esos umbrales son criterios iniciales propuestos, **no resultados obtenidos**. Decláralos antes de evaluar. `--require-real` exige >=20 vacantes, >=3 CV y >=20 pares, sin casos sintéticos. Si el contrato es inválido, sale con código 2; si no supera los umbrales, conserva el reporte y sale con código 1; si cumple, código 0.

| Métrica | Qué mide |
| --- | --- |
| Precision | Habilidades detectadas correctamente / todas las detectadas |
| Recall | Habilidades detectadas correctamente / todas las etiquetadas |
| F1 | Balance entre precision y recall |
| Requirement accuracy | Habilidades gold con clasificación correcta / habilidades gold etiquetadas; incluye omisiones como error |
| Matching exact match rate | Pares con conjuntos de coincidencias y faltantes completamente correctos / todos los pares |
| Error count | Archivos ilegibles, timeout, límites, datos no válidos; pares afectados se cuentan aparte |
| Latencia p50/p95 | Duración por caso para lectura + extracción cuando hay archivo; por par para comparación sobre texto |

Precision/recall se agregan por habilidades y se desglosan por CV/vacante. No son una probabilidad de contratación. Si un denominador es cero, el resultado es `null`, no un acierto artificial. Un archivo que falla aporta sus habilidades gold a las omisiones; no se elimina del denominador para mejorar recall. Pares sin texto disponible cuentan como fallos y coincidencias omitidas.

El reporte registra `omitted`, `incorrect`, errores de clasificación, coincidencias incorrectas/omitidas y errores de lectura por ID. No contiene fragmentos, contactos, rutas ni URLs. Las etiquetas e IDs deben ser anónimos; también es un artefacto privado. La latencia del CLI no incluye navegador, HTTP ni revisión humana; los logs de la API miden solicitudes. Un corpus de 20–30 vacantes produce resultados exploratorios, no garantiza calidad sobre todas las profesiones.

Publica únicamente un resumen agregado autorizado: tamaño/composición del corpus, versiones, política de anotación, separación desarrollo/validación, métricas, errores frecuentes y límites. Guarda capturas de demo con documentos ficticios. No anuncies cifras del smoke sintético como validación real.
