"""Pruebas dirigidas para validar las reglas de tri_postmortem (A2 · Axel)."""
import pytest
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
                    "descripcion": "Incrementar límite del pool a 50 conexiones",
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