import json

from conftest import pendiente

import pytest

from finnorte import llm
from finnorte.herramientas import (
    Herramienta,
    buscar_logs,
    ejecutar_agente,
    herramientas_triage,
    validar_plan_triage,
)

SUMA = Herramienta(
    "sumar",
    "Suma dos números",
    {"type": "object", "required": ["a", "b"], "properties": {"a": {"type": "number"}, "b": {"type": "number"}}},
    lambda a, b: a + b,
)
BORRAR = Herramienta(
    "borrar_rama",
    "Borra una rama remota",
    {"type": "object", "required": ["rama"], "properties": {"rama": {"type": "string"}}},
    lambda rama: f"borrada {rama}",
    sensible=True,
)


def _guion(*respuestas):
    it = iter(respuestas)
    return lambda p, s, **kw: json.dumps(next(it))


@pendiente("A4")
def test_agente_usa_herramienta_y_responde():
    llm.fake.responder = _guion(
        {"accion": "usar", "herramienta": "sumar", "argumentos": {"a": 2, "b": 3}},
        {"accion": "responder", "respuesta": "Es 5", "fuentes": []},
    )
    r = ejecutar_agente("¿Cuánto es 2+3?", [SUMA])
    assert r.respuesta == "Es 5" and r.pasos[0].resultado == 5


@pendiente("A4")
def test_herramienta_sensible_sin_confirmacion_no_se_ejecuta():
    ejecutadas = []
    h = Herramienta("borrar_rama", BORRAR.descripcion, BORRAR.esquema, lambda rama: ejecutadas.append(rama), sensible=True)
    llm.fake.responder = _guion(
        {"accion": "usar", "herramienta": "borrar_rama", "argumentos": {"rama": "main"}},
        {"accion": "responder", "respuesta": "No se borró", "fuentes": []},
    )
    r = ejecutar_agente("Borra main", [h], confirmar=lambda h, a: False)
    assert ejecutadas == [] and r.pasos[0].estado == "rechazada"


@pendiente("A4")
def test_herramienta_inexistente_es_invalida_y_hay_tope_de_pasos():
    llm.fake.responder = lambda p, s, **kw: json.dumps({"accion": "usar", "herramienta": "hackear", "argumentos": {}})
    r = ejecutar_agente("x", [SUMA], max_pasos=3)
    assert not r.terminado and len(r.pasos) == 3 and all(p.estado == "invalida" for p in r.pasos)

def test_a4_buscar_logs_falla_controlada_mas_de_2h_y_enmascara_pii():
    # Falla controlada si ventana > 2 horas
    with pytest.raises(ValueError, match="2 horas"):
        buscar_logs("2026-11-24T08:00:00", "2026-11-24T11:30:00", "ERROR")

    # Ventana válida <= 2h enmascara correo y CLABE
    res = buscar_logs("2026-11-24T10:00:00", "2026-11-24T11:00:00", "ERROR")
    assert res["total"] >= 1
    texto = " ".join(res["logs"])
    assert "juan.perez@correo.mx" not in texto
    assert "012180001234567890" not in texto
    assert "<CORREO_1>" in texto and "<CLABE_1>" in texto


def test_a4_validador_bloquea_ticket_sin_logs_previos():
    llm.fake.responder = _guion(
        {
            "accion": "usar",
            "herramienta": "crear_ticket_incidente",
            "argumentos": {"servicio": "pagos-api", "severidad": "P1", "resumen": "Caída total", "runbook": "rb-01"},
        },
        {"accion": "responder", "respuesta": "Pendiente", "fuentes": ["rb-01"]},
    )
    propuestas = []
    r = ejecutar_agente(
        "Abre ticket P1 directo",
        herramientas_triage(),
        confirmar=lambda h, a: propuestas.append((h.nombre, a)) or None,
    )
    hallazgos = validar_plan_triage(r, propuestas)
    assert len(hallazgos) >= 1
    assert any("buscar_logs" in h for h in hallazgos)