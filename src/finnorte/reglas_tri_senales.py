def validar_senales(datos: dict, previas: dict) -> list[str]:
    errores = []
    eventos = datos.get("eventos", [])

    if not eventos:
        errores.append("La lista de eventos no puede estar vacía.")

    for evento in eventos:
        hora = evento.get("hora", "")
        if len(hora) < 4 or ":" not in hora:
            errores.append(f"Formato de hora inválido detectado: {hora}")

    return errores