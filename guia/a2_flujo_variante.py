"""Guía A2 · Flujo de 4 etapas variante v5-triage: logs → señales → severidad → acciones → postmortem.

    python guia/a2_flujo_variante.py                    # con tu proveedor (.env)
    python guia/a2_flujo_variante.py --version 1        # fija la versión de los prompts (para comparar v1 vs v2)
    LLM_PROVIDER=fake python guia/a2_flujo_variante.py  # sin red: no disponible para esta variante

Qué hace:
  1. Ejecuta el flujo completo con 3 logs de incidentes (pool, TLS, SPEI timeout).
  2. Valida cada salida contra su esquema JSON y reglas de negocio (y reintenta si falla).
  3. Genera la matriz de trazabilidad: log → etapa → prompt → validación → intentos → errores.
  4. Repite el primer log tres veces para medir la consistencia de la severidad asignada.
  5. Guarda la matriz en bitacora/a2_matriz_vN.md con formato legible.

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
from finnorte.pipeline import Etapa, Pipeline
from finnorte import prompts as _prompts

# Importar funciones de validación de cada etapa
# Ajustar nombres según lo que definió cada integrante
try:
    from finnorte.reglas_tri_postmortem import validar_postmortem
except ImportError:
    print("⚠ Advertencia: no se encontró finnorte.reglas_tri_postmortem")
    validar_postmortem = lambda s, p: []

# TODO: Importar validaciones de las otras etapas cuando estén listas
# from finnorte.reglas_tri_senales import validar_senales
# from finnorte.reglas_tri_severidad import validar_severidad  
# from finnorte.reglas_tri_acciones import validar_acciones


def _version_de(prompt_usado: str):
    """Extrae el número de versión del prompt usado."""
    import re as _re
    m = _re.search(r"\.v(\d+)", prompt_usado)
    vs = _prompts.versiones(prompt_usado.split(".")[0])
    return int(m.group(1)) if m else (max(vs) if vs else 1)


import argparse

_ap = argparse.ArgumentParser(description="Guía A2 · flujo de triage de incidentes v5")
_ap.add_argument("--version", type=int, default=None, 
                 help="versión de los prompts tri_* (por defecto la más reciente)")
_ap.add_argument("--salida", default=None, 
                 help="nombre del archivo en bitacora/ (por defecto a2_matriz_vN)")
_args = _ap.parse_args()

# Definir el flujo de 4 etapas según el reparto del equipo
# TODO: Alan debe ajustar esto con las etapas reales y sus dependencias (usa=)
FLUJO = Pipeline([
    Etapa("senales", "tri_senales", version=_args.version),
    Etapa("severidad", "tri_severidad", version=_args.version, usa=["senales"]),
    Etapa("acciones", "tri_acciones", version=_args.version, usa=["senales", "severidad"]),
    Etapa("postmortem", "tri_postmortem", version=_args.version, 
          usa=["senales", "severidad", "acciones"], 
          validar=validar_postmortem),
], nombre="triage")

# Los 3 logs de incidentes para la matriz
LOGS_ENTRADA = {
    "inc-01-pool": "datos/v5-triage/logs/inc-01-pool.log",
    "inc-02-tls": "datos/v5-triage/logs/inc-02-tls.log",
    "inc-03-spei": "datos/v5-triage/logs/inc-03-spei-timeout.log",
}

print(f"{'='*70}")
print(f"  Flujo de Triage v5 - Equipo 5")
print(f"  Proveedor: {config().llm_proveedor}/{config().llm_modelo}")
print(f"{'='*70}\n")

matriz = []
resultados_completos = {}

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
        res = FLUJO.ejecutar({"entrada": log_texto})
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
            
            matriz.append({
                "incidente": inc_id,
                "etapa": e.nombre,
                "prompt": e.prompt,
                "version": _version_de(e.prompt),
                "valida": e.ok,
                "intentos": e.intentos,
                "errores": e.errores[:2],
                "salida_resumida": str(e.salida)[:100] + "..." if e.salida else None
            })
        
        # Mostrar resultado clave: la severidad clasificada
        if res.ok and "severidad" in res.salidas:
            sev = res.salidas["severidad"]
            print(f"\n  → Severidad: {sev.get('nivel', 'N/A')} "
                  f"({sev.get('criterio_rb01', 'sin criterio')})")
            
    except Exception as ex:
        print(f"\n✗ Error ejecutando flujo para {inc_id}: {ex}")
        matriz.append({
            "incidente": inc_id,
            "etapa": "ERROR_GENERAL",
            "prompt": "N/A",
            "version": None,
            "valida": False,
            "intentos": 0,
            "errores": [str(ex)[:200]],
            "salida_resumida": None
        })

# Medición de consistencia: repetir inc-01 tres veces
print(f"\n{'='*70}")
print(f"  Consistencia - Repitiendo inc-01-pool 3 veces")
print(f"{'='*70}\n")

log_consistencia = (RAIZ / LOGS_ENTRADA["inc-01-pool"]).read_text(encoding="utf-8")
severidades_repetidas = []

for i in range(3):
    try:
        res_rep = FLUJO.ejecutar({"entrada": log_consistencia})
        if res_rep.ok and "severidad" in res_rep.salidas:
            sev_nivel = res_rep.salidas["severidad"].get("nivel", "ERROR")
            severidades_repetidas.append(sev_nivel)
            print(f"  Ejecución {i+1}: {sev_nivel}")
        else:
            severidades_repetidas.append("ERROR")
            print(f"  Ejecución {i+1}: ERROR en flujo")
    except Exception as ex:
        severidades_repetidas.append("EXCEPTION")
        print(f"  Ejecución {i+1}: Excepción - {str(ex)[:60]}")

# Verificar consistencia
consistente = len(set(severidades_repetidas)) == 1
print(f"\n  Resultado: {'✓ Consistente' if consistente else '✗ Inconsistente'}")
print(f"  Severidades: {severidades_repetidas}")

# Guardar matriz en formato Markdown legible
version_prompts = _args.version or max(_prompts.versiones("tri_postmortem"), default=1)
nombre_archivo = _args.salida or f"a2_matriz_v{version_prompts}"
ruta_salida = RAIZ / "bitacora" / f"{nombre_archivo}.md"
ruta_salida.parent.mkdir(parents=True, exist_ok=True)

with open(ruta_salida, "w", encoding="utf-8") as f:
    f.write(f"# Matriz de Trazabilidad A2 - v5-triage\n\n")
    f.write(f"**Equipo:** Equipo 5  \n")
    f.write(f"**Variante:** v5-triage  \n")
    f.write(f"**Fecha:** {config().fecha_ejecucion}  \n")
    f.write(f"**Proveedor:** {config().llm_proveedor}/{config().llm_modelo}  \n")
    f.write(f"**Versión de prompts:** v{version_prompts}  \n\n")
    
    f.write("## Flujo de 4 Etapas\n\n")
    f.write("1. **señales** (`tri_senales`): Extrae eventos, indicadores y faltantes del log\n")
    f.write("2. **severidad** (`tri_severidad`): Clasifica SEV1/2/3/4 según rb-01\n")
    f.write("3. **acciones** (`tri_acciones`): Propone acciones inmediatas con citas a runbooks\n")
    f.write("4. **postmortem** (`tri_postmortem`): Genera borrador según pm-03\n\n")
    
    f.write("## Resultados por Incidente\n\n")
    
    for inc_id in LOGS_ENTRADA.keys():
        filas_inc = [m for m in matriz if m["incidente"] == inc_id]
        if not filas_inc:
            continue
            
        f.write(f"### {inc_id}\n\n")
        f.write("| Etapa | Prompt | Ver | Válida | Intentos | Errores |\n")
        f.write("|-------|--------|-----|--------|----------|----------|\n")
        
        for fila in filas_inc:
            valida_sym = "✓" if fila["valida"] else "✗"
            errores_txt = "; ".join(fila["errores"][:1]) if fila["errores"] else "-"
            errores_txt = errores_txt[:50] + "..." if len(errores_txt) > 50 else errores_txt
            
            f.write(f"| {fila['etapa']:12s} | {fila['prompt']:20s} | "
                   f"v{fila['version'] or '?'} | {valida_sym:6s} | "
                   f"{fila['intentos']:8d} | {errores_txt:50s} |\n")
        
        # Mostrar artefacto clave de cada etapa
        if inc_id in resultados_completos and resultados_completos[inc_id].ok:
            res_inc = resultados_completos[inc_id]
            
            f.write(f"\n**Artefactos clave:**\n\n")
            
            if "severidad" in res_inc.salidas:
                sev = res_inc.salidas["severidad"]
                f.write(f"- Severidad clasificada: **{sev.get('nivel', 'N/A')}** "
                       f"({sev.get('criterio_rb01', 'sin criterio')})\n")
            
            if "acciones" in res_inc.salidas:
                acciones = res_inc.salidas["acciones"].get("acciones", [])
                f.write(f"- Acciones propuestas: {len(acciones)} acciones\n")
            
            if "postmortem" in res_inc.salidas:
                pm = res_inc.salidas["postmortem"]
                num_acciones_pm = len(pm.get("acciones", []))
                num_lecciones = len(pm.get("lecciones", []))
                f.write(f"- Postmortem: {num_acciones_pm} acciones, {num_lecciones} lecciones\n")
        
        f.write("\n")
    
    f.write("## Consistencia\n\n")
    f.write(f"**Incidente repetido:** inc-01-pool (3 ejecuciones)  \n")
    f.write(f"**Severidades obtenidas:** {', '.join(severidades_repetidas)}  \n")
    f.write(f"**Resultado:** {'✓ Consistente' if consistente else '✗ Inconsistente'}  \n\n")
    
    if not consistente:
        f.write("⚠ **Advertencia:** La clasificación de severidad no es consistente entre ejecuciones. "
               "Revisar el prompt para reducir la variabilidad.\n\n")
    
    f.write("## Datos JSON Completos\n\n")
    f.write("```json\n")
    f.write(json.dumps(matriz, ensure_ascii=False, indent=2))
    f.write("\n```\n")

print(f"\n{'='*70}")
print(f"✓ Matriz guardada en: {ruta_salida}")
print(f"{'='*70}\n")

# También guardar versión JSON
ruta_json = RAIZ / "bitacora" / f"{nombre_archivo}.json"
with open(ruta_json, "w", encoding="utf-8") as f:
    json.dump({
        "metadata": {
            "equipo": "Equipo 5",
            "variante": "v5-triage",
            "proveedor": f"{config().llm_proveedor}/{config().llm_modelo}",
            "version_prompts": version_prompts,
            "consistencia": {
                "incidente": "inc-01-pool",
                "ejecuciones": 3,
                "severidades": severidades_repetidas,
                "consistente": consistente
            }
        },
        "matriz": matriz
    }, f, ensure_ascii=False, indent=2)

print(f"✓ Versión JSON guardada en: {ruta_json}\n")
