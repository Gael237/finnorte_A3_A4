import os
import json
from pathlib import Path
from finnorte.pipeline import Pipeline, Etapa

# Forzar Gemini para la prueba de red, o dejar en fake si no hay cuota
# os.environ["LLM_PROVIDER"] = "gemini"

etapa_senales = Etapa(
    nombre="senales",
    prompt="tri_senales",
    version=2,
    usa=[],
    reintentos=1
)
flujo = Pipeline([etapa_senales], nombre="prueba_senales_v2")

# Leer un log y un manual reales (ajusta las rutas a archivos reales de tu variante v5)
archivo_log = Path("datos/v5-triage/logs/inc-01-pool.log")
archivo_doc = Path("corpus/v5-triage/rb-01-severidades.md")

entrada_real = archivo_log.read_text(encoding="utf-8") if archivo_log.exists() else "ERROR: Log no encontrado. Revisa la ruta en datos/"
contexto_real = archivo_doc.read_text(encoding="utf-8") if archivo_doc.exists() else "ERROR: Documento no encontrado. Revisa la ruta en corpus/"

caso = {
    "entrada": entrada_real,
    "contexto": contexto_real
}

print(f"Proveedor efectivo: {os.environ.get('LLM_PROVIDER', 'gemini (por defecto)')}")
res = flujo.ejecutar(caso, detener_en_error=False)

print(f"\n¿Pasó res.ok?: {res.ok}")
print(f"Errores de la etapa: {[etapa.errores for etapa in res.etapas]}")
print("\nJSON obtenido:")
print(json.dumps(res.salidas.get("senales"), indent=2, ensure_ascii=False))