from __future__ import annotations
import json
import re
from typing import Any

RUNBOOKS_AUTORIZADOS = frozenset({"rb-02", "rb-03", "rb-04", "rb-05", "rb-06", "rb-07", "rb-08"})
_PATRONES_RUNBOOK = {
    "rb-02": r"latencia|p95|lentitud|lento|transferencias.*(?:lenta|latencia)",
    "rb-03": r"queuepool|connection slots|conexiones? (?:de )?(?:base|bd|datos)|base de datos|consultas? lentas",
    "rb-04": r"\btls\b|\bssl\b|certificado|certificate_verify_failed|certificate has expired",
    "rb-05": r"\bspei\b|spei-gateway|fn-5031|gateway",
    "rb-06": r"notificaciones|consumer lag|cola.{0,30}pendientes|message processing failed|mensaje.{0,20}venenoso",
    "rb-07": r"oomkilled|\boom\b|memoria|memory",
    "rb-08": r"despliegue|deploy|rollback|versión anterior|version anterior",
}
_PATRONES_DESTRUCTIVOS = re.compile(
    r"\b(?:apagar|borrar|eliminar|vaciar|purga(?:r)?|formatear|droppear)\b"
    r"|\breiniciar\s+(?:todo|todos|todas)\b"
    r"|\b(?:desactivar|deshabilitar)\s+(?:tls|ssl|autenticaci[oó]n|cifrado|seguridad)\b", re.I)
_ACCIONES_VAGAS = {"revisar el incidente", "investigar el problema", "tomar acciones", "monitorear", "escalar", "revisar", "investigar"}

def _texto_senales(senales: dict[str, Any]) -> str:
    return json.dumps({"eventos": senales.get("eventos", []), "indicadores": senales.get("indicadores")}, ensure_ascii=False, sort_keys=True).casefold()

def validar_acciones(datos: Any, previas: dict) -> list[str]:
    """Valida evidencia, runbooks y seguridad de las acciones propuestas."""
    if not isinstance(datos, dict):
        return ["La salida de acciones debe ser un objeto JSON"]
    senales, severidad = previas.get("senales"), previas.get("severidad")
    errores = []
    if not isinstance(senales, dict) or not isinstance(senales.get("indicadores"), dict):
        errores.append("Falta senales.indicadores con la estructura de la etapa tri_senales")
    if not isinstance(severidad, dict) or severidad.get("nivel") not in {"SEV1", "SEV2", "SEV3", "SEV4"}:
        errores.append("Falta severidad.nivel con un valor SEV1, SEV2, SEV3 o SEV4")
    if errores:
        return errores
    acciones, faltantes = datos.get("acciones"), datos.get("faltantes")
    if not isinstance(acciones, list) or not isinstance(faltantes, list):
        return ["acciones debe ser una lista y faltantes debe ser una lista de datos pendientes"]
    texto = _texto_senales(senales)
    sustentados = {rb for rb, patron in _PATRONES_RUNBOOK.items() if re.search(patron, texto, re.I)}
    if not acciones and not faltantes:
        errores.append("Sin acciones, faltantes debe explicar qué evidencia hace falta")
    for i, accion in enumerate(acciones):
        campo = f"acciones[{i}]"
        if not isinstance(accion, dict):
            errores.append(f"{campo} debe ser un objeto")
            continue
        runbook, descripcion = accion.get("runbook"), accion.get("descripcion")
        if runbook not in RUNBOOKS_AUTORIZADOS:
            errores.append(f"{campo}: runbook no autorizado: {runbook!r}")
            continue
        if not isinstance(descripcion, str) or len(descripcion.strip()) < 20:
            errores.append(f"{campo}: descripción demasiado breve o ausente; debe ser concreta")
            continue
        descripcion = descripcion.strip()
        if descripcion.casefold().rstrip(".") in _ACCIONES_VAGAS:
            errores.append(f"{campo}: la descripción es genérica; indica objeto y paso verificable")
        if _PATRONES_DESTRUCTIVOS.search(descripcion):
            errores.append(f"{campo}: acción destructiva prohibida")
        if runbook not in sustentados:
            errores.append(f"{campo}: {runbook} no está sustentado por las señales disponibles")
    return errores
