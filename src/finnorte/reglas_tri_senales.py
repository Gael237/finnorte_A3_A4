def validar_senales(resultado_json):
    eventos = resultado_json.get("eventos", [])
    if not eventos:
        raise ValueError("La lista de eventos no puede estar vacía. El log debe contener señales.")
    
    for evento in eventos:
        hora = evento.get("hora", "")
        if len(hora) < 4 or ":" not in hora: 
            raise ValueError(f"Formato de hora inválido detectado: {hora}")
    
    return True