# Bitácora de uso de IA

> Obligatoria en todas las entregas. Una fila por uso relevante de una herramienta de IA (chat, asistente de código, generador).
> La IA es una herramienta permitida; ocultarla no lo es. Se califica la honestidad y la calidad de la validación, no si la usaste.

| Fecha | Entrega | Herramienta y modelo | Para qué la usé | Prompt (resumen o enlace) | Qué acepté | Qué cambié o rechacé y por qué | Cómo lo validé |
|---|---|---|---|---|---|---|---|
| 2026-10-16 | A1 | Ejemplo: asistente de código | Ejemplo: generar el esqueleto de la función de normalización | "Escribe una función en numpy que…" | La estructura del ciclo | Usaba `/` sin cuidar la norma cero; lo corregí | Prueba `test_normalizar_vector_cero` |
| 2026-11-03 | A2 | Kiro (Claude Sonnet 4.5) | Generar etapa tri_postmortem: prompt v1, esquema JSON y validación en código | "Crear archivos para etapa 4 de triage según LAB2 y pm-03" | Estructura del esquema JSON, prompt base, validaciones de PII y consistencia | Ajusté criterios de validación: agregué detección de acciones genéricas y balance correctivas/preventivas; mejoré ejemplos en el prompt | Esquema valida con jsonschema, validación detecta patrones PII |
| 2026-11-03 | A2 | Kiro (Claude Sonnet 4.5) | Crear script guia/a2_flujo_variante.py para matriz de trazabilidad | "Crear script basado en s2_flujo_cambios.py para v5-triage con 4 etapas y medición de consistencia" | Estructura general del script, formato de matriz en Markdown | Adapté nombres de etapas según reparto del equipo, agregué medición de consistencia con 3 repeticiones, formato de salida legible | Ejecutaré tras integración del flujo completo |
