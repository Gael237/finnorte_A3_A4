"""Pruebas dirigidas para validar las reglas de tri_postmortem (A2 · Axel)."""
import pytest
from finnorte import prompts
from finnorte.reglas_tri_postmortem import validar_postmortem


class TestDeteccionDatosPersonales:
    """Pruebas para la detección de datos personales (PII)."""

    def test_detecta_señor_juan_mayusculas(self):
        """Detecta 'Señor Juan' con mayúsculas."""
        salida = {
            "resumen": {"descripcion": "Incidente reportado por Señor Juan", "duracion": "5 min", "severidad": "SEV2", "impacto": "ninguno"},
            "linea_tiempo": [{"hora": "2026-10-20T13:00:00Z", "evento": "inicio"}],
            "causa_raiz": {"tecnica": "error de red", "proceso": "falta monitoreo"},
            "deteccion": {"como": "manual", "tiempo_deteccion": "5 min"},
            "respuesta": {"que_funciono": ["logs"], "que_no_funciono": []},
            "acciones": [],
            "lecciones": ["revisar logs", "mejorar alertas"]
        }
        errores = validar_postmortem(salida, {"severidad": {"nivel": "SEV2"}})
        assert any("tratamiento personal" in e for e in errores), f"No detectó 'Señor Juan': {errores}"

    def test_detecta_señor_juan_minusculas(self):
        """Detecta 'señor juan' con minúsculas."""
        salida = {
            "resumen": {"descripcion": "Incidente reportado por señor juan", "duracion": "5 min", "severidad": "SEV2", "impacto": "ninguno"},
            "linea_tiempo": [{"hora": "2026-10-20T13:00:00Z", "evento": "inicio"}],
            "causa_raiz": {"tecnica": "error de red", "proceso": "falta monitoreo"},
            "deteccion": {"como": "manual", "tiempo_deteccion": "5 min"},
            "respuesta": {"que_funciono": ["logs"], "que_no_funciono": []},
            "acciones": [],
            "lecciones": ["revisar logs", "mejorar alertas"]
        }
        errores = validar_postmortem(salida, {"severidad": {"nivel": "SEV2"}})
        assert any("tratamiento personal" in e for e in errores), f"No detectó 'señor juan': {errores}"

    def test_detecta_correo_electronico(self):
        """Detecta correos electrónicos."""
        salida = {
            "resumen": {"descripcion": "Contacto juan.perez@example.com", "duracion": "5 min", "severidad": "SEV2", "impacto": "ninguno"},
            "linea_tiempo": [{"hora": "2026-10-20T13:00:00Z", "evento": "inicio"}],
            "causa_raiz": {"tecnica": "error de red", "proceso": "falta monitoreo"},
            "deteccion": {"como": "manual", "tiempo_deteccion": "5 min"},
            "respuesta": {"que_funciono": ["logs"], "que_no_funciono": []},
            "acciones": [],
            "lecciones": ["revisar logs", "mejorar alertas"]
        }
        errores = validar_postmortem(salida, {"severidad": {"nivel": "SEV2"}})
        assert any("correo electrónico" in e for e in errores), f"No detectó correo: {errores}"

    def test_detecta_correo_sin_punto_en_usuario(self):
        """Detecta correos cuyo usuario no contiene punto."""
        salida = {"resumen": {"descripcion": "Contacto cliente@gmail.com", "severidad": "SEV2"}}
        errores = validar_postmortem(salida, {"severidad": {"nivel": "SEV2"}})
        assert any("correo" in e.lower() for e in errores), f"No detect? correo Gmail: {errores}"

    def test_detecta_telefono(self):
        """Detecta números de teléfono."""
        salida = {
            "resumen": {"descripcion": "Llamar al 555-123-4567", "duracion": "5 min", "severidad": "SEV2", "impacto": "ninguno"},
            "linea_tiempo": [{"hora": "2026-10-20T13:00:00Z", "evento": "inicio"}],
            "causa_raiz": {"tecnica": "error de red", "proceso": "falta monitoreo"},
            "deteccion": {"como": "manual", "tiempo_deteccion": "5 min"},
            "respuesta": {"que_funciono": ["logs"], "que_no_funciono": []},
            "acciones": [],
            "lecciones": ["revisar logs", "mejorar alertas"]
        }
        errores = validar_postmortem(salida, {"severidad": {"nivel": "SEV2"}})
        assert any("teléfono" in e for e in errores), f"No detectó teléfono: {errores}"

    def test_detecta_clabe(self):
        """Detecta CLABEs (18 dígitos)."""
        salida = {
            "resumen": {"descripcion": "Transferencia a 012345678901234567", "duracion": "5 min", "severidad": "SEV2", "impacto": "ninguno"},
            "linea_tiempo": [{"hora": "2026-10-20T13:00:00Z", "evento": "inicio"}],
            "causa_raiz": {"tecnica": "error de red", "proceso": "falta monitoreo"},
            "deteccion": {"como": "manual", "tiempo_deteccion": "5 min"},
            "respuesta": {"que_funciono": ["logs"], "que_no_funciono": []},
            "acciones": [],
            "lecciones": ["revisar logs", "mejorar alertas"]
        }
        errores = validar_postmortem(salida, {"severidad": {"nivel": "SEV2"}})
        assert any("CLABE" in e for e in errores), f"No detectó CLABE: {errores}"

    def test_no_falso_positivo_sin_datos_personales(self):
        """No genera falsos positivos cuando no hay datos personales."""
        salida = {
            "resumen": {"descripcion": "Pool de conexiones saturado", "duracion": "5 min", "severidad": "SEV2", "impacto": "27% errores"},
            "linea_tiempo": [{"hora": "2026-10-20T13:00:00Z", "evento": "inicio"}],
            "causa_raiz": {"tecnica": "pool pequeño", "proceso": "falta capacity planning"},
            "deteccion": {"como": "alerta", "tiempo_deteccion": "3 min"},
            "respuesta": {"que_funciono": ["alerta"], "que_no_funciono": []},
            "acciones": [
                {"descripcion": "Incrementar pool", "tipo": "correctiva", "responsable": "SRE", "fecha_estimada": "2026-10-21"},
                {"descripcion": "Agregar monitoreo", "tipo": "preventiva", "responsable": "SRE", "fecha_estimada": "2026-10-28"}
            ],
            "lecciones": ["monitorear recursos", "capacity planning"]
        }
        errores = validar_postmortem(salida, {"severidad": {"nivel": "SEV2"}})
        pii_errors = [e for e in errores if "dato personal" in e]
        assert not any("correo" in e.lower() for e in errores), f"Falso positivo de correo: {errores}"
        assert not pii_errors, f"Falsos positivos de PII: {pii_errors}"


