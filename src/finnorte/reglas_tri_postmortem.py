"""Validación en código para la etapa tri_postmortem (A2 · Axel).

Reglas de negocio que el esquema JSON no puede verificar:
1. La severidad del resumen coincide con la severidad clasificada
2. No hay datos personales en el postmortem (nombres, correos, teléfonos, CLABEs)
3. Las secciones obligatorias de pm-03 están presentes y no vacías
4. Las acciones incluyen al menos una correctiva y una preventiva
"""
import re
from datetime import datetime, timezone
from typing import Any


def _reversa_cumple_rb08(previas: dict, descripcion: str) -> bool:
    """Exige medidas comparables antes y después del despliegue y control de migración."""
    eventos = previas.get("senales", {}).get("eventos", [])
    despliegues = []
    mediciones = []
    for evento in eventos:
        if not isinstance(evento, dict):
            continue
        hora = evento.get("hora")
        texto = str(evento.get("descripcion", "")).lower()
        try:
            instante = datetime.fromisoformat(str(hora).replace("Z", "+00:00"))
            if instante.tzinfo is None:
                instante = instante.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            continue
        if re.search(r"\b(deploy|despliegue)\b", texto):
            despliegues.append(instante)
        # El umbral de alerta no es una medición previa del servicio.
        if "umbral" in texto:
            continue
        errores = re.search(r"(?:errores[_\s]*5xx|5xx)\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*%", texto)
        latencia = re.search(r"(?:latencia[_\s]*p95|p95)\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*(ms|s)\b", texto)
        if errores:
            mediciones.append((instante, "5xx", float(errores.group(1).replace(",", "."))))
        if latencia:
            valor = float(latencia.group(1).replace(",", "."))
            mediciones.append((instante, "p95", valor * (1000 if latencia.group(2) == "s" else 1)))

    empeoro = any(
        antes_t < despliegue <= despues_t
        and 0 <= (despues_t - despliegue).total_seconds() <= 60 * 60
        and antes_tipo == despues_tipo and despues_valor > antes_valor
        for despliegue in despliegues
        for antes_t, antes_tipo, antes_valor in mediciones
        for despues_t, despues_tipo, despues_valor in mediciones
    )
    desc = descripcion.lower()
    verifica_script = "script" in desc and bool(re.search(r"verific|comprob", desc))
    escalamiento_si_falta = (
        "si falta" in desc and "dba" in desc
        and bool(re.search(r"escal", desc))
    )
    script_confirmado = bool(re.search(r"script.{0,35}(?:confirmado|disponible|existente)", desc))
    return empeoro and verifica_script and (escalamiento_si_falta or script_confirmado)


