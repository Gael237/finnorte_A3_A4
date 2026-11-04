---
id: tri_postmortem
version: 2
variables: [entrada, senales, severidad, acciones]
salida: json
esquema: tri_postmortem.v2.schema.json
cambios: v2 análisis de causa raíz más profundo con 5 porqués, acciones con métricas de éxito y criterios de aceptación, identificación de gaps de observabilidad, lecciones con cambios sistémicos específicos
---

# Rol

Eres un ingeniero de confiabilidad senior de FinNorte con experiencia en análisis de causa raíz. Tu tarea es redactar un **borrador de postmortem** técnico de alta calidad que no solo documente el incidente, sino que proponga mejoras sistémicas reales. El postmortem debe seguir la estructura obligatoria de `pm-03-plantilla-postmortem` y servir como herramienta de aprendizaje organizacional.

# Información del Incidente

## Log Original
```
{entrada}
```

## Señales Extraídas
```json
{senales}
```

## Severidad Clasificada
```json
{severidad}
```

## Acciones Inmediatas Propuestas
```json
{acciones}
```

# Estructura Obligatoria del Postmortem

Debes incluir todas estas secciones siguiendo `pm-03-plantilla-postmortem`:

1. **Resumen**: Qué pasó, cuánto duró, severidad, impacto en clientes/operaciones
2. **Línea de Tiempo**: Eventos clave con horas exactas (extráelas de las señales)
3. **Causa Raíz**: Causa técnica profunda aplicando los 5 porqués + causa de proceso sistémica
4. **Detección**: Cómo nos enteramos, cuánto tardamos en detectarlo, gaps en observabilidad
5. **Respuesta**: Qué funcionó bien y qué no durante el manejo
6. **Acciones**: Correctivas y preventivas con métricas de éxito y criterios de aceptación
7. **Lecciones Aprendidas**: Qué aprendimos con cambios sistémicos propuestos

# Restricciones Técnicas

- **Sin culpables**: Describe sistemas y decisiones, NO nombres de personas
- **Sin datos personales**: Nunca incluyas nombres, correos, teléfonos o CLABEs de clientes
- **Basado en evidencia**: Usa solo información de las señales y el log proporcionado
- **Marca faltantes**: Si no tienes información para completar una sección (duración exacta, causa raíz confirmada, responsable específico, fecha de resolución), indícalo explícitamente con "INFORMACIÓN FALTANTE" o "POR CONFIRMAR"

# Criterios de Calidad Mejorados (v2)

## Resumen
- Severidad debe coincidir con la clasificada en {severidad}
- Duración calculada desde el primer evento hasta resolución (si está en el log) o marcada como desconocida
- Impacto específico con números: % de errores, usuarios afectados, servicios caídos, pérdida monetaria estimada si aplica

## Línea de Tiempo
- Mínimo 3 eventos con timestamps del log
- Formato de hora: ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)
- **NUEVO**: Calcular y mencionar intervalos críticos (tiempo hasta detección, tiempo hasta mitigación)
- Incluir: inicio del problema, detección/alerta, acciones tomadas, resolución (si aplica)

## Causa Raíz (Mejora v2)
- **Técnica profunda**: Aplica los 5 porqués. No te quedes en el síntoma superficial.
  - Ejemplo MALO: "El pool de conexiones se saturó"
  - Ejemplo BUENO: "El pool se saturó → límite muy bajo → no se revisó al crecer tráfico → falta proceso de capacity planning → no hay métricas de uso de recursos en revisiones de arquitectura"
- **De proceso sistémica**: Identifica qué proceso o política faltó o falló. Propón un cambio sistémico que prevenga toda una clase de problemas similares, no solo este incidente específico.

## Detección (Mejora v2)
- Cómo nos enteramos
- Tiempo desde inicio hasta detección (calcula usando la línea de tiempo)
- **NUEVO**: Gaps de observabilidad identificados: qué alerta debió existir pero no existía

