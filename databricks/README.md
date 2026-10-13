# Ejecutar en Databricks
1. Crea o selecciona un workspace. Confirma acceso a compute, Unity Catalog y permisos CREATE SCHEMA/SELECT/MODIFY. No se ha conectado ninguna cuenta desde este proyecto.
2. Usa exclusivamente un catálogo/esquema de desarrollo: el notebook reemplaza snapshots en cada ejecución.
3. Crea un Volume desde Catalog Explorer y sube `data/sample_jobs.json`.
4. Construye el wheel: `python -m pip wheel . --no-deps -w dist`. Instala el wheel en el compute compatible.
5. Importa `01_medallion.py` como notebook. Rellena catalog, schema e input_path (ruta /Volumes/...). Ejecuta las celdas.
6. Verifica bronze_jobs, quarantine_jobs, silver_jobs y gold_skill_demand. Guarda los resultados y la captura del run.

Esto es un notebook inicial, no un despliegue validado. El siguiente incremento unificará IDs entre Spark y Python, incorporará MERGE incremental, pruebas Spark y un Job versionado mediante bundles. Los requisitos de compute/costos deben verificarse en tu cuenta antes de ejecutarlo.
