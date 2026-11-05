"""Guía A2 · Flujo de 4 etapas variante v5-triage: logs → señales → severidad → acciones → postmortem.

    python guia/a2_flujo_variante.py                    # con tu proveedor (.env)
    python guia/a2_flujo_variante.py --version 1        # fija la versión de los prompts (para comparar v1 vs v2)
    LLM_PROVIDER=fake python guia/a2_flujo_variante.py  # sin red: no disponible para esta variante

Qué hace:
  1. Ejecuta el flujo completo con 3 logs de incidentes (pool, TLS, SPEI timeout).
  2. Valida cada salida contra su esquema JSON y reglas de negocio (y reintenta si falla).
  3. Genera la matriz de trazabilidad: entrada → etapa → prompt → validación → intentos → errores → artefacto.
  4. Repite el primer log tres veces; compara severidad y JSON completo de postmortem.
  5. Guarda entradas, contexto filtrado, versiones/hash de prompts, salidas, intentos,
     errores, latencia y costo en bitacora/a2_matriz_vN.{md,json}.

La asignación original de etapas consta en avance1/equipo.md. Esta revisión de
auditabilidad fue hecha con ChatGPT Codex a petición de Alan; revisión final pendiente.
"""
import json
import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def _aviso_pendiente(tipo, valor, tb):
    """Si falta implementar una función, muestra un aviso claro en lugar del error largo."""
    if issubclass(tipo, NotImplementedError):
        print(f"\n✗ Falta implementar: {valor}.\n  Revisa el manual del LAB 2 y ejecuta pytest -q antes de este script.")
        return
    sys.__excepthook__(tipo, valor, tb)


sys.excepthook = _aviso_pendiente

from finnorte.config import config, RAIZ
from finnorte import llm, pii, prompts as _prompts
from finnorte.retrieval import _BM25, cargar_corpus, fragmentar
# Importar el flujo del equipo definido en variante.py
from finnorte.variante import FLUJO, FLUJO_V1


def _version_de(prompt_usado: str):
    """Extrae el número de versión del prompt usado."""
    import re as _re
    m = _re.search(r"\.v(\d+)", prompt_usado)
    vs = _prompts.versiones(prompt_usado.split(".")[0])
    return int(m.group(1)) if m else (max(vs) if vs else 1)


def _contexto_relevante(texto: str):
    """Aplica el BM25 del proyecto sin inicializar el índice vectorial A1."""
    documentos = cargar_corpus(RAIZ / "corpus" / "v5-triage")
    fragmentos = [fragmento for doc in documentos for fragmento in fragmentar(doc)]
    bm25 = _BM25([fragmento.texto for fragmento in fragmentos])
    puntajes = bm25.puntajes(texto)
    ordenados = sorted(range(len(puntajes)), key=lambda i: -puntajes[i])[:8]
    bloques = []
    fuentes = []
    caracteres = 0
    for indice_fragmento in ordenados:
        puntaje = puntajes[indice_fragmento]
        if puntaje <= 0:
            continue
        fragmento = fragmentos[indice_fragmento]
        lineas_seguras = []
        for linea in fragmento.texto.splitlines():
            if (
                re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", linea)
                or re.search(r"\b\d{2}\s+\d{4}\s+\d{4}\b", linea)
                or re.search(r"cliente afectado", linea, re.IGNORECASE)
            ):
                continue
            lineas_seguras.append(linea)
        texto_seguro = "\n".join(lineas_seguras).strip()
        if not texto_seguro:
            continue
        bloque = f"[doc:{fragmento.id}] {fragmento.titulo}\n{texto_seguro}"
        if caracteres + len(bloque) > 4000:
            break
        bloques.append(bloque)
        caracteres += len(bloque)
        fuentes.append({"id": fragmento.id, "puntaje": round(puntaje, 6)})
    return "\n\n".join(bloques), fuentes


def _salida_auditable(salida):
    """Conserva JSON completo salvo que contenga PII detectable; nunca guarda el dato."""
    try:
        texto = json.dumps(salida, ensure_ascii=False)
    except (TypeError, ValueError):
        return None, True
    if pii.contiene_pii(texto):
        return None, True
    return salida, False