class TestValidacionEsquemas:
    """Pruebas para validar que los esquemas v1 y v2 funcionan correctamente."""

    def test_postmortem_v1_valido_pasa_esquema_y_reglas(self):
        """Un postmortem v1 completo pasa validación de esquema y reglas de negocio."""
        import json
        from pathlib import Path
        from finnorte.config import RAIZ
        import jsonschema

        # Cargar esquema v1
        esquema_v1 = json.loads((RAIZ / "prompts/esquemas/tri_postmortem.schema.json").read_text(encoding="utf-8"))

        salida_v1 = {
            "resumen": {
                "descripcion": "Pool de conexiones saturado causando timeouts",
                "duracion": "INFORMACIÓN FALTANTE",
                "severidad": "SEV2",
                "impacto": "27% de errores registrados"
            },
            "linea_tiempo": [
                {"hora": "2026-10-20T13:00:00Z", "evento": "Despliegue de pagos-api v4.19"},
                {"hora": "2026-10-20T13:05:00Z", "evento": "Primera alerta de uso alto del pool"},
                {"hora": "2026-10-20T13:10:00Z", "evento": "Inicio de errores TimeoutError"}
            ],
            "causa_raiz": {
                "tecnica": "Pool configurado con límite bajo insuficiente para carga",
                "proceso": "Falta proceso de capacity planning regular"
            },
            "deteccion": {
                "como": "Alerta automática de tasa de errores",
                "tiempo_deteccion": "5 minutos desde primer error"
            },
            "respuesta": {
                "que_funciono": ["Alerta automática detectó el problema rápidamente"],
                "que_no_funciono": ["No había alerta proactiva de uso de pool"]
            },
            "acciones": [
                {
                    "descripcion": "Solicitar aprobación del DBA antes de ajustar el límite del pool según métricas verificadas",
                    "tipo": "correctiva",
                    "responsable": "equipo SRE",
                    "fecha_estimada": "2026-10-21"
                },
                {
                    "descripcion": "Agregar monitoreo proactivo de uso de pool al 80%",
                    "tipo": "preventiva",
                    "responsable": "equipo SRE",
                    "fecha_estimada": "2026-10-28"
                }
            ],
            "lecciones": [
                "Monitorear recursos antes de saturación previene incidentes",
                "Implementar capacity planning mensual para servicios críticos"
            ]
        }

        # Validar contra esquema v1
        try:
            jsonschema.validate(instance=salida_v1, schema=esquema_v1)
        except jsonschema.ValidationError as e:
            pytest.fail(f"Postmortem v1 válido falló esquema: {e.message}")

        # Validar reglas de negocio
        errores = validar_postmortem(salida_v1, {"severidad": {"nivel": "SEV2"}})
        assert not errores, f"Postmortem v1 válido no debería tener errores de negocio: {errores}"

    def test_postmortem_v2_sin_gaps_observabilidad_falla_esquema(self):
        """Un postmortem v2 sin gaps_observabilidad debe fallar validación de esquema."""
        import json
        from pathlib import Path
        from finnorte.config import RAIZ
        import jsonschema

        # Cargar esquema v2
        esquema_v2 = json.loads((RAIZ / "prompts/esquemas/tri_postmortem.v2.schema.json").read_text(encoding="utf-8"))

        salida_v2_sin_gaps = {
            "resumen": {
                "descripcion": "Pool de conexiones saturado",
                "duracion": "INFORMACIÓN FALTANTE",
                "severidad": "SEV2",
                "impacto": "27% errores"
            },
            "linea_tiempo": [
                {"hora": "2026-10-20T13:00:00Z", "evento": "Despliegue"},
                {"hora": "2026-10-20T13:05:00Z", "evento": "Alerta"},
                {"hora": "2026-10-20T13:10:00Z", "evento": "Errores"}
            ],
            "causa_raiz": {
                "tecnica": "Pool con límite bajo",
                "proceso": "Falta capacity planning"
            },
            "deteccion": {
                "como": "Alerta automática",
                "tiempo_deteccion": "5 minutos"
                # Falta gaps_observabilidad (requerido en v2)
            },
            "respuesta": {
                "que_funciono": ["Alerta funcionó"],
                "que_no_funciono": ["Detección tardía"]
            },
            "acciones": [
                {
                    "descripcion": "Incrementar pool",
                    "tipo": "correctiva",
                    "responsable": "SRE",
                    "fecha_estimada": "2026-10-21",
                    "metrica_exito": "Pool bajo 60% en pico",
                    "criterio_aceptacion": "Prueba de carga sin errores"
                },
                {
                    "descripcion": "Agregar monitoreo",
                    "tipo": "preventiva",
                    "responsable": "SRE",
                    "fecha_estimada": "2026-10-28",
                    "metrica_exito": "Alerta en menos de 1 minuto",
                    "criterio_aceptacion": "Implementado y probado"
                }
            ],
            "lecciones": [
                "Monitorear recursos proactivamente",
                "Implementar capacity planning"
            ]
        }

        # Debe fallar por falta de gaps_observabilidad
        with pytest.raises(jsonschema.ValidationError) as exc_info:
            jsonschema.validate(instance=salida_v2_sin_gaps, schema=esquema_v2)

        assert "gaps_observabilidad" in str(exc_info.value), \
            f"El esquema v2 debe rechazar ausencia de gaps_observabilidad: {exc_info.value}"

    def test_postmortem_v2_sin_metrica_exito_falla_esquema(self):
        """Un postmortem v2 sin metrica_exito en acciones debe fallar validación de esquema."""
        import json
        from pathlib import Path
        from finnorte.config import RAIZ
        import jsonschema

        # Cargar esquema v2
        esquema_v2 = json.loads((RAIZ / "prompts/esquemas/tri_postmortem.v2.schema.json").read_text(encoding="utf-8"))

        salida_v2_sin_metricas = {
            "resumen": {
                "descripcion": "Pool de conexiones saturado",
                "duracion": "INFORMACIÓN FALTANTE",
                "severidad": "SEV2",
                "impacto": "27% errores"
            },
            "linea_tiempo": [
                {"hora": "2026-10-20T13:00:00Z", "evento": "Despliegue"},
                {"hora": "2026-10-20T13:05:00Z", "evento": "Alerta"},
                {"hora": "2026-10-20T13:10:00Z", "evento": "Errores"}
            ],
            "causa_raiz": {
                "tecnica": "Pool con límite bajo",
                "proceso": "Falta capacity planning"
            },
            "deteccion": {
                "como": "Alerta automática",
                "tiempo_deteccion": "5 minutos",
                "gaps_observabilidad": "Falta alerta proactiva al 80% de uso"
            },
            "respuesta": {
                "que_funciono": ["Alerta funcionó"],
                "que_no_funciono": ["Detección tardía"]
            },
            "acciones": [
                {
                    "descripcion": "Incrementar pool",
                    "tipo": "correctiva",
                    "responsable": "SRE",
                    "fecha_estimada": "2026-10-21"
                    # Faltan metrica_exito y criterio_aceptacion (requeridos en v2)
                },
                {
                    "descripcion": "Agregar monitoreo",
                    "tipo": "preventiva",
                    "responsable": "SRE",
                    "fecha_estimada": "2026-10-28",
                    "metrica_exito": "Alerta en menos de 1 minuto",
                    "criterio_aceptacion": "Implementado y probado"
                }
            ],
            "lecciones": [
                "Monitorear recursos proactivamente",
                "Implementar capacity planning"
            ]
        }

        # Debe fallar por falta de metrica_exito y criterio_aceptacion en primera acción
        with pytest.raises(jsonschema.ValidationError) as exc_info:
            jsonschema.validate(instance=salida_v2_sin_metricas, schema=esquema_v2)

        error_msg = str(exc_info.value)
        assert "metrica_exito" in error_msg or "criterio_aceptacion" in error_msg, \
            f"El esquema v2 debe rechazar ausencia de metrica_exito/criterio_aceptacion: {exc_info.value}"


