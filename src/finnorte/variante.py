"""TU SISTEMA: el motor de la variante de tu equipo.

Contrato mínimo (lo usa `python -m finnorte evaluar ... --sistema finnorte.variante:sistema`,
la API de la semana 4 y la interfaz de la semana 5):

    sistema(entrada: dict) -> dict con
        respuesta: str        el artefacto final en texto (casos, hallazgos, respuesta, README, triage)
        fuentes: list[str]    ids de fragmentos/documentos del corpus que respaldan la salida
        abstuvo: bool         True si la entrada está fuera de alcance o no hay contexto suficiente
        errores_citas: list   salida de controles.verificar_citas
        artefacto: dict       (opcional) la salida estructurada (JSON) de tu última etapa
        costo_usd, latencia_ms

Construye esto por incrementos:
  A1  → INDICE con el corpus de tu variante (corpus/<variante>/) y búsqueda semántica
  A2  → FLUJO de 4 etapas con prompts versionados en prompts/ y esquemas en prompts/esquemas/
  Av1 → RAG (contexto en el prompt) + controles + evaluación contra tu contrato de calidad
"""

from __future__ import annotations
from .reglas_tri_senales import validar_senales
from .reglas_tri_severidad import validar_severidad
from .reglas_tri_acciones import validar_acciones
from .reglas_tri_postmortem import validar_postmortem
import time
import json
from pathlib import Path

from . import controles, pii
from .config import RAIZ
from .pipeline import Etapa, Pipeline
from .retrieval import Indice, contexto_para_prompt

VARIANTE = "v5-triage"          # v1-qa | v2-revisor | v3-soporte | v4-documentador | v5-triage
_INDICE: Indice | None = None


def indice() -> Indice:
    global _INDICE
    if _INDICE is None:
        _INDICE = Indice.desde_carpeta(RAIZ / "corpus" / VARIANTE)
    return _INDICE


def leer_entrada(entrada: dict) -> str:
    """Normaliza la entrada de los casos de evaluación a texto."""
    if "archivo" in entrada:
        return (RAIZ / entrada["archivo"]).read_text(encoding="utf-8")
    for clave in ("requisito", "codigo", "pregunta", "log"):
        if clave in entrada:
            return str(entrada[clave])
    raise ValueError(f"Entrada sin campo reconocido: {list(entrada)}")

ETAPA_SENALES = Etapa(
    "senales",
    "tri_senales",
    version=1,
    validar=validar_senales,
)

ETAPA_SEVERIDAD = Etapa(
    "severidad",
    "tri_severidad",
    version=1,
    usa=["senales"],
    validar=validar_severidad,
)

ETAPA_ACCIONES = Etapa(
    "acciones",
    "tri_acciones",
    version=2,
    usa=["senales", "severidad"],
    validar=validar_acciones,
)

ETAPA_POSTMORTEM = Etapa(
    "postmortem",
    "tri_postmortem",
    version=2,
    usa=["senales", "severidad", "acciones"],
    validar=validar_postmortem,
)


def _validar_acciones_v1(datos: dict, previas: dict) -> list[str]:
    """Adapta faltantes de tri_acciones v1 (string) al validador com?n (lista)."""
    if not isinstance(datos, dict):
        return ["La salida v1 de acciones debe ser un objeto JSON"]
    faltantes = datos.get("faltantes")
    if not isinstance(faltantes, str):
        return ["tri_acciones.v1 requiere que faltantes sea un string"]
    adaptados = {**datos, "faltantes": [faltantes] if faltantes.strip() else []}
    return validar_acciones(adaptados, previas)


ETAPA_ACCIONES_V1 = Etapa(
    "acciones",
    "tri_acciones",
    version=1,
    usa=["senales", "severidad"],
    validar=_validar_acciones_v1,
)

FLUJO = Pipeline(
    [ETAPA_SENALES, ETAPA_SEVERIDAD, ETAPA_ACCIONES, ETAPA_POSTMORTEM],
    nombre=VARIANTE,
)
FLUJO_V1 = Pipeline(
    [
        Etapa("senales", "tri_senales", version=1, validar=validar_senales),
        Etapa("severidad", "tri_severidad", version=1, usa=["senales"], validar=validar_severidad),
        ETAPA_ACCIONES_V1,
        Etapa("postmortem", "tri_postmortem", version=1,
              usa=["senales", "severidad", "acciones"], validar=validar_postmortem),
    ],
    nombre=f"{VARIANTE}-v1",
)

# Configuración del motor. guia/av1_configuraciones.py la cambia para medir A, B, C y D.
CONFIG_POR_DEFECTO = {
    "version_prompt": 2,   # 1 o 2: qué versión de prompts usa el flujo
    "usar_rag": True,      # recuperar contexto del corpus de la variante (A1)
    "controles": True,     # abstención, filtrado de confidenciales, citas verificadas, saneo
    "k": 4,                # fragmentos a recuperar
    "umbral": 0.35,        # similitud mínima para no abstenerse (ajústalo con tus datos)
}


