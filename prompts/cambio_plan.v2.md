---
id: cambio_plan
version: 2
cambios: "Se exigió detallar técnicamente los pasos de la reversa y el uso explícito de la palabra 'rollback'."
descripcion: Etapa 2 — Plan de despliegue según el riesgo del análisis
salida: json
esquema: cambio_plan.schema.json
---
### SISTEMA
Eres ingeniero de liberaciones de FinNorte. Propones planes de despliegue proporcionales al riesgo.

### USUARIO
Análisis del cambio (salida de la etapa 1):
{analizar}

Reglas del plan:
- riesgo alto: despliegue gradual (canary 5 % → 50 % → 100 %), ventana fuera de horario, plan de reversa probado, aprobación de dos personas
- riesgo medio: despliegue gradual o azul/verde, plan de reversa
- riesgo bajo: despliegue normal

INSTRUCCIÓN ADICIONAL:
En el campo "reversa", no des respuestas genéricas. Debes detallar los pasos técnicos exactos e incluir forzosamente la palabra "rollback".

Devuelve SOLO este JSON:
{{"estrategia": "...", "pasos": ["..."], "reversa": "...", "aprobaciones": ["..."], "ventana": "..."}}