def validar_postmortem(salida: dict, previas: dict) -> list[str]:
    """Valida el borrador de postmortem contra reglas de negocio.
    
    Args:
        salida: La salida de la etapa tri_postmortem
        previas: Salidas de etapas anteriores (debe incluir 'severidad')
    
    Returns:
        Lista de errores encontrados (vacía si todo está correcto)
    """
    errores = []
    
    # Regla 1: Severidad debe coincidir con la clasificada
    severidad_clasificada = previas.get("severidad", {}).get("nivel")
    severidad_resumen = salida.get("resumen", {}).get("severidad")
    
    if severidad_clasificada and severidad_resumen != severidad_clasificada:
        errores.append(
            f"La severidad del resumen ({severidad_resumen}) no coincide "
            f"con la severidad clasificada ({severidad_clasificada})"
        )
    
    # Regla 2: Detectar datos personales (patrón simple)
    texto_completo = str(salida)
    
    # Patrones de PII
    patrones_pii = [
        (r'\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b', 'correo electrónico', re.IGNORECASE),
        (r'\b\d{18}\b', 'CLABE', 0),
        (r'\b\d{3}[-\s]?\d{3}[-\s]?\d{4}\b', 'teléfono', 0),
        (r'\b(señor|señora|sr\.?|sra\.?|don|doña)\s+[A-Z][a-z]+', 'tratamiento personal', re.IGNORECASE),
    ]
    
    for patron, tipo, flags in patrones_pii:
        if re.search(patron, texto_completo, flags):
            errores.append(
                f"Posible dato personal detectado ({tipo}). "
                "Los postmortems no deben incluir información de clientes"
            )
    
    # Regla 3: Verificar que las secciones obligatorias no estén vacías
    secciones_requeridas = {
        'resumen': ['descripcion', 'impacto'],
        'causa_raiz': ['tecnica', 'proceso'],
        'deteccion': ['como'],
        'lecciones': None  # Es un array
    }
    
    for seccion, campos in secciones_requeridas.items():
        if seccion not in salida:
            errores.append(f"Falta la sección obligatoria '{seccion}' (pm-03)")
            continue
            
        if campos is None:  # Array
            if not salida[seccion]:
                errores.append(f"La sección '{seccion}' está vacía")
        else:  # Objeto con campos
            for campo in campos:
                valor = salida[seccion].get(campo, "")
                if not valor or valor == "":
                    errores.append(f"El campo '{seccion}.{campo}' está vacío")
    
    # Regla 4: Verificar balance de acciones correctivas y preventivas
    acciones = salida.get("acciones", [])
    
    if acciones:
        tipos = [a.get("tipo") for a in acciones]
        tiene_correctiva = "correctiva" in tipos
        tiene_preventiva = "preventiva" in tipos
        
        if not tiene_correctiva:
            errores.append(
                "El postmortem debe incluir al menos una acción correctiva "
                "(solución inmediata del problema)"
            )
        
        if not tiene_preventiva:
            errores.append(
                "El postmortem debe incluir al menos una acción preventiva "
                "(evitar que vuelva a ocurrir)"
            )
    
    # Regla 5: Verificar que las acciones no sean genéricas
    acciones_genericas = [
        "reiniciar",
        "reiniciar todo",
        "revisar",
        "investigar más",
        "monitorear",
    ]
    
    for accion in acciones:
        desc = accion.get("descripcion", "").lower()
        for generica in acciones_genericas:
            if generica in desc and len(desc) < 30:
                errores.append(
                    f"Acción demasiado genérica: '{accion.get('descripcion')}'. "
                    "Las acciones deben ser específicas y accionables"
                )
                break

        propone_aumentar_pool = re.search(
            r"\b(?:aumentar|incrementar|ampliar|expandir|subir|elevar|aumento|incremento)\b"
            r".{0,60}\bpool\b|\bpool\b.{0,60}\b"
            r"(?:aumentar|incrementar|ampliar|expandir|subir|elevar|aumento|incremento)\b",
            desc,
        )
        autorizacion_dba = re.search(
            r"\b(?:aprobaci[oó]n|autorizaci[oó]n)\b.{0,35}\bdba\b",
            desc,
        )
        niega_autorizacion = re.search(
            r"\b(?:sin|no\s+(?:requiere|necesita|hay))\s+(?:la\s+)?"
            r"(?:aprobaci[oó]n|autorizaci[oó]n)\b",
            desc,
        )
        prohibe_aumento = re.search(
            r"\b(?:no|nunca|bloquear|prohibir)\b.{0,50}\b"
            r"(?:aumentar|incrementar|ampliar|expandir|subir|elevar)\b.{0,35}\bpool\b",
            desc,
        )
        if propone_aumentar_pool and (
            not autorizacion_dba or (niega_autorizacion and not prohibe_aumento)
        ):
            errores.append(
                "Acción incompatible con rb-03: cualquier aumento del pool requiere "
                "aprobación del DBA y no puede proponerse sin ella"
            )

        propone_reversa = re.search(r"\b(revertir|reversa|rollback)\b", desc)
        if propone_reversa and not _reversa_cumple_rb08(previas, desc):
            errores.append(
                "Acción incompatible con rb-08: requiere mediciones comparables antes "
                "y después del despliegue (máximo 60 minutos), verificación del script "
                "de reversa y escalamiento al DBA si falta"
            )
    
    return errores
