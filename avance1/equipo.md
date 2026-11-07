# Acuerdos del equipo

> Llénenlo al formar el equipo y actualícenlo en cada entrega. El profesor lo revisa junto con el historial de Git y la coevaluación.

## Datos
| Campo                           | Valor                                                       |
|---------------------------------|-------------------------------------------------------------|
| Equipo                          | Equipo 5                                                    |
| Variante                        | v5-triage                                                   |
| Repositorio                     | https://github.com/AlanGaelQC/finnorte-ia-v5-triage-equipo5 |
| Canal de comunicación           | whatsApp                                                    |
| Horario fijo de trabajo semanal | Sin horario fijo documentado                               |

## Integrantes y roles
Los roles **rotan en cada entrega**; todos programan.

|          Integrante            | Usuario de GitHub |      Rol Avance 1                                | Rol Avance 2 | Rol Final |
|--------------------------------|-------------------|--------------------------------------------------|--------------|-----------|
| Alan Gael Quintanilla Clemente |    AlanGaelQC     | Integración (`sistema()`, fusión de ramas)       |              |           |
| Jair Emmanuel Rivera Cano      |   JairRivera14    | Evaluación (casos, contrato, configuraciones A–D)|              |           |
| Gael Aaron Aguirre Mendez      |     Gael237       | Prompts y flujo (v1/v2, esquemas, reglas)        |              |           |
| Axel Ivan Isaak De La Paz      |    axlisaak       | Documento y evidencia (PDF, bitácoras)           |              |           |

## Dueños de etapa del flujo (A2 · individual)
Cada integrante es dueño de **una** etapa: su prompt v1 y esquema, su validación en código (`validar=`) y su v2 medida.

| Etapa | Nombre en `FLUJO` | Prompt (`prompts/<id>.v1.md`) | Dueño (integrante) | Usuario de GitHub |
|---|---|---|---|---|
| 1 | `senales` | `tri_senales` | Gael Aaron Aguirre Mendez | Gael237 |
| 2 | `severidad` | `tri_severidad` | Jair Emmanuel Rivera Cano | JairRivera14 |
| 3 | `acciones` | `tri_acciones` | Alan Gael Quintanilla Clemente | AlanGaelQC |
| 4 | `postmortem` | `tri_postmortem` | Axel Ivan Isaak De La Paz | axlisaak |

## Reglas de trabajo
- Nadie sube directo a `main`: rama → pull request → una aprobación → fusionar.
- Cada pull request dice qué cambió y cómo se probó.
- Las llaves van en `.env`, nunca en el repositorio. Si se filtra una, se revoca en menos de 1 hora (ing-02).
- Si alguien no puede cumplir, lo avisa **antes** de la fecha, no después.

## Decisión de fusión (Avance 1)
| Pieza | Opciones (de quién) | Elegida | Evidencia que la justifica |
|---|---|---|---|
| Buscador (A1) | Índice vectorial actual y BM25 del repositorio | Índice vectorial integrado en `src/finnorte/retrieval.py` | En 10 preguntas nuevas del corpus v5-triage con embeddings Gemini, vector: acierto@1 10/10 y @3 10/10; BM25: @1 7/10 y @3 8/10 (`bitacora/a1_comparacion.json`). Esta comparación no sustituye las métricas individuales de los demás integrantes. |
| Flujo (A2) | Cuatro etapas v1 y flujo integrado | `FLUJO_V1` y `FLUJO` en `src/finnorte/variante.py` | 64 passed, 9 skipped en `main` (ejecución local de Alan, 2026-11-05). La matriz real A2 de 2026-11-06 documenta tres incidentes: 2/3 flujos válidos. En tres repeticiones de inc-01, 1/3 flujos completos válidos; la etapa acciones pasó 3/3 como validación técnica (`bitacora/a2_matriz_haiku55_revalidada_20261106.json`). |
| Prompts | v1 y v2 por etapa | `FLUJO_V1` usa v1 y `FLUJO` usa v2 en las cuatro etapas | A–D reales: B−A en exactitud +0.00; no se demostró mejora agregada atribuible a v2. La comparación aislada de acciones 1×1 (`bitacora/a2_acciones_v1_v2_1x1_20261106.json`) no prueba mejora general. |

## Registro de decisiones importantes
| Fecha | Decisión | Alternativas descartadas | Por qué |
|---|---|---|---|
| 2026-11-05 | Verificar 20 casos y A–D con `fake + hash`, `--rep 1` | Reportar esos porcentajes como calidad del modelo | El script corrió 12 normales, 4 fuera y 4 adversariales sin avisos de error; los valores obtenidos con fake no miden calidad ni consistencia de tres repeticiones. |
| 2026-11-05 | Mantener pendiente la medición con Gemini | Afirmar que la evaluación real pasó | `gemini-3.6-flash` y `gemini-3.5-flash-lite` devolvieron HTTP 503 antes de producir una salida. |
| 2026-11-05 | Usar el buscador vectorial actual frente a BM25 en el conjunto nuevo de 10 preguntas | BM25 para este conjunto | Con Gemini, vector 10/10 @3 y BM25 8/10 @3; con embeddings locales, vector 10/10 @3 y BM25 8/10 @3. Ambos usan 10 preguntas; esta comparación no demuestra un beneficio A–D. |

## Mediciones adicionales de A1 y calibración del umbral

- En las 10 preguntas existentes, con embeddings Gemini: vector obtuvo acierto@1 de 10/10 y acierto@3 de 10/10; BM25 obtuvo acierto@1 de 7/10 y acierto@3 de 8/10. Evidencia versionada: `bitacora/a1_comparacion.json`.
- Calibración RAG limitada a dos casos: `t01=0.5651` y `t09=0.3339`, con umbral `0.35`. Esta muestra pequeña no constituye una calibración general.
- Actualización 2026-11-06: `bitacora/av1_A.json` a `av1_D.json` son los reportes reales de A–D, con 20 casos y 3 repeticiones (60 ejecuciones por configuración); las trazas de la corrida local registraron Anthropic Claude Haiku 5.5. La corrida `fake` queda excluida de estas mediciones. Los JSON A–D no guardan proveedor/modelo de embeddings; la configuración local declarada para esa corrida no puede verificarse solo desde los reportes.

## Evaluación real del Avance 1 (2026-11-06)

- Configuración efectiva de la corrida: Anthropic Claude Haiku 5.5 para respuestas y embeddings locales `paraphrase-multilingual-MiniLM-L12-v2` según entorno de ejecución; los JSON A–D no almacenan esos metadatos completos.
- 20 casos × 3 repeticiones por configuración: exactitud A=.3500, B=.3500, C=.4833 y D=.4833; ninguna cumple todas las metas de `contrato_calidad.yaml`.
- Diferencias: C−B +.13 (IC 95 % .05–.2167); D−C +.00 (IC 95 % −.0833–.0833). No atribuir mejora a controles ni a una etapa individual.
- Consistencia por tipo de acierto A/B: normales 12/12, fuera 4/4, adversariales 4/4; C: 8/12, 4/4, 4/4; D: 9/12, 4/4, 4/4. Casos variables: C t01/t04/t05/t08; D t04/t05/t08.
- Limitación de confidencialidad: `filtrar_clasificacion` y `sanear_salida` siguen pendientes para Avance 2; `opcional` devuelve las entradas originales. PII=0 en la salida medida no garantiza que el contexto enviado al modelo carezca de datos sensibles.