class TestValidacionSecciones:
    """Pruebas para validar secciones obligatorias."""

    def test_falta_seccion_resumen(self):
        """Detecta cuando falta la sección resumen."""
        salida = {
            "linea_tiempo": [{"hora": "2026-10-20T13:00:00Z", "evento": "inicio"}],
            "causa_raiz": {"tecnica": "error", "proceso": "falta proceso"},
            "deteccion": {"como": "manual", "tiempo_deteccion": "5 min"},
            "respuesta": {"que_funciono": ["logs"], "que_no_funciono": []},
            "acciones": [],
            "lecciones": ["leccion1", "leccion2"]
        }
        errores = validar_postmortem(salida, {})
        assert any("resumen" in e for e in errores), f"No detectó falta de resumen: {errores}"

    def test_campo_vacio_descripcion(self):
        """Detecta cuando el campo descripcion está vacío."""
        salida = {
            "resumen": {"descripcion": "", "duracion": "5 min", "severidad": "SEV2", "impacto": "ninguno"},
            "linea_tiempo": [{"hora": "2026-10-20T13:00:00Z", "evento": "inicio"}],
            "causa_raiz": {"tecnica": "error", "proceso": "falta proceso"},
            "deteccion": {"como": "manual", "tiempo_deteccion": "5 min"},
            "respuesta": {"que_funciono": ["logs"], "que_no_funciono": []},
            "acciones": [],
            "lecciones": ["leccion1", "leccion2"]
        }
        errores = validar_postmortem(salida, {"severidad": {"nivel": "SEV2"}})
        assert any("resumen.descripcion" in e and "vacío" in e for e in errores), f"No detectó descripcion vacía: {errores}"


