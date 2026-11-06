"""Regla de negocio para clasificar incidentes según rb-01."""

import re
from typing import Any

BOOLEANOS = (
    "transferencias_caidas_todos",
    "acceso_caido_todos",
    "exposicion_datos",
    "falla_componente_critico",
    "alternativa_disponible",
    "falla_parcial_sin_impacto_dinero",
    "problema_menor",
)
NUMERICOS = (
    "p95_transferencias_s",
    "duracion_p95_sobre_3s_min",
    "errores_5xx_pct",
)

_ALCANCE_TOTAL_TRANSFERENCIAS = re.compile(
    r"\b(?:todas\s+las\s+transferencias|todos\s+los\s+(?:usuarios|env[ií]os(?:\s+SPEI)?)|"
    r"ca[ií]da\s+total\s+(?:de\s+)?(?:las\s+)?transferencias|"
    r"transferencias\s+(?:ca[ií]das|fallidas)\s+para\s+todos)\b",
    re.IGNORECASE,
)


def _texto_log_original(entrada_original: Any) -> str:
    if isinstance(entrada_original, str):
        return entrada_original
    if isinstance(entrada_original, dict):
        for clave in ("entrada", "log"):
            texto = entrada_original.get(clave)
            if isinstance(texto, str):
                return texto
    return ""


def _hay_evidencia_alcance_total(entrada_original: Any) -> bool:
    texto_log = _texto_log_original(entrada_original)
    return bool(_ALCANCE_TOTAL_TRANSFERENCIAS.search(texto_log))


def validar_severidad(salida: Any, salidas: dict) -> list[str]:
    """Devuelve errores si el nivel no concuerda con las señales."""
    senales = salidas.get("senales")
    if not isinstance(senales, dict):
        return ["Falta la salida estructurada de la etapa senales"]

    indicadores = senales.get("indicadores")
    if not isinstance(indicadores, dict):
        return ["senales.indicadores debe ser un objeto"]

    faltan = [clave for clave in (*BOOLEANOS, *NUMERICOS)
              if clave not in indicadores]
    if faltan:
        return [f"Faltan indicadores: {', '.join(faltan)}"]

    errores = []
    for clave in BOOLEANOS:
        valor = indicadores[clave]
        if valor is not None and type(valor) is not bool:
            errores.append(f"{clave} debe ser true, false o null")

    for clave in NUMERICOS:
        valor = indicadores[clave]
        if valor is not None and (
            isinstance(valor, bool)
            or not isinstance(valor, (int, float))
            or valor < 0
        ):
            errores.append(f"{clave} debe ser un número no negativo o null")

    porcentaje = indicadores["errores_5xx_pct"]
    if isinstance(porcentaje, (int, float)) and not isinstance(porcentaje, bool) and porcentaje > 100:
        errores.append("errores_5xx_pct no puede superar 100")
    if errores:
        return errores

    i = indicadores
    entrada_original = salidas.get("_entrada_original")
    if i["transferencias_caidas_todos"] is True and not _hay_evidencia_alcance_total(entrada_original):
        return [
            "transferencias_caidas_todos=true requiere evidencia explícita de alcance total en el log original; "
            "un evento generado por el modelo no demuestra ese alcance"
        ]

    if any(i[clave] is True for clave in (
        "transferencias_caidas_todos", "acceso_caido_todos", "exposicion_datos"
    )):
        esperado = "SEV1"
    elif (
        i["p95_transferencias_s"] is not None
        and i["duracion_p95_sobre_3s_min"] is not None
        and i["p95_transferencias_s"] > 3
        and i["duracion_p95_sobre_3s_min"] > 10
    ) or (
        i["errores_5xx_pct"] is not None
        and i["errores_5xx_pct"] > 5
    ) or (
        i["falla_componente_critico"] is True
        and i["alternativa_disponible"] is True
    ):
        esperado = "SEV2"
    elif i["falla_parcial_sin_impacto_dinero"] is True:
        esperado = "SEV3"
    elif i["problema_menor"] is True:
        esperado = "SEV4"
    else:
        return ["No hay evidencia suficiente para asignar una severidad según rb-01"]

    if not isinstance(salida, dict) or salida.get("nivel") != esperado:
        return [f"Según los indicadores y rb-01, el nivel debe ser {esperado}"]
    return []
