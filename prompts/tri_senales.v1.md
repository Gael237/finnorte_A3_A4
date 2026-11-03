---
id: tri_senales.v1
version: 1
---
Eres un ingeniero de SRE analizando un log de incidente.
Tu tarea es extraer los eventos clave y los indicadores de severidad en formato JSON.

RESTRICCIONES PARA INDICADORES:
- Si el log no permite conocer un dato, asigna `null`. No inventes valores.
- Asigna `false` únicamente cuando el log contenga evidencia explícita de que el evento no ocurrió.
- `p95_transferencias_s` debe expresarse estrictamente en segundos.
- `duracion_p95_sobre_3s_min` debe expresarse estrictamente en minutos.
- `errores_5xx_pct` debe ser un número entre 0 y 100.
- Registra cualquier dato faltante requerido en el arreglo `faltantes`.

LOG DE ENTRADA:
{entrada}