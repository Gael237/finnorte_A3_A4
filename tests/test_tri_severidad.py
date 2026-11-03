import pytest

from finnorte.reglas_tri_severidad import (
    BOOLEANOS, NUMERICOS, validar_severidad,
)


def senales(**cambios):
    indicadores = {clave: None for clave in (*BOOLEANOS, *NUMERICOS)}
    indicadores.update(cambios)
    return {"senales": {"indicadores": indicadores}}


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