class TestValidacionAcciones:
    """Pruebas para validar acciones correctivas y preventivas."""

    def test_falta_accion_correctiva(self):
        """Detecta cuando no hay acciones correctivas."""
        salida = {
            "resumen": {"descripcion": "Incidente", "duracion": "5 min", "severidad": "SEV2", "impacto": "ninguno"},
            "linea_tiempo": [{"hora": "2026-10-20T13:00:00Z", "evento": "inicio"}],
            "causa_raiz": {"tecnica": "error", "proceso": "falta proceso"},
            "deteccion": {"como": "manual", "tiempo_deteccion": "5 min"},
            "respuesta": {"que_funciono": ["logs"], "que_no_funciono": []},
            "acciones": [
                {"descripcion": "Agregar monitoreo", "tipo": "preventiva", "responsable": "SRE", "fecha_estimada": "2026-10-28"}
            ],
            "lecciones": ["leccion1", "leccion2"]
        }
        errores = validar_postmortem(salida, {"severidad": {"nivel": "SEV2"}})
        assert any("correctiva" in e for e in errores), f"No detectó falta de acción correctiva: {errores}"

    def test_falta_accion_preventiva(self):
        """Detecta cuando no hay acciones preventivas."""
        salida = {
            "resumen": {"descripcion": "Incidente", "duracion": "5 min", "severidad": "SEV2", "impacto": "ninguno"},
            "linea_tiempo": [{"hora": "2026-10-20T13:00:00Z", "evento": "inicio"}],
            "causa_raiz": {"tecnica": "error", "proceso": "falta proceso"},
            "deteccion": {"como": "manual", "tiempo_deteccion": "5 min"},
            "respuesta": {"que_funciono": ["logs"], "que_no_funciono": []},
            "acciones": [
                {"descripcion": "Reiniciar servicio", "tipo": "correctiva", "responsable": "ops", "fecha_estimada": "2026-10-20"}
            ],
            "lecciones": ["leccion1", "leccion2"]
        }
        errores = validar_postmortem(salida, {"severidad": {"nivel": "SEV2"}})
        assert any("preventiva" in e for e in errores), f"No detectó falta de acción preventiva: {errores}"

    def test_accion_generica(self):
        """Detecta acciones genéricas."""
        salida = {
            "resumen": {"descripcion": "Incidente", "duracion": "5 min", "severidad": "SEV2", "impacto": "ninguno"},
            "linea_tiempo": [{"hora": "2026-10-20T13:00:00Z", "evento": "inicio"}],
            "causa_raiz": {"tecnica": "error", "proceso": "falta proceso"},
            "deteccion": {"como": "manual", "tiempo_deteccion": "5 min"},
            "respuesta": {"que_funciono": ["logs"], "que_no_funciono": []},
            "acciones": [
                {"descripcion": "reiniciar", "tipo": "correctiva", "responsable": "ops", "fecha_estimada": "2026-10-20"},
                {"descripcion": "monitorear mejor", "tipo": "preventiva", "responsable": "SRE", "fecha_estimada": "2026-10-28"}
            ],
            "lecciones": ["leccion1", "leccion2"]
        }
        errores = validar_postmortem(salida, {"severidad": {"nivel": "SEV2"}})
        assert any("genérica" in e for e in errores), f"No detectó acción genérica: {errores}"