def _sha256_prompt(prompt_usado: str) -> str:
    version = _version_de(prompt_usado)
    ruta = _prompts.CARPETA / f"{prompt_usado.split('.')[0]}.v{version}.md"
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def _ejecutar_trazable(flujo, entrada):
    """Registra intentos del proveedor sin guardar credenciales ni el prompt completo."""
    llamadas = []
    generar_original = llm.generar

    def generar_registrando(*args, **kwargs):
        try:
            respuesta = generar_original(*args, **kwargs)
        except Exception as exc:
            llamadas.append({
                "etiqueta": kwargs.get("etiqueta", ""),
                "error": str(exc),
                "intentos_proveedor_configurados_max": config().reintentos + 1,
            })
            raise
        salida, salida_omitida_pii = _salida_auditable(respuesta.datos)
        llamadas.append({
            "etiqueta": kwargs.get("etiqueta", ""),
            "proveedor": respuesta.proveedor,
            "modelo": respuesta.modelo,
            "intentos_proveedor": respuesta.intentos,
            "tokens_entrada": respuesta.tokens_entrada,
            "tokens_salida": respuesta.tokens_salida,
            "latencia_ms": respuesta.latencia_ms,
            "costo_usd": respuesta.costo_usd,
            "salida_json": salida,
            "salida_omitida_por_pii": salida_omitida_pii,
        })
        return respuesta

    llm.generar = generar_registrando
    try:
        resultado = flujo.ejecutar(entrada)
    except Exception as exc:
        exc.llamadas_llm = llamadas
        raise
    finally:
        llm.generar = generar_original
    return resultado, llamadas


def _corrida_auditable(res, llamadas, inc_id, ruta_log, log_texto, contexto, fuentes_contexto, tipo):
    return {
        "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tipo": tipo,
        "incidente": inc_id,
        "archivo_entrada": ruta_log,
        "entrada_log": log_texto,
        "entrada_sha256": hashlib.sha256(log_texto.encode("utf-8")).hexdigest(),
        "contexto": contexto,
        "fuentes_contexto": fuentes_contexto,
        "ok": res.ok,
        "costo_usd": res.costo_usd,
        "latencia_ms": res.latencia_ms,
        "llamadas_llm": llamadas,
        "etapas": [
            {
                "nombre": e.nombre,
                "prompt": e.prompt,
                "prompt_sha256": _sha256_prompt(e.prompt),
                "valida": e.ok,
                "intentos": e.intentos,
                "errores": e.errores,
                "latencia_ms": e.latencia_ms,
                "costo_usd": e.costo_usd,
                "salida": _salida_auditable(e.salida)[0],
                "salida_omitida_por_pii": _salida_auditable(e.salida)[1],
            }
            for e in res.etapas
        ],
    }


import argparse

_ap = argparse.ArgumentParser(description="Guía A2 · flujo de triage de incidentes v5")
_ap.add_argument("--version", type=int, default=None,
                 help="versión de los prompts (1 para v1, 2 o None para la más reciente)")
_ap.add_argument("--salida", default=None,
                 help="nombre del archivo en bitacora/ (por defecto a2_matriz_vN)")
_args = _ap.parse_args()

# Determinar qué flujo usar y verificar que exista
flujo_a_usar = None
version_solicitada = None

if _args.version == 1:
    if not FLUJO_V1 or not FLUJO_V1.etapas:
        print(f"\n✗ Error: Se solicitó --version 1 pero FLUJO_V1 no está definido en variante.py")
        print(f"  Alan debe definir FLUJO_V1 con las 4 etapas en versión 1 de los prompts")
        exit(1)
    flujo_a_usar = FLUJO_V1
    version_solicitada = 1
else:
    flujo_a_usar = FLUJO
    # Detectar la versión real del flujo usado
    version_solicitada = None  # Se calculará después de la primera ejecución

# Los 3 logs de incidentes para la matriz
LOGS_ENTRADA = {
    "inc-01-pool": "datos/v5-triage/logs/inc-01-pool.log",
    "inc-02-tls": "datos/v5-triage/logs/inc-02-tls.log",
    "inc-03-spei": "datos/v5-triage/logs/inc-03-spei-timeout.log",
}

print(f"{'='*70}")
print(f"  Flujo de Triage v5 - Equipo 5")
print(f"  Proveedor: {config().llm_proveedor}/{config().llm_modelo}")
if version_solicitada:
    print(f"  Usando flujo: FLUJO_V{version_solicitada}")
else:
    print(f"  Usando flujo: FLUJO (versión más reciente)")
print(f"{'='*70}\n")

