"""Contexto auditable para las ejecuciones A2 de v5-triage."""
from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from pathlib import Path

from .pipeline import Pipeline

from .config import RAIZ
from .retrieval import _BM25, cargar_corpus, fragmentar


def preparar_contexto_a2(texto: str, carpeta_corpus: str | Path | None = None):
    """Devuelve contexto, fuentes BM25 y evidencia separada de la politica rb-01."""
    carpeta = Path(carpeta_corpus) if carpeta_corpus else RAIZ / "corpus" / "v5-triage"
    documentos = cargar_corpus(carpeta)
    politica = next((doc for doc in documentos if doc.id == "rb-01"), None)
    ruta_politica = carpeta / "rb-01-severidades.md"
    if politica is None or not ruta_politica.is_file():
        raise FileNotFoundError(f"No esta disponible la politica obligatoria rb-01 en {ruta_politica}")

    fragmentos = [fragmento for doc in documentos for fragmento in fragmentar(doc)]
    bm25 = _BM25([fragmento.texto for fragmento in fragmentos])
    puntajes = bm25.puntajes(texto)
    ordenados = sorted(range(len(puntajes)), key=lambda i: -puntajes[i])[:8]
    bloques = []
    fuentes_bm25 = []
    caracteres = 0
    for indice in ordenados:
        puntaje = puntajes[indice]
        if puntaje <= 0:
            continue
        fragmento = fragmentos[indice]
        lineas_seguras = []
        for linea in fragmento.texto.splitlines():
            if (re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", linea)
                    or re.search(r"\b\d{2}\s+\d{4}\s+\d{4}\b", linea)
                    or re.search(r"cliente afectado", linea, re.IGNORECASE)):
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
        fuentes_bm25.append({"id": fragmento.id, "puntaje": round(puntaje, 6)})

    texto_bm25 = "\n\n".join(bloques)
    contexto = (
        "POLITICA OBLIGATORIA PARA LA ETAPA DE SEVERIDAD; texto directo del corpus, "
        "independiente de la recuperacion BM25.\n"
        "[politica-obligatoria:rb-01]\n"
        f"{politica.texto}\n\n"
        "FRAGMENTOS RECUPERADOS POR BM25 (solo estos IDs son fuentes de recuperacion):\n"
        f"{texto_bm25}"
    )
    evidencia_politica = {
        "id": "rb-01",
        "archivo": str(ruta_politica.relative_to(RAIZ)) if ruta_politica.is_relative_to(RAIZ) else ruta_politica.name,
        "sha256": hashlib.sha256(ruta_politica.read_bytes()).hexdigest(),
        "origen": "texto obligatorio leido directamente del corpus; separado de BM25",
        "recuperado_por_bm25": any(f["id"].startswith("rb-01#") for f in fuentes_bm25),
    }
    return contexto, fuentes_bm25, evidencia_politica


def validar_fuentes_bm25(salida: dict, fuentes_bm25: list[dict]) -> list[str]:
    """Rechaza citas de senales que no aparecen en los fragmentos BM25 entregados."""
    permitidas = {fuente.get("id") for fuente in fuentes_bm25}
    citas = salida.get("fuentes", []) if isinstance(salida, dict) else []
    if not isinstance(citas, list):
        return []
    return [f"Fuente citada no recuperada por BM25: {cita}" for cita in citas if cita not in permitidas]


def validar_citas_bm25(salida: dict, etapa: str, fuentes_bm25: list[dict]) -> list[str]:
    """Verifica citas documentales segun el contexto realmente recuperado."""
    permitidos = {fuente.get("id", "").split("#", 1)[0] for fuente in fuentes_bm25}
    if not isinstance(salida, dict):
        return []
    if etapa == "senales":
        return validar_fuentes_bm25(salida, fuentes_bm25)
    if etapa == "acciones":
        citas = [accion.get("runbook") for accion in salida.get("acciones", []) if isinstance(accion, dict)]
    elif etapa == "postmortem":
        citas = re.findall(r"\brb-\d{2}\b", str(salida))
        permitidos.add("rb-01")  # politica obligatoria, incorporada directamente y no atribuida a BM25
    else:
        return []
    return [f"Documento citado no disponible en el contexto: {cita}" for cita in citas if cita and cita not in permitidos]


def flujo_con_fuentes_bm25(flujo: Pipeline, fuentes_bm25: list[dict]) -> Pipeline:
    """Clona el flujo y aplica auditoria de IDs BM25 a la salida de senales."""
    etapas = deepcopy(flujo.etapas)
    for etapa in etapas:
        if etapa.nombre != "senales":
            continue
        validar_base = etapa.validar

        def validar(salida, previas, base=validar_base, recuperadas=fuentes_bm25):
            errores = base(salida, previas) if base else []
            return errores + validar_citas_bm25(salida, etapa.nombre, recuperadas)

        etapa.validar = validar
    return Pipeline(etapas, nombre=flujo.nombre)


def diagnostico_consistencia(ejecuciones_validas, severidades, postmortems_validos, postmortem_consistente):
    if ejecuciones_validas < 3:
        return "No se completaron tres ejecuciones validas; la consistencia no se declara."
    if len(set(severidades)) != 1:
        return "Las severidades difirieron entre las ejecuciones; la consistencia no se declara."
    if postmortems_validos == 3 and not postmortem_consistente:
        return (f"La severidad coincidi\u00f3 en {ejecuciones_validas}/3 ejecuciones, "
                "pero los JSON completos de postmortem difirieron; consistente=false bajo la regla estricta.")
    return "Los requisitos estrictos de consistencia no se cumplieron."