class TestValidacionSeveridad:
    """Pruebas para validar concordancia de severidad."""

    def test_severidad_no_coincide(self):
        """Detecta cuando la severidad del resumen no coincide con la clasificada."""
        salida = {
            "resumen": {"descripcion": "Incidente", "duracion": "5 min", "severidad": "SEV1", "impacto": "ninguno"},
            "linea_tiempo": [{"hora": "2026-10-20T13:00:00Z", "evento": "inicio"}],
            "causa_raiz": {"tecnica": "error", "proceso": "falta proceso"},
            "deteccion": {"como": "manual", "tiempo_deteccion": "5 min"},
            "respuesta": {"que_funciono": ["logs"], "que_no_funciono": []},
            "acciones": [
                {"descripcion": "Reiniciar servicio ahora", "tipo": "correctiva", "responsable": "ops", "fecha_estimada": "2026-10-20"},
                {"descripcion": "Agregar monitoreo proactivo", "tipo": "preventiva", "responsable": "SRE", "fecha_estimada": "2026-10-28"}
            ],
            "lecciones": ["leccion1", "leccion2"]
        }
        errores = validar_postmortem(salida, {"severidad": {"nivel": "SEV2"}})
        assert any("SEV1" in e and "SEV2" in e and "no coincide" in e for e in errores), f"No detectó discordancia de severidad: {errores}"

    def test_severidad_coincide(self):
        """No genera error cuando la severidad coincide."""
        salida = {
            "resumen": {"descripcion": "Incidente", "duracion": "5 min", "severidad": "SEV2", "impacto": "ninguno"},
            "linea_tiempo": [{"hora": "2026-10-20T13:00:00Z", "evento": "inicio"}],
            "causa_raiz": {"tecnica": "error", "proceso": "falta proceso"},
            "deteccion": {"como": "manual", "tiempo_deteccion": "5 min"},
            "respuesta": {"que_funciono": ["logs"], "que_no_funciono": []},
            "acciones": [
                {"descripcion": "Reiniciar servicio ahora", "tipo": "correctiva", "responsable": "ops", "fecha_estimada": "2026-10-20"},
                {"descripcion": "Agregar monitoreo proactivo", "tipo": "preventiva", "responsable": "SRE", "fecha_estimada": "2026-10-28"}
            ],
            "lecciones": ["leccion1", "leccion2"]
        }
        errores = validar_postmortem(salida, {"severidad": {"nivel": "SEV2"}})
        errores_sev = [e for e in errores if "severidad" in e and "no coincide" in e]
        assert not errores_sev, f"Falso positivo en severidad: {errores_sev}"


