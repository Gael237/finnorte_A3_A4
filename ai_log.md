# Bitácora de uso de IA

> Obligatoria en todas las entregas. Una fila por uso relevante de una herramienta de IA (chat, asistente de código, generador).
> La IA es una herramienta permitida; ocultarla no lo es. Se califica la honestidad y la calidad de la validación, no si la usaste.

| Fecha | Entrega | Herramienta y modelo | Para qué la usé | Prompt (resumen o enlace) | Qué acepté | Qué cambié o rechacé y por qué | Cómo lo validé |
|---|---|---|---|---|---|---|---|
| 2026-10-16 | A1 | Ejemplo: asistente de código | Ejemplo: generar el esqueleto de la función de normalización | "Escribe una función en numpy que…" | La estructura del ciclo | Usaba `/` sin cuidar la norma cero; lo corregí | Prueba `test_normalizar_vector_cero` |

| 2026-11-03 | LAB 2 — tri_severidad | ChatGPT Codex (GPT-6) | Proponer el prompt v1, esquema JSON, regla de severidad y pruebas | “Ayúdame a implementar mi etapa según rb-01 y el formato del proyecto” | Prompt, esquema, validador y pruebas | Corregí la posición del import tras un SyntaxError; dejé FLUJO vacío hasta integrar las otras etapas | El prompt y esquema cargaron; py_compile no dio errores; 13 pruebas locales pasaron |