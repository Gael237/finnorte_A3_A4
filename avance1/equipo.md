# Acuerdos del equipo

> Llénenlo al formar el equipo y actualícenlo en cada entrega. El profesor lo revisa junto con el historial de Git y la coevaluación.

## Datos
| Campo                           | Valor                                                       |
|---------------------------------|-------------------------------------------------------------|
| Equipo                          | Equipo 5                                                    |
| Variante                        | v5-triage                                                   |
| Repositorio                     | https://github.com/AlanGaelQC/finnorte-ia-v5-triage-equipo5 |
| Canal de comunicación           | whatsApp                                                    |
| Horario fijo de trabajo semanal |                                                             |

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
| Flujo (A2) | Cuatro etapas v1 y flujo integrado | `FLUJO_V1` y `FLUJO` en `src/finnorte/variante.py` | 64 passed, 9 skipped en `main` (ejecución local de Alan, 2026-11-05). Faltan matriz de tres incidentes y tres repeticiones reales. |
| Prompts | v1 y v2 por etapa | `FLUJO_V1` usa v1 y `FLUJO` usa v2 en las cuatro etapas | Las versiones y el formato de v2 se verificaron localmente; la mejora de calidad frente a v1 está pendiente de medir con proveedor real. |

## Registro de decisiones importantes
| Fecha | Decisión | Alternativas descartadas | Por qué |
|---|---|---|---|
| 2026-11-05 | Verificar 20 casos y A–D con `fake + hash`, `--rep 1` | Reportar esos porcentajes como calidad del modelo | El script corrió 12 normales, 4 fuera y 4 adversariales sin avisos de error; los valores obtenidos con fake no miden calidad ni consistencia de tres repeticiones. |
| 2026-11-05 | Mantener pendiente la medición con Gemini | Afirmar que la evaluación real pasó | `gemini-3.6-flash` y `gemini-3.5-flash-lite` devolvieron HTTP 503 antes de producir una salida. |
| 2026-11-05 | Usar el buscador vectorial actual frente a BM25 en el conjunto nuevo de 10 preguntas | BM25 para este conjunto | Vector 10/10 @3 y BM25 8/10 @3, con `EMB_PROVIDER=gemini`; falta comparar las propuestas individuales de A1 en condiciones equivalentes. |