@pytest.mark.parametrize("version", [1, 2])
def test_prompt_postmortem_renderiza_contexto_y_carga_esquema(version):
    prompt = prompts.cargar("tri_postmortem", version)
    contexto = "[doc:rb-03#0] No aumentar el pool sin aprobación del DBA."
    valores = {
        "entrada": "Log sintético para comprobar el render del prompt.",
        "senales": "{}",
        "severidad": "{}",
        "acciones": "{}",
        "contexto": contexto,
    }

    sistema, usuario = prompt.render(
        **{nombre: valores[nombre] for nombre in prompt.variables}
    )

    assert prompt.salida_json is True
    assert isinstance(prompt.esquema, dict)
    if version == 2:
        assert contexto in sistema + usuario
        texto_prompt = sistema + usuario
        assert "rb-03" in texto_prompt and "rb-08" in texto_prompt
        assert "datos no confiables" in texto_prompt
    else:
        assert "contexto" not in prompt.variables


def _postmortem_con_acciones(acciones):
    return {
        "resumen": {"descripcion": "Incidente de pool", "severidad": "SEV2", "impacto": "Time-outs en pagos-api"},
        "causa_raiz": {"tecnica": "El pool llegó al límite configurado", "proceso": "El proceso requiere revisión"},
        "deteccion": {"como": "Alerta de errores 5xx"},
        "lecciones": ["Validar capacidad antes de despliegues mayores"],
        "acciones": acciones,
    }


def test_rechaza_aumento_pool_sin_aprobacion_dba_rb03():
    salida = _postmortem_con_acciones([
        {"descripcion": "Aumentar el pool de pagos-api a 50 conexiones", "tipo": "correctiva"},
        {"descripcion": "Agregar una revisión semanal del uso del pool", "tipo": "preventiva"},
    ])

    errores = validar_postmortem(salida, {"severidad": {"nivel": "SEV2"}})

    assert any("rb-03" in error and "DBA" in error for error in errores)


def test_acepta_aumento_pool_condicionado_a_aprobacion_dba_rb03():
    salida = _postmortem_con_acciones([
        {"descripcion": "Solicitar aprobación del DBA antes de aumentar el pool de pagos-api", "tipo": "correctiva"},
        {"descripcion": "Agregar una revisión semanal del uso del pool", "tipo": "preventiva"},
    ])

    errores = validar_postmortem(salida, {"severidad": {"nivel": "SEV2"}})

    assert not any("rb-03" in error for error in errores)


def test_rechaza_reversa_sin_evidencia_temporal_rb08():
    salida = _postmortem_con_acciones([
        {"descripcion": "Revertir el despliegue; verificar script de migración y escalar al DBA si falta", "tipo": "correctiva"},
        {"descripcion": "Agregar una revisión posterior a despliegues", "tipo": "preventiva"},
    ])
    previas = {
        "severidad": {"nivel": "SEV2"},
        "senales": {"eventos": [
            {"hora": "2026-10-20T13:02:11Z", "descripcion": "Despliegue de pagos-api"},
            {"hora": "2026-10-20T14:10:00Z", "descripcion": "Errores 5xx observados"},
        ]},
    }

    errores = validar_postmortem(salida, previas)

    assert any("rb-08" in error for error in errores)


def test_acepta_reversa_con_evidencia_y_control_de_migracion_rb08():
    salida = _postmortem_con_acciones([
        {"descripcion": "Revertir según rb-08: los errores 5xx empeoraron 20 min tras el despliegue; verificar script de reversa de migración y escalar al DBA si falta", "tipo": "correctiva"},
        {"descripcion": "Agregar una revisión posterior a despliegues", "tipo": "preventiva"},
    ])
    previas = {
        "severidad": {"nivel": "SEV2"},
        "senales": {"eventos": [
            {"hora": "2026-10-20T13:00:00Z", "descripcion": "errores_5xx=2% observados antes del despliegue"},
            {"hora": "2026-10-20T13:02:11Z", "descripcion": "Despliegue de pagos-api"},
            {"hora": "2026-10-20T13:22:00Z", "descripcion": "errores_5xx=27% observados tras el despliegue"},
        ]},
    }

    errores = validar_postmortem(salida, previas)

    assert not any("rb-08" in error for error in errores)


