import json

import jsonschema

from finnorte import llm, prompts
from finnorte.reglas_tri_acciones import validar_acciones
from finnorte.variante import FLUJO, FLUJO_V1

INDICADORES = {
    "transferencias_caidas_todos": None,
    "acceso_caido_todos": None,
    "exposicion_datos": None,
    "falla_componente_critico": None,
    "alternativa_disponible": None,
    "falla_parcial_sin_impacto_dinero": None,
    "problema_menor": None,
    "p95_transferencias_s": 3.4,
    "duracion_p95_sobre_3s_min": 11,
    "errores_5xx_pct": 7,
}
SENALES = {
    "eventos": [
        {"hora": "10:00", "descripcion": "Inicio de degradacion de pagos-api"},
        {"hora": "10:01", "descripcion": "Alerta de latencia p95 en pagos-api"},
        {"hora": "10:02", "descripcion": "Errores 5xx en transferencias: 7%"},
    ],
    "indicadores": INDICADORES,
    "faltantes": [],
    "fuentes" : []
}
SEVERIDAD = {
    "nivel": "SEV2",
    "criterio_rb01": "p95 superior a 3 segundos por mas de 10 minutos",
    "justificacion": "El log de prueba informa 3.4 segundos durante 11 minutos.",
    "fuente": "rb-01",
}
ACCIONES = {
    "acciones": [{
        "descripcion": "Comparar la latencia p95 con los despliegues de pagos-api de los ultimos 60 minutos.",
        "runbook": "rb-02",
    }],
    "faltantes": [],
}
POSTMORTEM = {
    "resumen": {
        "descripcion": "Degradacion de transferencias por latencia y errores 5xx.",
        "duracion": "INFORMACION FALTANTE: no se registro la resolucion.",
        "severidad": "SEV2",
        "impacto": "La tasa observada de errores 5xx fue 7%.",
    },
    "linea_tiempo": [
        {"hora": "2026-11-04T10:00:00Z", "evento": "Inicio de degradacion de pagos-api."},
        {"hora": "2026-11-04T10:01:00Z", "evento": "Alerta de latencia p95 en pagos-api."},
        {"hora": "2026-11-04T10:02:00Z", "evento": "La tasa de errores 5xx llega a 7%."},
    ],
    "causa_raiz": {
        "tecnica": "Las señales muestran latencia p95 elevada y errores 5xx.",
        "proceso": "No hay evidencia suficiente para confirmar una causa de proceso.",
    },
    "deteccion": {
        "como": "Alerta de latencia p95.",
        "tiempo_deteccion": "1 minuto desde el inicio registrado.",
        "gaps_observabilidad": "No se informo si habia alerta previa a la degradacion.",
    },
    "respuesta": {
        "que_funciono": ["Se registro una alerta de latencia p95."],
        "que_no_funciono": ["Informacion faltante: no hay datos de mitigacion."],
    },
    "acciones": [
        {
            "descripcion": "Analizar las consultas lentas y ajustar el pool tras validar la capacidad.",
            "tipo": "correctiva",
            "responsable": "equipo de pagos-api",
            "fecha_estimada": "POR CONFIRMAR",
            "metrica_exito": "Pool estable bajo el umbral acordado durante una semana.",
            "criterio_aceptacion": "Prueba de carga aprobada y cambio revisado por operaciones.",
        },
        {
            "descripcion": "Agregar una alerta proactiva para latencia p95 elevada.",
            "tipo": "preventiva",
            "responsable": "equipo de SRE",
            "fecha_estimada": "POR CONFIRMAR",
            "metrica_exito": "Alerta visible en menos de un minuto al superar el umbral.",
            "criterio_aceptacion": "Alerta probada y runbook actualizado para guardias.",
        },
    ],
    "lecciones": [
        "Las alertas de latencia deben contar con umbrales previos a errores 5xx.",
        "Registrar la mitigacion permite medir la duracion total del incidente.",
    ],
}
RESPUESTAS_VALIDAS = [SENALES, SEVERIDAD, ACCIONES, POSTMORTEM]


def test_flujo_lab2_encadena_cuatro_etapas_y_valida_sus_esquemas(monkeypatch):
    respuestas = list(RESPUESTAS_VALIDAS)
    prompts_llm = []

    def responder(prompt, sistema):
        prompts_llm.append(prompt)
        return json.dumps(respuestas.pop(0), ensure_ascii=False)

    monkeypatch.setattr(llm.fake, "responder", responder)
    res = FLUJO.ejecutar({"entrada": "Log simulado: alerta de latencia p95 y errores 5xx."})

    assert res.ok, [etapa.errores for etapa in res.etapas]
    assert [etapa.nombre for etapa in res.etapas] == ["senales", "severidad", "acciones", "postmortem"]
    assert set(res.salidas) == {"senales", "severidad", "acciones", "postmortem"}
    assert respuestas == []
    for etapa in FLUJO.etapas:
        jsonschema.validate(res.salidas[etapa.nombre], prompts.cargar(etapa.prompt, etapa.version).esquema)

    assert "Alerta de latencia p95 en pagos-api" in prompts_llm[1]
    assert '"nivel": "SEV2"' in prompts_llm[2]
    assert "rb-02" in prompts_llm[3]
    assert "Alerta de latencia p95 en pagos-api" in prompts_llm[3]
    assert "faltantes" in res.salidas["acciones"]


def test_flujo_lab2_se_detiene_ante_severidad_fuera_de_esquema(monkeypatch):
    respuestas = [SENALES, {**SEVERIDAD, "nivel": "SEV5"}, {**SEVERIDAD, "nivel": "SEV5"}]
    llamadas = []

    def responder(prompt, sistema):
        llamadas.append(prompt)
        return json.dumps(respuestas.pop(0), ensure_ascii=False)

    monkeypatch.setattr(llm.fake, "responder", responder)
    res = FLUJO.ejecutar({"entrada": "Log simulado de prueba."})

    assert res.ok is False
    assert [etapa.nombre for etapa in res.etapas] == ["senales", "severidad"]
    assert res.etapas[0].ok is True
    assert res.etapas[1].ok is False
    assert "acciones" not in res.salidas and "postmortem" not in res.salidas
    assert len(llamadas) == 3


def test_etapas_y_flujo_v1_adaptan_faltantes_string(monkeypatch):
    assert [etapa.nombre for etapa in FLUJO_V1.etapas] == ["senales", "severidad", "acciones", "postmortem"]
    etapa_acciones_v1 = FLUJO_V1.etapas[2]
    assert etapa_acciones_v1.version == 1
    assert etapa_acciones_v1.validar is not validar_acciones
    previas = {"senales": SENALES, "severidad": SEVERIDAD}
    salida_v1 = {
        "acciones": [{
            "descripcion": "Comparar latencia p95 con los despliegues recientes de pagos-api.",
            "runbook": "rb-02",
        }],
        "faltantes": "",
    }
    assert etapa_acciones_v1.validar(salida_v1, previas) == []
