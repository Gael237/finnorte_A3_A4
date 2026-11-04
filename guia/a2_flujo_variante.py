"""Guía A2 · Flujo de 4 etapas variante v5-triage: logs → señales → severidad → acciones → postmortem.

    python guia/a2_flujo_variante.py                    # con tu proveedor (.env)
    python guia/a2_flujo_variante.py --version 1        # fija la versión de los prompts (para comparar v1 vs v2)
    LLM_PROVIDER=fake python guia/a2_flujo_variante.py  # sin red: no disponible para esta variante

Qué hace:
  1. Ejecuta el flujo completo con 3 logs de incidentes (pool, TLS, SPEI timeout).
  2. Valida cada salida contra su esquema JSON y reglas de negocio (y reintenta si falla).
  3. Genera la matriz de trazabilidad: entrada → etapa → prompt → validación → intentos → errores → artefacto.
  4. Repite el primer log tres veces para medir la consistencia de la severidad asignada.
  5. Guarda la matriz en bitacora/a2_matriz_vN.md con formato legible y datos JSON auditables.

Autores: Equipo 5 - v5-triage
  - Jair: etapa señales
  - Alan: etapa severidad + integración Pipeline.ejecutar
  - Gael: etapa acciones
  - Axel: etapa postmortem + este script de matriz
"""
import json
import sys
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
from finnorte import prompts as _prompts
# Importar el flujo del equipo definido en variante.py
from finnorte.variante import FLUJO, FLUJO_V1


def _version_de(prompt_usado: str):
    """Extrae el número de versión del prompt usado."""
    import re as _re
    m = _re.search(r"\.v(\d+)", prompt_usado)
    vs = _prompts.versiones(prompt_usado.split(".")[0])
    return int(m.group(1)) if m else (max(vs) if vs else 1)


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
resultados_completos = {}
versiones_reales_usadas = set()