if not flujo_a_usar.etapas:
    print("✗ Error: El flujo está vacío. Alan debe integrar las 4 etapas en variante.py")
    print("  Necesita definir FLUJO con las etapas: senales, severidad, acciones, postmortem")
    exit(1)

matriz = []
corridas = []
resultados_completos = {}
versiones_reales_usadas = set()
cuota_agotada = False

for inc_id, ruta_log in LOGS_ENTRADA.items():
    # Leer el log
    log_path = RAIZ / ruta_log
    if not log_path.exists():
        print(f"\n✗ No se encontró {ruta_log}")
        continue

    log_texto = log_path.read_text(encoding="utf-8")
    contexto, fuentes_contexto = _contexto_relevante(log_texto)

    if cuota_agotada:
        motivo = "Omitida: el proveedor agotó cuota en una corrida previa"
        corridas.append({
            "tipo": "matriz", "incidente": inc_id, "archivo_entrada": ruta_log,
            "entrada_log": log_texto,
            "entrada_sha256": hashlib.sha256(log_texto.encode("utf-8")).hexdigest(),
            "contexto": contexto, "fuentes_contexto": fuentes_contexto,
            "ok": False, "omitida": True, "error_general": motivo, "etapas": [],
            "llamadas_llm": [],
        })
        matriz.append({
            "corrida_id": f"matriz-{inc_id}", "tipo_corrida": "matriz",
            "entrada": inc_id, "etapa": "NO_EJECUTADA", "prompt": "N/A",
            "version": None, "valida": False, "intentos": 0,
            "errores": [motivo], "artefacto": None,
        })
        print(f"\n{inc_id}: {motivo}")
        continue

    print(f"\n{'─'*70}")
    print(f"📋 {inc_id}: {ruta_log}")
    print(f"{'─'*70}")

    # Ejecutar el flujo
    try:
        res, llamadas = _ejecutar_trazable(
            flujo_a_usar, {"entrada": log_texto, "contexto": contexto}
        )
        resultados_completos[inc_id] = res
        corrida_id = f"matriz-{inc_id}"
        corridas.append(_corrida_auditable(
            res, llamadas, inc_id, ruta_log, log_texto, contexto, fuentes_contexto, "matriz"
        ))

        estado = "✓ OK" if res.ok else "✗ FALLÓ"
        print(f"\n{estado} · US${res.costo_usd:.5f} · {res.latencia_ms:.0f} ms\n")

        # Registrar cada etapa en la matriz
        for e in res.etapas:
            estado_etapa = "✓" if e.ok else "✗"
            errores_resumidos = "; ".join(e.errores[:2]) if e.errores else ""

            print(f"  {estado_etapa} {e.nombre:12s} {e.prompt:25s} "
                  f"intentos={e.intentos:1d} "
                  f"{errores_resumidos[:60]}")
            if e.nombre == "severidad" and not e.ok:
                print("  Salida candidata de severidad (omitiendo datos personales):")
                print(json.dumps(_salida_auditable(e.salida)[0], ensure_ascii=False, indent=2))
                print("  Errores exactos de la etapa:")
                print(json.dumps(e.errores, ensure_ascii=False, indent=2))

            version_etapa = _version_de(e.prompt)
            versiones_reales_usadas.add(version_etapa)

            # Guardar la salida completa como JSON para auditoría
            salida_json, salida_omitida_pii = _salida_auditable(e.salida)

            matriz.append({
                "corrida_id": corrida_id,
                "tipo_corrida": "matriz",
                "entrada": inc_id,
                "fuentes_contexto": fuentes_contexto,
                "etapa": e.nombre,
                "prompt": e.prompt,
                "version": version_etapa,
                "valida": e.ok,
                "intentos": e.intentos,
                "errores": e.errores,
                "artefacto": salida_json,
                "artefacto_omitido_por_pii": salida_omitida_pii,
            })

        # Mostrar resultado clave: la severidad clasificada
        if res.ok and "severidad" in res.salidas:
            sev = res.salidas["severidad"]
            print(f"\n  → Severidad: {sev.get('nivel', 'N/A')} "
                  f"({sev.get('criterio_rb01', 'sin criterio')})")

    except Exception as ex:
        print(f"\n✗ Error ejecutando flujo para {inc_id}: {ex}")
        cuota_agotada = "exceeded your current quota" in str(ex).lower()
        corridas.append({
            "tipo": "matriz", "incidente": inc_id,
            "archivo_entrada": ruta_log, "entrada_log": log_texto,
            "entrada_sha256": hashlib.sha256(log_texto.encode("utf-8")).hexdigest(),
            "contexto": contexto, "fuentes_contexto": fuentes_contexto,
            "ok": False, "error_general": str(ex),
            "llamadas_llm": getattr(ex, "llamadas_llm", []), "etapas": [],
        })
        matriz.append({
            "corrida_id": f"matriz-{inc_id}",
            "tipo_corrida": "matriz",
            "entrada": inc_id,
            "etapa": "ERROR_GENERAL",
            "prompt": "N/A",
            "version": None,
            "valida": False,
            "intentos": 0,
            "errores": [str(ex)[:200]],
            "artefacto": None
        })