def test_acepta_prohibicion_explicita_de_aumentar_pool_rb03():
    salida = _postmortem_con_acciones([
        {"descripcion": "No aumentar el pool sin aprobaci\u00f3n expl\u00edcita del DBA", "tipo": "correctiva"},
        {"descripcion": "Agregar una metrica preventiva semanal del pool", "tipo": "preventiva"},
    ])

    errores = validar_postmortem(salida, {"severidad": {"nivel": "SEV2"}})

    assert not any("rb-03" in error for error in errores)


def test_no_confunde_aumento_de_trafico_con_aumento_del_pool_rb03():
    salida = _postmortem_con_acciones([
        {"descripcion": "Definir un punto de control verificable para canary", "tipo": "correctiva"},
        {"descripcion": "Comparar uso de pool y tasa de errores 5xx antes de incrementar el porcentaje de trafico", "tipo": "preventiva"},
    ])

    errores = validar_postmortem(salida, {"severidad": {"nivel": "SEV2"}})

    assert not any("rb-03" in error for error in errores)


def test_rechaza_reversa_si_mediciones_solo_comparan_antes_y_despues_de_reversa_rb08():
    salida = _postmortem_con_acciones([
        {"descripcion": "Revertir el despliegue y medir errores 5xx en ventanas comparables antes y despues de la reversa; verificar script de reversa de migracion y escalar al DBA si falta", "tipo": "correctiva"},
        {"descripcion": "Agregar una revision posterior a despliegues", "tipo": "preventiva"},
    ])
    previas = {"severidad": {"nivel": "SEV2"}, "senales": {"eventos": [
        {"hora": "2026-10-20T13:02:11Z", "descripcion": "Despliegue de pagos-api"},
        {"hora": "2026-10-20T13:22:00Z", "descripcion": "Alerta de errores_5xx=27% (umbral 5%)"},
    ]}}

    errores = validar_postmortem(salida, previas)

    assert any("rb-08" in error for error in errores)


def test_intento_1_reunir_mediciones_y_verificar_requisitos_pasa_rb08():
    salida = _postmortem_con_acciones([
        {"descripcion": "Propuesta: reunir la comparaci\u00f3n pre y post despliegue de errores 5xx y de latencia p95 de POST /v1/transferencias (ventana de 60 min antes y despu\u00e9s de 13:02:11Z) para evaluar si hay empeoramiento demostrable y decidir sobre la reversa conforme a rb-08.", "tipo": "correctiva"},
        {"descripcion": "Propuesta: confirmar con el DBA si la versi\u00f3n 4.19 incluy\u00f3 migraciones y si existe script de reversa; identificar en el monitor de BD las consultas de mas de 5 s de pagos-api. Cancelar solo consultas confirmadas como de reportes. No aumentar el pool sin aprobaci\u00f3n expl\u00edcita del DBA.", "tipo": "correctiva"},
        {"descripcion": "Propuesta: crear una alerta para uso del pool de conexiones de pagos-api mayor a 90 %, con destinatario de respuesta definido y registro de acuse, activa tambien durante las ventanas de despliegue.", "tipo": "preventiva"},
    ])
    previas = {"severidad": {"nivel": "SEV2"}, "senales": {"eventos": [
        {"hora": "2026-10-20T13:02:11Z", "descripcion": "Despliegue de pagos-api"},
        {"hora": "2026-10-20T13:22:00Z", "descripcion": "Alerta de errores_5xx=27% (umbral 5%)"},
    ]}}

    assert validar_postmortem(salida, previas) == []


