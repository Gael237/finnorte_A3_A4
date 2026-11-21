"""Agente con herramientas (T10): el modelo PROPONE una acción en JSON; tu código decide y la ejecuta."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

import jsonschema

from . import llm, pii, trazas
from .caso_guia import agente_ref
from .config import RAIZ, config
from .retrieval import Indice


@dataclass
class Herramienta:
    nombre: str
    descripcion: str
    esquema: dict
    funcion: Callable[..., Any]
    sensible: bool = False


@dataclass
class Paso:
    n: int
    propuesta: dict
    resultado: Any = None
    estado: str = ""


@dataclass
class ResultadoAgente:
    respuesta: str
    fuentes: list
    pasos: list[Paso] = field(default_factory=list)
    terminado: bool = True


def _catalogo(herrs: dict[str, Herramienta]) -> str:
    return "\n".join(
        f"- {h.nombre}: {h.descripcion}. Argumentos (JSON Schema): {json.dumps(h.esquema, ensure_ascii=False)}"
        + (" [SENSIBLE: requiere confirmación]" if h.sensible else "")
        for h in herrs.values()
    )


SISTEMA_AGENTE = """Eres un asistente de ingeniería de FinNorte que resuelve tareas en pasos.
En cada turno devuelve SOLO un JSON con una de dos formas:
{{"accion": "usar", "herramienta": "<nombre>", "argumentos": {{...}}, "razon": "<por qué>"}}
{{"accion": "responder", "respuesta": "<respuesta final>", "fuentes": ["<id>", ...]}}
Herramientas disponibles:
{catalogo}
No inventes herramientas ni resultados. Si una herramienta falla, decide si reintentar o responder con lo que tienes."""


def _guion_triage_fake(tarea: str):
    """Guion determinista para tareas de triage en modo fake sin responder explícito."""
    fechas = re.findall(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", tarea)
    desde = fechas[0] if len(fechas) >= 1 else "2026-11-24T10:00:00"
    hasta = fechas[1] if len(fechas) >= 2 else "2026-11-24T11:30:00"

    def _paso(mensaje: str) -> dict:
        if mensaje.startswith("Tarea:"):
            return {
                "accion": "usar",
                "herramienta": "buscar_logs",
                "argumentos": {"desde": desde, "hasta": hasta, "patron": "ERROR"},
                "razon": "Consulto logs operativos primero.",
            }
        if mensaje.startswith("Resultado de buscar_logs"):
            return {
                "accion": "usar",
                "herramienta": "consultar_runbooks_triage",
                "argumentos": {"consulta": "timeout pool conexiones severidad"},
                "razon": "Reviso runbooks de severidad.",
            }
        if mensaje.startswith("Resultado de consultar_runbooks_triage"):
            return {
                "accion": "usar",
                "herramienta": "crear_ticket_incidente",
                "argumentos": {
                    "servicio": "pagos-api",
                    "severidad": "P1",
                    "resumen": "Timeouts 504 y pool de conexiones agotado en pagos-api",
                    "runbook": "rb-03",
                },
                "razon": "Evidencia validada; propongo ticket P1.",
            }
        return {
            "accion": "responder",
            "respuesta": "Ticket de incidente propuesto y pendiente de confirmación.",
            "fuentes": ["logs-operativos", "rb-03"],
        }

    return _paso


def ejecutar_agente(
    tarea: str,
    herramientas: list[Herramienta],
    confirmar: Callable[[Herramienta, dict], bool | None] | None = None,
    max_pasos: int = 5,
    contexto: str = "",
) -> ResultadoAgente:
    herrs = {h.nombre: h for h in herramientas}
    sistema = SISTEMA_AGENTE.format(catalogo=_catalogo(herrs))
    historial: list[dict] = []
    pasos: list[Paso] = []
    vistos: set[tuple[str, str]] = set()
    mensaje = f"Tarea: {tarea}" + (f"\n\nContexto:\n{contexto}" if contexto else "")

    guion = None
    if config().llm_proveedor == "fake" and llm.fake.responder is None:
        if "revisar_ventana_despliegue" in herrs:
            guion = agente_ref._GuionSimulado(tarea)
        elif "buscar_logs" in herrs:
            guion = _guion_triage_fake(tarea)

    for n in range(1, max_pasos + 1):
        if guion is not None:
            prop = guion(mensaje)
            texto = json.dumps(prop, ensure_ascii=False)
        else:
            r = llm.generar(mensaje, sistema, json=True, historial=historial, etiqueta=f"a4/agente/paso{n}")
            prop = r.datos if isinstance(r.datos, dict) else {}
            texto = r.texto

        historial += [{"rol": "user", "texto": mensaje}, {"rol": "model", "texto": texto}]
        paso = Paso(n=n, propuesta=prop)
        pasos.append(paso)

        if prop.get("accion") == "responder":
            paso.estado = "respuesta"
            trazas.registrar("agente_a4", paso=n, estado=paso.estado)
            return ResultadoAgente(str(prop.get("respuesta", "")), list(prop.get("fuentes", [])), pasos, terminado=True)

        nombre_h = prop.get("herramienta", "")
        h = herrs.get(nombre_h)
        if prop.get("accion") != "usar" or h is None:
            paso.estado = "invalida"
            mensaje = f"Acción inválida. Usa una herramienta de {list(herrs)} o responde."
            trazas.registrar("agente_a4", paso=n, herramienta=nombre_h, estado=paso.estado)
            continue

        args = prop.get("argumentos")
        if not isinstance(args, dict):
            paso.estado = "invalida"
            mensaje = f"Los argumentos para {h.nombre} deben ser un objeto JSON."
            trazas.registrar("agente_a4", paso=n, herramienta=h.nombre, estado=paso.estado)
            continue

        errores = [e.message for e in jsonschema.Draft202012Validator(h.esquema).iter_errors(args)]
        if errores:
            paso.estado = "invalida"
            mensaje = f"Argumentos inválidos para {h.nombre}: {errores[:3]}"
            trazas.registrar("agente_a4", paso=n, herramienta=h.nombre, estado=paso.estado)
            continue

        firma = (h.nombre, json.dumps(args, sort_keys=True, ensure_ascii=False))
        if firma in vistos:
            paso.estado = "repetida"
            mensaje = f"Ya ejecutaste {h.nombre} con esos argumentos exactos. Usa ese resultado o responde."
            trazas.registrar("agente_a4", paso=n, herramienta=h.nombre, estado=paso.estado)
            continue

        if h.sensible:
            decision = confirmar(h, args) if confirmar else False
            if decision is not True:
                paso.estado = "sin_confirmar" if decision is None else "rechazada"
                mensaje = (
                    f"{h.nombre}({args}) quedó PENDIENTE de autorización humana. Informa al usuario y responde."
                    if decision is None
                    else f"La persona NO confirmó {h.nombre}({args}). No la ejecutes; responde explicando."
                )
                trazas.registrar("agente_a4", paso=n, herramienta=h.nombre, estado=paso.estado)
                continue

        vistos.add(firma)
        try:
            paso.resultado = h.funcion(**args)
        except Exception as exc:
            paso.resultado = f"ERROR: {exc}"
        paso.estado = "ejecutada"
        mensaje = f"Resultado de {h.nombre}: {json.dumps(paso.resultado, ensure_ascii=False, default=str)[:3000]}"
        trazas.registrar("agente_a4", paso=n, herramienta=h.nombre, estado=paso.estado)

    return ResultadoAgente("No pude completar la tarea en el número máximo de pasos.", [], pasos, terminado=False)


# ─── HERRAMIENTAS DE LA VARIANTE v5-triage (A4) ───

_LOGS_BASE = [
    {"ts": "2026-11-24T10:05:12", "servicio": "pagos-api", "nivel": "ERROR",
     "msg": "Timeout 504 contra gateway-spei cliente juan.perez@correo.mx CLABE 012180001234567890"},
    {"ts": "2026-11-24T10:18:44", "servicio": "pagos-api", "nivel": "ERROR",
     "msg": "Pool de conexiones PostgreSQL agotado (100/100) en cluster-pagos-01"},
    {"ts": "2026-11-24T11:30:00", "servicio": "auth-service", "nivel": "WARN",
     "msg": "Incremento de latencia p99=1450ms en validación de tokens"},
]


def _parsear_iso(valor: str) -> datetime:
    return datetime.fromisoformat(valor.replace("Z", "+00:00"))


def buscar_logs(desde: str, hasta: str, patron: str) -> dict:
    """Consulta logs en una ventana máxima de 2 horas y enmascara PII antes de devolverlos."""
    t_inicio = _parsear_iso(desde)
    t_fin = _parsear_iso(hasta)
    if t_fin < t_inicio:
        raise ValueError("El parámetro 'hasta' debe ser posterior o igual a 'desde'.")
    diferencia_horas = (t_fin - t_inicio).total_seconds() / 3600.0
    if diferencia_horas > 2.0:
        raise ValueError(f"La ventana de consulta ({diferencia_horas:.2f}h) excede el máximo permitido de 2 horas.")

    pat = patron.strip().lower()
    coincidencias = []
    for entrada in _LOGS_BASE:
        ts_log = _parsear_iso(entrada["ts"])
        if t_inicio <= ts_log <= t_fin:
            texto_completo = f"{entrada['ts']} [{entrada['nivel']}] {entrada['servicio']}: {entrada['msg']}"
            if not pat or pat in texto_completo.lower():
                enmascarado, _ = pii.enmascarar(texto_completo)
                coincidencias.append(enmascarado)

    return {"ventana_horas": round(diferencia_horas, 2), "total": len(coincidencias), "logs": coincidencias, "fuente": "logs-operativos"}


def consultar_runbooks_triage(consulta: str) -> dict:
    """Busca procedimientos y severidades en el corpus v5-triage."""
    idx = Indice.desde_carpeta(RAIZ / "corpus" / "v5-triage")
    res = idx.buscar(consulta, k=3)
    return {
        "resultados": [
            {"doc_id": r.fragmento.doc_id, "puntaje": round(r.puntaje, 3), "texto": r.fragmento.texto[:450]}
            for r in res
        ]
    }


def crear_ticket_incidente(servicio: str, severidad: str, resumen: str, runbook: str) -> dict:
    """Herramienta SENSIBLE: registra un ticket de incidente de producción (requiere confirmación humana)."""
    return {
        "ticket_id": f"INC-{abs(hash((servicio, severidad, resumen))) % 90000 + 10000}",
        "servicio": servicio,
        "severidad": severidad,
        "resumen": resumen,
        "runbook": runbook,
        "estado": "ABIERTO",
    }


def herramientas_triage() -> list[Herramienta]:
    return [
        Herramienta(
            nombre="buscar_logs",
            descripcion="Busca eventos en logs operativos en una ventana máxima de 2 horas (enmascara PII automáticamente).",
            esquema={
                "type": "object",
                "required": ["desde", "hasta", "patron"],
                "additionalProperties": False,
                "properties": {
                    "desde": {"type": "string", "description": "Timestamp ISO-8601 inicial (ej. 2026-11-24T10:00:00)"},
                    "hasta": {"type": "string", "description": "Timestamp ISO-8601 final, máximo 2h después (ej. 2026-11-24T11:30:00)"},
                    "patron": {"type": "string", "description": "Texto o nivel a filtrar (ej. ERROR, pagos-api)"},
                },
            },
            funcion=buscar_logs,
            sensible=False,
        ),
        Herramienta(
            nombre="consultar_runbooks_triage",
            descripcion="Consulta los runbooks y políticas de severidad del corpus v5-triage (rb-01, rb-02, etc.).",
            esquema={
                "type": "object",
                "required": ["consulta"],
                "additionalProperties": False,
                "properties": {
                    "consulta": {"type": "string", "minLength": 3},
                },
            },
            funcion=consultar_runbooks_triage,
            sensible=False,
        ),
        Herramienta(
            nombre="crear_ticket_incidente",
            descripcion="Crea un ticket oficial de incidente P1/P2/P3 tras confirmar evidencia en logs y runbook.",
            esquema={
                "type": "object",
                "required": ["servicio", "severidad", "resumen", "runbook"],
                "additionalProperties": False,
                "properties": {
                    "servicio": {"type": "string", "minLength": 2},
                    "severidad": {"type": "string", "enum": ["P1", "P2", "P3"]},
                    "resumen": {"type": "string", "minLength": 5},
                    "runbook": {"type": "string", "pattern": "^rb-\\d+"},
                },
            },
            funcion=crear_ticket_incidente,
            sensible=True,
        ),
    ]


def validar_plan_triage(resultado: ResultadoAgente, propuestas: list[tuple[str, dict]]) -> list[str]:
    """Validador determinista de lógica tradicional para v5-triage (y compatibilidad con caso guía)."""
    from .agente_servicio import validar_plan as validar_plan_guia

    hallazgos = validar_plan_guia(resultado, propuestas)
    logs_ok = any(
        p.propuesta.get("herramienta") == "buscar_logs"
        and p.estado == "ejecutada"
        and isinstance(p.resultado, dict)
        and p.resultado.get("total", 0) > 0
        for p in resultado.pasos
    )
    runbooks_ok = any(
        p.propuesta.get("herramienta") == "consultar_runbooks_triage"
        and p.estado == "ejecutada"
        for p in resultado.pasos
    )

    for nombre, args in propuestas:
        if nombre != "crear_ticket_incidente":
            continue
        if not logs_ok:
            hallazgos.append("Regla v5-triage: debes ejecutar buscar_logs y encontrar evidencia antes de crear un ticket.")
        if args.get("severidad") == "P1" and not runbooks_ok:
            hallazgos.append("Regla v5-triage: los incidentes P1 requieren consultar runbooks antes de abrir ticket.")
    return hallazgos