# Medición de consistencia: repetir inc-01 tres veces
print(f"\n{'='*70}")
print(f"  Consistencia - Repitiendo inc-01-pool 3 veces")
print(f"{'='*70}\n")

log_consistencia = (RAIZ / LOGS_ENTRADA["inc-01-pool"]).read_text(encoding="utf-8")
contexto_consistencia, fuentes_consistencia = _contexto_relevante(log_consistencia)
severidades_repetidas = []
ejecuciones_validas = 0
postmortems_validos = 0
hashes_postmortem = []
errores_por_repeticion = []

for i in range(3):
    if cuota_agotada:
        motivo = "Omitida: el proveedor agotó cuota en una corrida previa"
        severidades_repetidas.append("NO_EJECUTADA")
        hashes_postmortem.append(None)
        errores_por_repeticion.append({"repeticion": i + 1, "error_general": motivo})
        corridas.append({
            "tipo": f"consistencia-{i + 1}", "incidente": "inc-01-pool",
            "archivo_entrada": LOGS_ENTRADA["inc-01-pool"],
            "entrada_log": log_consistencia,
            "entrada_sha256": hashlib.sha256(log_consistencia.encode("utf-8")).hexdigest(),
            "contexto": contexto_consistencia,
            "fuentes_contexto": fuentes_consistencia,
            "ok": False, "omitida": True, "error_general": motivo,
            "llamadas_llm": [], "etapas": [],
        })
        print(f"  Ejecución {i + 1}: {motivo}")
        continue
    try:
        res_rep, llamadas_rep = _ejecutar_trazable(flujo_a_usar, {
            "entrada": log_consistencia, "contexto": contexto_consistencia
        })
        corridas.append(_corrida_auditable(
            res_rep, llamadas_rep, "inc-01-pool", LOGS_ENTRADA["inc-01-pool"],
            log_consistencia, contexto_consistencia, fuentes_consistencia,
            f"consistencia-{i + 1}",
        ))
        for e in res_rep.etapas:
            matriz.append({
                "corrida_id": f"consistencia-{i + 1}",
                "tipo_corrida": "consistencia",
                "entrada": "inc-01-pool",
                "fuentes_contexto": fuentes_consistencia,
                "etapa": e.nombre,
                "prompt": e.prompt,
                "version": _version_de(e.prompt),
                "valida": e.ok,
                "intentos": e.intentos,
                "errores": e.errores,
                "artefacto": _salida_auditable(e.salida)[0],
                "artefacto_omitido_por_pii": _salida_auditable(e.salida)[1],
            })
            versiones_reales_usadas.add(_version_de(e.prompt))

        if res_rep.ok and "severidad" in res_rep.salidas:
            sev_nivel = res_rep.salidas["severidad"].get("nivel", "ERROR")
            severidades_repetidas.append(sev_nivel)
            ejecuciones_validas += 1
            salida_postmortem = res_rep.salidas.get("postmortem")
            if isinstance(salida_postmortem, dict):
                postmortem_json = json.dumps(
                    salida_postmortem, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":"),
                )
                hashes_postmortem.append(hashlib.sha256(postmortem_json.encode("utf-8")).hexdigest())
                postmortems_validos += 1
            else:
                hashes_postmortem.append(None)
            print(f"  Ejecución {i+1}: {sev_nivel}; postmortem válido={isinstance(salida_postmortem, dict)}")
        else:
            severidades_repetidas.append("ERROR")
            hashes_postmortem.append(None)
            errores_por_repeticion.append({
                "repeticion": i + 1,
                "salida_candidata_severidad": _salida_auditable(next(
                    (e.salida for e in res_rep.etapas if e.nombre == "severidad"), None
                ))[0],
                "etapas": [
                    {"nombre": e.nombre, "valida": e.ok, "errores": e.errores,
                     "salida": _salida_auditable(e.salida)[0],
                     "salida_omitida_por_pii": _salida_auditable(e.salida)[1]}
                    for e in res_rep.etapas
                ],
            })
            print(f"  Ejecución {i+1}: ERROR en flujo")
    except Exception as ex:
        cuota_agotada = "exceeded your current quota" in str(ex).lower()
        severidades_repetidas.append("EXCEPTION")
        hashes_postmortem.append(None)
        errores_por_repeticion.append({"repeticion": i + 1, "error_general": str(ex)})
        corridas.append({
            "tipo": f"consistencia-{i + 1}", "incidente": "inc-01-pool",
            "archivo_entrada": LOGS_ENTRADA["inc-01-pool"],
            "entrada_log": log_consistencia,
            "entrada_sha256": hashlib.sha256(log_consistencia.encode("utf-8")).hexdigest(),
            "contexto": contexto_consistencia,
            "fuentes_contexto": fuentes_consistencia,
            "ok": False, "error_general": str(ex),
            "llamadas_llm": getattr(ex, "llamadas_llm", []), "etapas": [],
        })
        print(f"  Ejecución {i+1}: Excepción - {str(ex)[:60]}")

