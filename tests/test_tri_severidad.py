import pytest

from finnorte.reglas_tri_severidad import (
    BOOLEANOS, NUMERICOS, validar_severidad,
)
from finnorte.config import RAIZ


def senales(**cambios):
    indicadores = {clave: None for clave in (*BOOLEANOS, *NUMERICOS)}
    indicadores.update(cambios)
    eventos = []
    if cambios.get("transferencias_caidas_todos") is True:
        eventos.append({"hora": "00:00", "descripcion": "Todas las transferencias están caídas"})
    log_original = "Todas las transferencias están caídas" if cambios.get("transferencias_caidas_todos") is True else ""
    return {
        "senales": {"indicadores": indicadores, "eventos": eventos},
        "_entrada_original": {"entrada": log_original},
    }


@pytest.mark.parametrize(
    ("indicadores", "nivel"),
    [
        ({"transferencias_caidas_todos": True}, "SEV1"),
        ({"exposicion_datos": True, "errores_5xx_pct": 8}, "SEV1"),
        ({"p95_transferencias_s": 3.5,
          "duracion_p95_sobre_3s_min": 11}, "SEV2"),
        ({"errores_5xx_pct": 5.1}, "SEV2"),
        ({"falla_componente_critico": True,
          "alternativa_disponible": True}, "SEV2"),
        ({"falla_parcial_sin_impacto_dinero": True}, "SEV3"),
        ({"problema_menor": True}, "SEV4"),
    ],
)
def test_clasifica_segun_rb01(indicadores, nivel):
    assert validar_severidad({"nivel": nivel}, senales(**indicadores)) == []


def test_rechaza_un_nivel_incorrecto():
    errores = validar_severidad(
        {"nivel": "SEV4"}, senales(errores_5xx_pct=8)
    )
    assert errores and "SEV2" in errores[0]


def test_no_inventa_severidad_si_no_hay_evidencia():
    assert validar_severidad({"nivel": "SEV4"}, senales())


def test_inc02_rechaza_evento_inventado_de_alcance_total_contra_log_original():
    log_original = (RAIZ / "datos/v5-triage/logs/inc-02-tls.log").read_text(encoding="utf-8")
    salida_senales = {
        "indicadores": {
            clave: None for clave in (*BOOLEANOS, *NUMERICOS)
        },
        "eventos": [
            {"hora": "00:00", "descripcion": "Falla el envío SPEI de trf_77 (reintento=1)"},
            {"hora": "00:01", "descripcion": "Alerta: spei.envios_fallidos=100%"},
            {"hora": "00:01", "descripcion": "Todas las transferencias SPEI están caídas"},
        ],
    }
    salida_senales["indicadores"].update({
        "transferencias_caidas_todos": True,
        "falla_componente_critico": True,
        "falla_parcial_sin_impacto_dinero": False,
        "problema_menor": False,
    })

    errores = validar_severidad(
        {"nivel": "SEV1"},
        {"senales": salida_senales, "_entrada_original": {"entrada": log_original}},
    )

    assert errores == [
        "transferencias_caidas_todos=true requiere evidencia explícita de alcance total en el log original; "
        "un evento generado por el modelo no demuestra ese alcance"
    ]


def test_log_con_alcance_total_explicito_permite_evaluar_sev1():
    salida = senales(transferencias_caidas_todos=True)

    assert validar_severidad({"nivel": "SEV1"}, salida) == []
