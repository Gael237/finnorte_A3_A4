import json
import jsonschema

from finnorte import llm, prompts
from finnorte.pipeline import Etapa, Pipeline
from finnorte.reglas_tri_acciones import validar_acciones
from finnorte.reglas_tri_severidad import BOOLEANOS, NUMERICOS
from finnorte.variante import ETAPA_ACCIONES

INDICADORES = {clave: None for clave in (*BOOLEANOS, *NUMERICOS)}
INDICADORES.update({"p95_transferencias_s": 1.2, "errores_5xx_pct": 0.2})
SENALES = {"eventos": [{"hora": "10:00", "descripcion": "Alerta de latencia p95 en pagos-api"}], "indicadores": INDICADORES, "faltantes": []}
SEVERIDAD = {"nivel": "SEV2", "criterio_rb01": "Latencia p95 por encima del umbral", "justificacion": "La señal reporta latencia p95; falta confirmar duración.", "fuente": "rb-01"}
SALIDA_VALIDA = {"acciones": [{"descripcion": "Comparar la latencia p95 de pagos-api con el despliegue de los últimos 60 minutos.", "runbook": "rb-02"}], "faltantes": ["Confirmar si hubo un despliegue en los últimos 60 minutos."]}

def _flujo_aislado(monkeypatch, salida):
    """Prueba Pipeline.ejecutar con usa=[] y contexto de negocio explícito."""
    monkeypatch.setattr(llm.fake, "responder", lambda prompt, sistema: json.dumps(salida))
    validar_con_contexto = lambda datos, previas: validar_acciones(datos, {"senales": SENALES, "severidad": SEVERIDAD})
    etapa = Etapa("acciones", "tri_acciones", version=2, usa=[], validar=validar_con_contexto, reintentos=0)
    entrada = {"senales": json.dumps(SENALES), "severidad": json.dumps(SEVERIDAD)}
    return Pipeline([etapa], nombre="acciones-aislada").ejecutar(entrada)

def test_pipeline_ejecuta_acciones_con_json_valido(monkeypatch):
    res = _flujo_aislado(monkeypatch, SALIDA_VALIDA)
    assert res.ok is True
    assert res.salidas["acciones"] == SALIDA_VALIDA
    jsonschema.validate(res.salidas["acciones"], prompts.cargar("tri_acciones", 2).esquema)

def test_pipeline_rechaza_runbook_catalogo_rb01(monkeypatch):
    salida = {"acciones": [{"descripcion": "Revisar la latencia p95 de pagos-api y compararla con el umbral.", "runbook": "rb-01"}], "faltantes": []}
    res = _flujo_aislado(monkeypatch, salida)
    assert res.ok is False
    assert any("runbook" in error.lower() for error in res.etapas[0].errores)

def test_pipeline_rechaza_accion_destructiva(monkeypatch):
    salida = {"acciones": [{"descripcion": "Reiniciar todos los pods de pagos-api para recuperar el servicio.", "runbook": "rb-02"}], "faltantes": []}
    res = _flujo_aislado(monkeypatch, salida)
    assert res.ok is False
    assert any("destructiva" in error.lower() for error in res.etapas[0].errores)


def test_rechaza_rb02_si_eventos_vacios_e_indicadores_none():
    senales_sin_observaciones = {
        "eventos": [],
        "indicadores": {clave: None for clave in (*BOOLEANOS, *NUMERICOS)},
        "faltantes": [],
    }
    errores = validar_acciones(
        SALIDA_VALIDA,
        {"senales": senales_sin_observaciones, "severidad": SEVERIDAD},
    )
    assert any("rb-02" in error and "sustentado" in error for error in errores)



def test_rechaza_rb02_si_p95_es_menor_o_igual_a_3_sin_eventos():
    indicadores = {clave: None for clave in (*BOOLEANOS, *NUMERICOS)}
    indicadores["p95_transferencias_s"] = 1.2
    senales_sin_alerta = {"eventos": [], "indicadores": indicadores, "faltantes": []}
    errores = validar_acciones(
        SALIDA_VALIDA,
        {"senales": senales_sin_alerta, "severidad": SEVERIDAD},
    )
    assert any("rb-02" in error and "sustentado" in error for error in errores)


def test_pipeline_exige_faltantes_si_no_hay_evidencia(monkeypatch):
    senales = {"eventos": [], "indicadores": INDICADORES, "faltantes": []}
    monkeypatch.setattr(llm.fake, "responder", lambda prompt, sistema: json.dumps({"acciones": [], "faltantes": []}))
    etapa = Etapa("acciones", "tri_acciones", version=2, usa=[], validar=lambda datos, previas: validar_acciones(datos, {"senales": senales, "severidad": SEVERIDAD}), reintentos=0)
    res = Pipeline([etapa]).ejecutar({"senales": json.dumps(senales), "severidad": json.dumps(SEVERIDAD)})
    assert res.ok is False
    assert any("faltantes" in error for error in res.etapas[0].errores)

def test_prompt_v2_carga_renderiza_y_etapa_completa_declara_dependencias():
    prompt = prompts.cargar("tri_acciones")
    sistema, usuario = prompt.render(senales=json.dumps(SENALES), severidad=json.dumps(SEVERIDAD))
    assert prompt.version == 2
    assert prompt.meta["cambios"].startswith("v2")
    assert "rb-08" in sistema and "faltantes" in usuario
    assert ETAPA_ACCIONES.usa == ["senales", "severidad"]
    assert ETAPA_ACCIONES.prompt == "tri_acciones"
    assert ETAPA_ACCIONES.version == 2