# Consistencia estricta: las tres corridas y postmortems son válidos e idénticos.
postmortem_consistente = (
    postmortems_validos == 3 and len(set(hashes_postmortem)) == 1
    and None not in hashes_postmortem
)
consistente = (ejecuciones_validas == 3 and
               len(set(severidades_repetidas)) == 1 and
               "ERROR" not in severidades_repetidas and
               "EXCEPTION" not in severidades_repetidas and
               postmortem_consistente)

print(f"\n  Ejecuciones válidas: {ejecuciones_validas}/3")
print(f"  Severidades: {severidades_repetidas}")
print(f"  Postmortems válidos: {postmortems_validos}/3")
print(f"  JSON de postmortem idénticos: {postmortem_consistente}")
print(f"  Resultado: {'✓ Consistente' if consistente else '✗ Inconsistente'}")

if not consistente:
    if ejecuciones_validas < 3:
        print(f"  → Al menos una ejecución falló. Revisar validación y esquemas.")
    else:
        print(f"  → Las 3 ejecuciones fueron válidas pero con severidades diferentes.")
        print(f"  → Revisar el prompt para reducir variabilidad.")

# Determinar la versión real usada
if version_solicitada:
    version_real = version_solicitada
else:
    version_real = max(versiones_reales_usadas) if versiones_reales_usadas else 1

prompts_usados = {}
for etapa in flujo_a_usar.etapas:
    prompt_cargado = _prompts.cargar(etapa.prompt, etapa.version)
    ruta_prompt = _prompts.CARPETA / f"{prompt_cargado.id}.v{prompt_cargado.version}.md"
    prompts_usados[prompt_cargado.nombre] = hashlib.sha256(ruta_prompt.read_bytes()).hexdigest()
version_real = version_solicitada or max(
    (_version_de(nombre) for nombre in prompts_usados), default=1
)

corridas_matriz = [corrida for corrida in corridas if corrida.get("tipo") == "matriz"]
matriz_integrada_completa = (
    len(corridas_matriz) == len(LOGS_ENTRADA)
    and all(corrida.get("ok") and len(corrida.get("etapas", [])) == 4 for corrida in corridas_matriz)
)
estado_matriz = "COMPLETA" if matriz_integrada_completa else "PENDIENTE: una o más corridas no completaron las cuatro etapas"

# Guardar matriz en formato Markdown legible
nombre_archivo = _args.salida or f"a2_matriz_v{version_real}"
ruta_salida = RAIZ / "bitacora" / f"{nombre_archivo}.md"
ruta_salida.parent.mkdir(parents=True, exist_ok=True)

