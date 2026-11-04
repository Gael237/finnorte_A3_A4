"""Validación en código para la etapa tri_postmortem (A2 · Axel).

Reglas de negocio que el esquema JSON no puede verificar:
1. La severidad del resumen coincide con la severidad clasificada
2. No hay datos personales en el postmortem (nombres, correos, teléfonos, CLABEs)
3. Las secciones obligatorias de pm-03 están presentes y no vacías
4. Las acciones incluyen al menos una correctiva y una preventiva
"""
import re
from typing import Any


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
    
    return errores
