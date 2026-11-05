"""Prueba reproducible de señales v2 con un log y contexto recuperado.

Desde la raíz: python guia/prueba_senales.py
Respeta LLM_PROVIDER y EMB_PROVIDER de .env o del entorno; fake no demuestra calidad del modelo.
"""
import json

from finnorte import controles
from finnorte.config import RAIZ, config
from finnorte.pipeline import Etapa, Pipeline
from finnorte.reglas_tri_senales import validar_senales
from finnorte.retrieval import Indice, contexto_para_prompt


def ejecutar():
    log = (RAIZ / "datos/v5-triage/logs/inc-01-pool.log").read_text(encoding="utf-8")
    indice = Indice.desde_carpeta(RAIZ / "corpus/v5-triage")
    recuperados = [
        r for r in indice.buscar(log, k=4)
        if r.fragmento.clasificacion in {"publica", "interna"}
    ]
    if not recuperados:
        raise RuntimeError("No se recuperó ningún fragmento permitido para la prueba")
    contexto = contexto_para_prompt(recuperados)

    def validar(datos, previas):
        fuentes = datos.get("fuentes", [])
        # Una extracción puramente del log puede no citar políticas. Si cita,
        # cada ID sí debe corresponder a un fragmento del contexto.
        errores_citas = controles.verificar_citas(fuentes, recuperados) if fuentes else []
        return validar_senales(datos, previas) + errores_citas

    etapa = Etapa("senales", "tri_senales", version=2, validar=validar)
    resultado = Pipeline([etapa], nombre="prueba_senales_v2").ejecutar(
        {"entrada": log, "contexto": contexto}
    )
    print(f"Proveedor efectivo: {config().llm_proveedor}/{config().llm_modelo}")
    print("Fragmentos recuperados:", [r.fragmento.id for r in recuperados])
    print("Etapa válida:", resultado.ok)
    print("Errores:", resultado.etapas[0].errores)
    if resultado.ok:
        print(json.dumps(resultado.salidas["senales"], ensure_ascii=False, indent=2))
    return resultado.ok


if __name__ == "__main__":
    raise SystemExit(0 if ejecutar() else 1)