with open(ruta_salida, "w", encoding="utf-8") as f:
    f.write(f"# Matriz de Trazabilidad A2 - v5-triage\n\n")
    f.write(f"**Equipo:** Equipo 5  \n")
    f.write(f"**Variante:** v5-triage  \n")
    f.write(f"**Fecha UTC:** {datetime.now(timezone.utc).isoformat(timespec='seconds')}  \n")
    f.write(f"**Proveedor:** {config().llm_proveedor}/{config().llm_modelo}  \n")
    f.write(f"**Versión de prompts:** v{version_real}  \n\n")
    f.write(f"**Estado de matriz de Pipeline (4 etapas):** {estado_matriz}  \n")
    f.write("**Límite:** ejecución directa de `Pipeline.ejecutar` con contexto BM25 local; no ejecuta `sistema()` ni prueba el RAG vectorial.  \n")
    f.write("**Recuperación de contexto:** BM25 local directo (sin inicializar el índice vectorial A1); líneas con datos personales omitidas.  \n")
    f.write("**SHA-256 de prompts:**\n")
    for nombre_prompt, digest in sorted(prompts_usados.items()):
        f.write(f"- `{nombre_prompt}`: `{digest}`\n")
    f.write("\n")

    f.write("## Flujo de 4 Etapas\n\n")
    f.write("1. **señales** (`tri_senales`): Extrae eventos, indicadores y faltantes del log\n")
    f.write("2. **severidad** (`tri_severidad`): Clasifica SEV1/2/3/4 según rb-01\n")
    f.write("3. **acciones** (`tri_acciones`): Propone acciones inmediatas con citas a runbooks\n")
    f.write("4. **postmortem** (`tri_postmortem`): Genera borrador según pm-03\n\n")

    f.write("## Resultados por Incidente\n\n")

    for inc_id in LOGS_ENTRADA.keys():
        filas_inc = [
            m for m in matriz
            if m["entrada"] == inc_id and m.get("tipo_corrida") == "matriz"
        ]
        if not filas_inc:
            continue

        f.write(f"### {inc_id}\n\n")
        f.write(f"**Entrada:** `{LOGS_ENTRADA[inc_id]}`\n\n")
        corridas_inc = [c for c in corridas_matriz if c["incidente"] == inc_id]
        if corridas_inc:
            fuentes = corridas_inc[0].get("fuentes_contexto", [])
            f.write("**Contexto recuperado:** " + ", ".join(x["id"] for x in fuentes) + "\n\n")
        f.write("| Etapa | Prompt | Ver | Válida | Intentos | Artefacto | Errores |\n")
        f.write("|-------|--------|-----|--------|----------|-----------|----------|\n")

        for fila in filas_inc:
            valida_sym = "✓" if fila["valida"] else "✗"
            errores_txt = "; ".join(fila["errores"][:1]) if fila["errores"] else "-"
            errores_txt = errores_txt[:50] + "..." if len(errores_txt) > 50 else errores_txt

            # Mostrar resumen corto del artefacto en la tabla
            if fila.get("artefacto"):
                try:
                    art_data = fila["artefacto"] if isinstance(fila["artefacto"], dict) else json.loads(fila["artefacto"])
                    if isinstance(art_data, dict):
                        # Mostrar campos clave según la etapa
                        if fila["etapa"] == "severidad":
                            art_resumen = f"SEV: {art_data.get('nivel', 'N/A')}"
                        elif fila["etapa"] == "acciones":
                            num_acc = len(art_data.get('acciones', []))
                            art_resumen = f"{num_acc} acciones"
                        elif fila["etapa"] == "postmortem":
                            sev_pm = art_data.get('resumen', {}).get('severidad', 'N/A')
                            art_resumen = f"PM SEV: {sev_pm}"
                        else:
                            art_resumen = f"{len(str(art_data))} caracteres"
                    else:
                        art_resumen = f"{len(str(art_data))} caracteres"
                except:
                    art_resumen = f"{len(fila['artefacto'])} caracteres"
            else:
                art_resumen = "N/A"

            f.write(f"| {fila['etapa']:12s} | {fila['prompt']:20s} | "
                   f"v{fila['version'] or '?'} | {valida_sym:6s} | "
                   f"{fila['intentos']:8d} | {art_resumen:30s} | {errores_txt:50s} |\n")

        # Mostrar artefactos clave de cada etapa
        if inc_id in resultados_completos and resultados_completos[inc_id].ok:
            res_inc = resultados_completos[inc_id]

            f.write(f"\n**Artefactos clave:**\n\n")

            if "severidad" in res_inc.salidas:
                sev = res_inc.salidas["severidad"]
                f.write(f"- **severidad**: {sev.get('nivel', 'N/A')} "
                       f"({sev.get('criterio_rb01', 'sin criterio')})\n")

            if "acciones" in res_inc.salidas:
                acciones = res_inc.salidas["acciones"].get("acciones", [])
                f.write(f"- **acciones**: {len(acciones)} acciones propuestas\n")
                if acciones:
                    for acc in acciones[:2]:
                        f.write(f"  - {acc.get('descripcion', 'N/A')[:80]}\n")

            if "postmortem" in res_inc.salidas:
                pm = res_inc.salidas["postmortem"]
                num_acciones_pm = len(pm.get("acciones", []))
                num_lecciones = len(pm.get("lecciones", []))
                f.write(f"- **postmortem**: {num_acciones_pm} acciones, {num_lecciones} lecciones\n")

        f.write("\n")

    f.write("## Consistencia\n\n")
    f.write(f"**Incidente repetido:** inc-01-pool (3 ejecuciones)  \n")
    f.write(f"**Ejecuciones válidas:** {ejecuciones_validas}/3  \n")
    f.write(f"**Severidades obtenidas:** {', '.join(severidades_repetidas)}  \n")
    f.write(f"**Postmortems válidos:** {postmortems_validos}/3  \n")
    f.write(f"**Hashes de postmortem:** {', '.join(str(x) for x in hashes_postmortem)}  \n")
    f.write(f"**JSON de postmortem idénticos:** {postmortem_consistente}  \n")
    f.write(f"**Resultado de consistencia:** {'CONSISTENTE' if consistente else 'INCONSISTENTE / PENDIENTE'}  \n\n")

    if not consistente:
        f.write("⚠ **Advertencia:** La consistencia solo se declara si las tres corridas son válidas, "
               "coincide la severidad y los JSON completos de postmortem son idénticos. "
               "Consultar errores y artefactos por corrida en el JSON de auditoría.\n\n")
    f.write(f"**Matriz de Pipeline (4 etapas):** {estado_matriz}\n")
    f.write("**Integración de sistema/RAG vectorial:** PENDIENTE; no se declara LAB 3 completo.\n\n")
    if errores_por_repeticion:
        f.write("**Errores de repeticiones:** revisar `errores_por_repeticion` en el JSON adjunto.\n\n")

    f.write("## Auditoría de Artefactos\n\n")
    f.write("Los artefactos completos (salida JSON de cada etapa) están guardados en el archivo JSON adjunto "
           f"`{nombre_archivo}.json` para consulta y auditoría.\n\n")