def armar_salida(t0: float, respuesta: str, fuentes: list[str], abstuvo: bool,
                 errores_citas: list[str] | None = None, artefacto: dict | None = None, costo_usd: float = 0.0) -> dict:
    """Arma el dict que esperan la evaluación, la API (S4) y la interfaz (S5)."""
    return {"respuesta": respuesta, "fuentes": fuentes, "abstuvo": abstuvo, "errores_citas": errores_citas or [],
            "artefacto": artefacto or {}, "costo_usd": costo_usd,
            "latencia_ms": round((time.perf_counter() - t0) * 1000, 1)}


def sistema(entrada: dict, config: dict | None = None) -> dict:
    """Conecta búsqueda, controles y las cuatro etapas de triage."""
    cfg = {**CONFIG_POR_DEFECTO, **(config or {})}
    t0 = time.perf_counter()
    texto = leer_entrada(entrada)

    recuperados = indice().buscar(texto, k=cfg["k"]) if cfg["usar_rag"] else []

    if cfg["controles"]:
        recuperados = controles.opcional(
            controles.filtrar_clasificacion,
            recuperados,
            por_defecto=recuperados,
        )
        if cfg["usar_rag"] and controles.debe_abstenerse(
            recuperados, cfg["umbral"]
        ):
            return armar_salida(t0, controles.RESPUESTA_ABSTENCION, [], True)

    contexto = contexto_para_prompt(recuperados) if recuperados else "(sin contexto)"
    flujo = FLUJO_V1 if cfg["version_prompt"] == 1 else FLUJO
    resultado = flujo.ejecutar({"entrada": texto, "contexto": contexto})

    if not resultado.ok:
        return armar_salida(
            t0, controles.RESPUESTA_ABSTENCION, [], True,
            costo_usd=resultado.costo_usd,
        )

    senales = resultado.salidas.get("senales")
    severidad = resultado.salidas.get("severidad")
    acciones = resultado.salidas.get("acciones")
    postmortem = resultado.salidas.get("postmortem")
    if not all(isinstance(x, dict) for x in
               (senales, severidad, acciones, postmortem)):
        return armar_salida(
            t0, controles.RESPUESTA_ABSTENCION, [], True,
            costo_usd=resultado.costo_usd,
        )

    acciones_inmediatas = acciones.get("acciones", [])
    fuentes = []
    candidatas = [severidad.get("fuente")]
    candidatas.extend(
        accion.get("runbook")
        for accion in acciones_inmediatas
        if isinstance(accion, dict)
    )
    for fuente in candidatas:
        if isinstance(fuente, str) and fuente and fuente not in fuentes:
            fuentes.append(fuente)

    incidentes_similares = []
    if cfg["usar_rag"]:
        for recuperado in recuperados:
            doc_id = recuperado.fragmento.doc_id
            if (
                doc_id in {"pm-01", "pm-02"}
                and recuperado.puntaje >= cfg["umbral"]
                and doc_id not in incidentes_similares
            ):
                incidentes_similares.append(doc_id)
                if doc_id not in fuentes:
                    fuentes.append(doc_id)

    causa = postmortem.get("causa_raiz", {})
    artefacto = {
        "severidad": severidad.get("nivel"),
        "sintomas": senales.get("eventos", []),
        "causa_probable": causa.get("tecnica") if isinstance(causa, dict) else None,
        "runbook": [f for f in fuentes if f.startswith("rb-") and f != "rb-01"],
        "acciones_inmediatas": acciones_inmediatas,
        "incidentes_similares": incidentes_similares,
        "borrador_postmortem": postmortem,
    }
    respuesta = json.dumps(artefacto, ensure_ascii=False)

    errores = (
        controles.verificar_citas(fuentes, recuperados)
        if cfg["usar_rag"] else []
    )
    if cfg["controles"]:
        if any("no recuperada" in error for error in errores):
            return armar_salida(
                t0, controles.RESPUESTA_ABSTENCION, [], True,
                errores_citas=errores, costo_usd=resultado.costo_usd,
            )

        respuesta, _avisos = controles.opcional(
            controles.sanear_salida,
            respuesta,
            por_defecto=(respuesta, []),
        )
        if pii.contiene_pii(respuesta) or pii.contiene_pii(
            json.dumps(artefacto, ensure_ascii=False)
        ):
            return armar_salida(
                t0, controles.RESPUESTA_ABSTENCION, [], True,
                errores_citas=errores, costo_usd=resultado.costo_usd,
            )

    return armar_salida(
        t0, respuesta, fuentes, False,
        errores_citas=errores, artefacto=artefacto,
        costo_usd=resultado.costo_usd,
    )