for inc_id, ruta_log in LOGS_ENTRADA.items():
    # Leer el log
    log_path = RAIZ / ruta_log
    if not log_path.exists():
        print(f"\n✗ No se encontró {ruta_log}")
        continue

    log_texto = log_path.read_text(encoding="utf-8")

    print(f"\n{'─'*70}")
    print(f"📋 {inc_id}: {ruta_log}")
    print(f"{'─'*70}")

    # Ejecutar el flujo
    try:
        res = flujo_a_usar.ejecutar({"entrada": log_texto})
        resultados_completos[inc_id] = res

        estado = "✓ OK" if res.ok else "✗ FALLÓ"
        print(f"\n{estado} · US${res.costo_usd:.5f} · {res.latencia_ms:.0f} ms\n")

        # Registrar cada etapa en la matriz
        for e in res.etapas:
            estado_etapa = "✓" if e.ok else "✗"
            errores_resumidos = "; ".join(e.errores[:2]) if e.errores else ""

            print(f"  {estado_etapa} {e.nombre:12s} {e.prompt:25s} "
                  f"intentos={e.intentos:1d} "
                  f"{errores_resumidos[:60]}")

            version_etapa = _version_de(e.prompt)
            versiones_reales_usadas.add(version_etapa)

            # Guardar la salida completa como JSON para auditoría
            salida_json = e.salida if e.salida is not None else None

            matriz.append({
                "entrada": inc_id,
                "etapa": e.nombre,
                "prompt": e.prompt,
                "version": version_etapa,
                "valida": e.ok,
                "intentos": e.intentos,
                "errores": e.errores,
                "artefacto": salida_json
            })

        # Mostrar resultado clave: la severidad clasificada
        if res.ok and "severidad" in res.salidas:
            sev = res.salidas["severidad"]
            print(f"\n  → Severidad: {sev.get('nivel', 'N/A')} "
                  f"({sev.get('criterio_rb01', 'sin criterio')})")

    except Exception as ex:
        print(f"\n✗ Error ejecutando flujo para {inc_id}: {ex}")
        matriz.append({
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
severidades_repetidas = []
ejecuciones_validas = 0

for i in range(3):
    try:
        res_rep = flujo_a_usar.ejecutar({"entrada": log_consistencia})
        if res_rep.ok and "severidad" in res_rep.salidas:
            sev_nivel = res_rep.salidas["severidad"].get("nivel", "ERROR")
            severidades_repetidas.append(sev_nivel)
            ejecuciones_validas += 1
            print(f"  Ejecución {i+1}: {sev_nivel}")
        else:
            severidades_repetidas.append("ERROR")
            print(f"  Ejecución {i+1}: ERROR en flujo")
    except Exception as ex:
        severidades_repetidas.append("EXCEPTION")
        print(f"  Ejecución {i+1}: Excepción - {str(ex)[:60]}")

# Verificar consistencia: debe haber 3 ejecuciones válidas Y las 3 con la misma severidad
consistente = (ejecuciones_validas == 3 and
               len(set(severidades_repetidas)) == 1 and
               "ERROR" not in severidades_repetidas and
               "EXCEPTION" not in severidades_repetidas)

print(f"\n  Ejecuciones válidas: {ejecuciones_validas}/3")
print(f"  Severidades: {severidades_repetidas}")
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

# Guardar matriz en formato Markdown legible
nombre_archivo = _args.salida or f"a2_matriz_v{version_real}"
ruta_salida = RAIZ / "bitacora" / f"{nombre_archivo}.md"
ruta_salida.parent.mkdir(parents=True, exist_ok=True)

with open(ruta_salida, "w", encoding="utf-8") as f:
    import datetime
    f.write(f"# Matriz de Trazabilidad A2 - v5-triage\n\n")
    f.write(f"**Equipo:** Equipo 5  \n")
    f.write(f"**Variante:** v5-triage  \n")
    f.write(f"**Fecha:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
    f.write(f"**Proveedor:** {config().llm_proveedor}/{config().llm_modelo}  \n")
    f.write(f"**Versión de prompts:** v{version_real}  \n\n")

    f.write("## Flujo de 4 Etapas\n\n")
    f.write("1. **señales** (`tri_senales`): Extrae eventos, indicadores y faltantes del log\n")
    f.write("2. **severidad** (`tri_severidad`): Clasifica SEV1/2/3/4 según rb-01\n")
    f.write("3. **acciones** (`tri_acciones`): Propone acciones inmediatas con citas a runbooks\n")
    f.write("4. **postmortem** (`tri_postmortem`): Genera borrador según pm-03\n\n")

    f.write("## Resultados por Incidente\n\n")

    for inc_id in LOGS_ENTRADA.keys():
        filas_inc = [m for m in matriz if m["entrada"] == inc_id]
        if not filas_inc:
            continue

        f.write(f"### {inc_id}\n\n")
        f.write(f"**Entrada:** `{LOGS_ENTRADA[inc_id]}`\n\n")
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
    f.write(f"**Resultado:** {'✓ Consistente' if consistente else '✗ Inconsistente'}  \n\n")

    if not consistente:
        if ejecuciones_validas < 3:
            f.write("⚠ **Advertencia:** Al menos una ejecución falló. "
                   "Revisar que el flujo complete las 4 etapas sin errores de validación.\n\n")
        else:
            f.write("⚠ **Advertencia:** Las 3 ejecuciones fueron válidas pero asignaron severidades diferentes. "
                   "Revisar el prompt tri_severidad para reducir la variabilidad.\n\n")

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
            "proveedor": f"{config().llm_proveedor}/{config().llm_modelo}",
            "version_prompts": version_real,
            "flujo_usado": f"FLUJO_V{version_real}" if version_solicitada else "FLUJO",
            "consistencia": {
                "incidente": "inc-01-pool",
                "ejecuciones_totales": 3,
                "ejecuciones_validas": ejecuciones_validas,
                "severidades": severidades_repetidas,
                "consistente": consistente
            }
        },
        "matriz": matriz
    }, f, ensure_ascii=False, indent=2)

print(f"✓ Versión JSON guardada en: {ruta_json}\n")