print(f"\n{'='*70}")
print(f"✓ Matriz guardada en: {ruta_salida}")
print(f"{'='*70}\n")

# Guardar versión JSON con artefactos completos
ruta_json = RAIZ / "bitacora" / f"{nombre_archivo}.json"
with open(ruta_json, "w", encoding="utf-8") as f:
    json.dump({
        "metadata": {
            "equipo": "Equipo 5",
            "variante": "v5-triage",
            "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "proveedor": f"{config().llm_proveedor}/{config().llm_modelo}",
            "version_prompts": version_real,
            "flujo_usado": f"FLUJO_V{version_real}" if version_solicitada else "FLUJO",
            "prompts_sha256": prompts_usados,
            "parametros": {
                "temperatura_etapa": {e.nombre: e.temperatura for e in flujo_a_usar.etapas},
                "reintentos_adicionales_etapa": {e.nombre: e.reintentos for e in flujo_a_usar.etapas},
                "reintentos_http_proveedor": config().reintentos,
            },
            "recuperacion_contexto": "BM25 local directo con _BM25, corpus v5-triage; PII omitida",
            "matriz_pipeline_4_etapas": {
                "estado": estado_matriz,
                "corridas_validas": sum(bool(c.get("ok")) for c in corridas_matriz),
                "corridas_esperadas": len(LOGS_ENTRADA),
            },
            "integracion_sistema_rag_vectorial": "PENDIENTE; esta matriz ejecuta Pipeline directamente con BM25 local",
            "consistencia": {
                "incidente": "inc-01-pool",
                "ejecuciones_totales": 3,
                "ejecuciones_validas": ejecuciones_validas,
                "severidades": severidades_repetidas,
                "postmortems_validos": postmortems_validos,
                "hashes_postmortem": hashes_postmortem,
                "postmortem_consistente": postmortem_consistente,
                "consistente": consistente,
                "errores_por_repeticion": errores_por_repeticion,
            },
        },
        "corridas": corridas,
        "matriz": matriz,
    }, f, ensure_ascii=False, indent=2)

print(f"✓ Versión JSON guardada en: {ruta_json}\n")