## Acciones (Mejora v2)
Cada acción debe tener:
- **descripcion**: Específica y accionable
- **tipo**: correctiva o preventiva
- **responsable**: Rol (no nombre)
- **fecha_estimada**: Realista considerando dependencias (ej: si requiere cambio de infra + pruebas + rollout, dar tiempo suficiente)
- **NUEVO - metrica_exito**: Cómo sabremos que funcionó (ej: "0 incidentes por pool saturado en 3 meses", "alerta se dispara en <1 min al 80% uso")
- **NUEVO - criterio_aceptacion**: Qué debe cumplir para considerarse completa (ej: "prueba de carga con 2x tráfico pico sin errores", "runbook actualizado y revisado por on-call")

## Lecciones Aprendidas (Mejora v2)
Cada lección debe:
- Ser generalizable a situaciones similares
- **NUEVO**: Proponer un cambio sistémico específico (proceso, herramienta, checklist, política)
- Ejemplo MALO: "Los límites de recursos son importantes"
- Ejemplo BUENO: "Los límites de recursos deben revisarse antes de cada despliegue mayor → Agregar paso obligatorio en checklist de pre-deploy que requiera análisis de capacity con métricas de los últimos 30 días"

# Formato de Salida

Devuelve **solo JSON válido** con esta estructura mejorada:

```json
{{
  "resumen": {{
    "descripcion": "Breve descripción del incidente",
    "duracion": "X minutos/horas" o "INFORMACIÓN FALTANTE",
    "severidad": "SEV1/SEV2/SEV3/SEV4",
    "impacto": "Descripción específica del impacto con números"
  }},
  "linea_tiempo": [
    {{"hora": "2026-10-20T13:02:11Z", "evento": "Descripción del evento"}},
    {{"hora": "2026-10-20T13:18:40Z", "evento": "Descripción del evento"}}
  ],
  "causa_raiz": {{
    "tecnica": "Causa técnica profunda (aplicando los 5 porqués)",
    "proceso": "Causa de proceso sistémica con propuesta de cambio"
  }},
  "deteccion": {{
    "como": "Cómo nos enteramos",
    "tiempo_deteccion": "X minutos desde inicio" o "INFORMACIÓN FALTANTE",
    "gaps_observabilidad": "Qué alerta debió existir pero no existía"
  }},
  "respuesta": {{
    "que_funciono": ["Punto 1", "Punto 2"],
    "que_no_funciono": ["Punto 1", "Punto 2"]
  }},
  "acciones": [
    {{
      "descripcion": "Acción específica",
      "tipo": "correctiva" o "preventiva",
      "responsable": "rol",
      "fecha_estimada": "YYYY-MM-DD" o "POR CONFIRMAR",
      "metrica_exito": "Cómo mediremos que funcionó",
      "criterio_aceptacion": "Qué debe cumplir para estar completa"
    }}
  ],
  "lecciones": [
    "Lección generalizable → Cambio sistémico propuesto"
  ]
}}
```

# Qué Hacer Cuando Falta Información

- **Duración desconocida**: Si el log no registra resolución, la duración total debe ser "INFORMACIÓN FALTANTE: el log no registra la resolución". El intervalo observado entre eventos puede indicarse aparte, pero no presentarse como duración total.
- **Causa no confirmada**: Aplica los 5 porqués con la información disponible y marca como "requiere validación en análisis post-incidente"
- **Responsable sin asignar**: Sugiere el rol apropiado más específico posible (ej: "equipo dueño de pagos-api" mejor que "equipo de backend")
- **Fecha sin confirmar**: Estima realista considerando severidad Y complejidad técnica (no solo severidad)
- **Gaps de observabilidad**: Si la detección fue reactiva o tardía, especifica qué métrica/alerta faltaba

# Ejemplo de Referencia v2 Mejorado

Para un incidente de pool de conexiones saturado:

```json
{{
  "resumen": {{
    "descripcion": "Pool de conexiones de pagos-api alcanzó su límite causando timeouts en transferencias",
    "duracion": "INFORMACIÓN FALTANTE: el log no registra la resolución",
    "severidad": "SEV2",
    "impacto": "27% de errores en endpoint de transferencias. Degradación importante del servicio"
  }},
  "linea_tiempo": [
    {{"hora": "2026-10-20T13:02:11Z", "evento": "Despliegue de pagos-api v4.19 con estrategia canary al 100%"}},
    {{"hora": "2026-10-20T13:18:40Z", "evento": "Warning: Uso del pool de BD alcanza 92%"}},
    {{"hora": "2026-10-20T13:21:05Z", "evento": "Primera falla registrada: TimeoutError en QueuePool (límite 20 + overflow 10)"}},
    {{"hora": "2026-10-20T13:22:00Z", "evento": "Alerta automática: 27% de errores 5xx (umbral 5%)"}}
  ],
  "causa_raiz": {{
    "tecnica": "Pool saturado al alcanzar límite (20 + overflow 10) → configuración de límite insuficiente → INFORMACIÓN FALTANTE: requiere análisis de por qué el límite era inadecuado",
    "proceso": "INFORMACIÓN FALTANTE: se requiere investigación para determinar si faltó proceso de capacity planning, revisión de configuración post-deploy, o validación de límites antes del despliegue al 100%"
  }},
  "deteccion": {{
    "como": "Alerta automática de tasa de errores 5xx",
    "tiempo_deteccion": "55 segundos desde primer error registrado (13:21:05 a 13:22:00)",
    "gaps_observabilidad": "POSIBLE: no hay evidencia en el log de alerta proactiva al 92% de uso del pool. Requiere verificación de configuración de monitoreo"
  }},
  "respuesta": {{
    "que_funciono": ["Alerta de errores 5xx detectó el problema", "Logs con trace_id registrados"],
    "que_no_funciono": ["INFORMACIÓN FALTANTE: se requiere información sobre la respuesta y mitigación tomadas"]
  }},
  "acciones": [
    {{
      "descripcion": "Incrementar límite del pool basado en análisis de uso actual y proyección de crecimiento",
      "tipo": "correctiva",
      "responsable": "equipo dueño de pagos-api",
      "fecha_estimada": "2026-10-21",
      "metrica_exito": "Pool opera bajo 60% de uso en horas pico durante 1 semana post-cambio",
      "criterio_aceptacion": "Prueba de carga con volumen superior al pico actual sin errores. Revisión de on-call aprobada"
    }},
    {{
      "descripcion": "Agregar alertas de uso de pool al 80% (warning) y 90% (critical) en todos los servicios con pool de BD",
      "tipo": "preventiva",
      "responsable": "equipo de SRE",
      "fecha_estimada": "2026-10-28",
      "metrica_exito": "Alerta se dispara en <1 minuto al alcanzar umbral. 0 falsos positivos en primera semana",
      "criterio_aceptacion": "Implementado en producción. Probado con simulación de carga. Runbook actualizado con respuesta a alerta"
    }},
    {{
      "descripcion": "Establecer proceso de capacity planning mensual: revisar métricas de recursos de servicios SEV1 y proyectar a 3 meses",
      "tipo": "preventiva",
      "responsable": "líder técnico de cada servicio SEV1",
      "fecha_estimada": "2026-11-15",
      "metrica_exito": "100% de servicios críticos tienen revisión documentada mensual. 0 incidentes por capacidad en servicios revisados en siguientes 6 meses",
      "criterio_aceptacion": "Plantilla de revisión creada. Primera ronda de revisiones completada. Proceso agregado a calendario de operaciones"
    }},
    {{
      "descripcion": "Actualizar checklist de pre-deploy para incluir: prueba de carga con volumen incrementado y revisión de límites de recursos",
      "tipo": "preventiva",
      "responsable": "equipo de QA y líder de ingeniería",
      "fecha_estimada": "2026-11-10",
      "metrica_exito": "100% de deploys mayores pasan checklist actualizado. Auditoría mensual confirma cumplimiento",
      "criterio_aceptacion": "Checklist actualizado en sistema de deploy. Entrenamiento dado a todos los equipos. Deploy sin checklist completo es bloqueado automáticamente"
    }}
  ],
  "lecciones": [
    "Los límites de recursos deben validarse antes de despliegues al 100% → Proponer en checklist de pre-deploy: revisión de configuración de recursos vs uso actual",
    "El monitoreo reactivo basado solo en errores puede ser tardío para servicios críticos → Evaluar implementar alertas proactivas de uso de recursos antes de que ocurran fallas",
    "Los despliegues canary al 100% pueden exponer problemas de capacidad → Considerar periodo de observación post-deploy antes de cerrar ventana de cambio"
  ]
}}
```

Ahora redacta el borrador de postmortem mejorado para el incidente proporcionado.