def test_intento_2_rechaza_ejecucion_condicional_de_reversa_rb08():
    salida = _postmortem_con_acciones([
        {"descripcion": "Propuesta: reunir mediciones comparables de errores 5xx y latencia p95 de POST /v1/transferencias en la ventana de 60 minutos previa al despliegue (12:02Z\u201313:02Z) y en la ventana de 60 minutos posterior (13:02Z\u201314:02Z), con la misma granularidad. Esta comparaci\u00f3n es requisito para decidir si rb-08 aplica. Mientras no exista, no se recomienda la reversa de pagos-api.", "tipo": "correctiva"},
        {"descripcion": "Propuesta: antes de cualquier reversa de pagos-api por rb-08, confirmar con el DBA si la versi\u00f3n 4.19 incluy\u00f3 migraciones de base de datos. Si existen y no tienen script de reversa, escalar al DBA antes de revertir. Si no hay migraciones o tienen script de reversa, y la comparaci\u00f3n de la acci\u00f3n anterior confirma empeoramiento, ejecutar la reversa con estrategia inmediata y verificar la ca\u00edda de errores 5xx en 10 minutos.", "tipo": "correctiva"},
        {"descripcion": "Propuesta: identificar con el DBA las consultas de mas de 5 s asociadas a pagos-api en el monitor de base de datos. Cancelar unicamente las que se confirme que son de reportes. No aumentar el tamano del pool sin aprobacion explicita del DBA, que debe obtenerse antes de cualquier cambio.", "tipo": "correctiva"},
        {"descripcion": "Propuesta preventiva: definir una alerta para el uso del pool de conexiones de pagos-api por encima de un umbral acordado, con notificacion al equipo responsable, dado que la advertencia de 92 % quedo solo en log.", "tipo": "preventiva"},
    ])
    previas = {"severidad": {"nivel": "SEV2"}, "senales": {"eventos": [
        {"hora": "2026-10-20T13:02:11Z", "descripcion": "Despliegue de pagos-api"},
        {"hora": "2026-10-20T13:22:00Z", "descripcion": "Alerta de errores_5xx=27% (umbral 5%)"},
    ]}}
    error_rb08 = ("Acci\u00f3n incompatible con rb-08: requiere mediciones comparables antes "
                  "y despu\u00e9s del despliegue (m\u00e1ximo 60 minutos), verificaci\u00f3n del script "
                  "de reversa y escalamiento al DBA si falta")

    errores = validar_postmortem(salida, previas)

    assert errores == [error_rb08]


@pytest.mark.parametrize(
    "descripcion",
    [
        "Propuesta: obtener las métricas previas y posteriores al despliegue de 4.19 (errores 5xx de transferencias, latencia p95 y uso del pool) en la ventana de 60 minutos anterior y posterior a 13:02:11Z, y, con el DBA, verificar si la versión 4.19 incluye migraciones de base de datos y si tienen script de reversa. Hasta contar con esa comparación, no se propone ejecutar una reversa (rb-08).",
        "Propuesta: obtener mediciones comparables de transferencias.errores_5xx y de latencia p95 de transferencias en una ventana de 60 minutos antes de 2026-10-20T13:02:11Z y en los 60 minutos posteriores, con la misma granularidad. Esta acción solo recopila evidencia y no implica ejecutar ninguna reversa.",
        "Propuesta: verificar con el DBA si la versión 4.19 incluye migraciones de base de datos y, en ese caso, si existe script de reversa validado. Si no existe o no se puede confirmar, escalar al DBA antes de cualquier decisión sobre la versión 4.19. Esta acción no implica ejecutar reversa.",
    ],
)
def test_rb08_no_marca_como_ejecucion_la_negacion_de_reversa_guardada(descripcion):
    salida = _postmortem_con_acciones([
        {"descripcion": descripcion, "tipo": "correctiva"},
        {"descripcion": "Documentar las mediciones disponibles y los faltantes", "tipo": "preventiva"},
    ])

    errores = validar_postmortem(salida, {"severidad": {"nivel": "SEV2"}})

    assert not any("rb-08" in error for error in errores)


def test_rechaza_reversa_si_solo_hay_alerta_posterior_rb08():
    salida = _postmortem_con_acciones([
        {"descripcion": "Revertir el despliegue; verificar script de reversa de migración y escalar al DBA si falta", "tipo": "correctiva"},
        {"descripcion": "Agregar una revisión posterior a despliegues", "tipo": "preventiva"},
    ])
    previas = {"severidad": {"nivel": "SEV2"}, "senales": {"eventos": [
        {"hora": "2026-10-20T13:02:11Z", "descripcion": "Despliegue de pagos-api"},
        {"hora": "2026-10-20T13:22:00Z", "descripcion": "Alerta de errores_5xx=27% (umbral 5%)"},
    ]}}
    assert any("rb-08" in error for error in validar_postmortem(salida, previas))
