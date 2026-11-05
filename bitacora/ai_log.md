### Jair - Laboratorio 3 y Avance 1 (Severidad y Evaluación)

* **¿Qué hizo la IA?:** Me ayudó a redactar la versión 2 del prompt (`tri_severidad.v2.md`) para que evalúe usando el contexto recuperado (RAG) en lugar de reglas estáticas. También me ayudo a formar de manera correcta los 10 casos faltantes (normales, fuera de dominio y adversariales) para completar los 20 requeridos en `evals/v5-triage.jsonl`. Además, la IA bloqueó mi avance hasta que le demostré con capturas la ejecución real de mis pruebas.
* **¿Qué acepté/cambié?:** Acepté la estructura del prompt con llaves dobles `{{ }}` para el JSON de salida y los 10 casos de prueba. 
* **¿Cómo lo validé personalmente?:** 
  1. Ejecuté `pytest -v` localmente y comprobé que todas mis pruebas de la etapa de severidad pasaron en verde.
  2. Ejecuté manualmente en Google AI Studio el prompt v2, pasándole el catálogo `rb-01` como contexto y las señales extraídas de `inc-01-pool.log`. Verifiqué que el modelo respetó la restricción de elegir el nivel de mayor severidad (eligió SEV1 sobre SEV2) y justificó las limitaciones de los datos faltantes sin romper el formato JSON.
  *Nota: La ejecución de `s3_rag_eval.py` arrojó error intencional (Falta implementar A1) ya que estoy a la espera de que Alan integre el buscador de Gael en `main`.*