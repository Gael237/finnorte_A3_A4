import json
from finnorte.pipeline import Pipeline, Etapa

# 1. Configurar la etapa (usando la versión 2 explícitamente)
etapa_senales = Etapa(
    nombre="senales",
    prompt="tri_senales",
    version=2,
    usa=[],
    reintentos=3
)

# 2. Crear el motor
flujo = Pipeline([etapa_senales], nombre="prueba_senales_v2")

# 3. Caso de prueba con log simulado y contexto de un manual
caso = {
    "entrada": "2026-11-04 10:05:00 ERROR [pagos-api] Timeout connection to SPEI. Múltiples transferencias fallidas reportadas por usuarios.",
    "contexto": "Documento [doc:rb-05]: Si ocurren timeouts masivos hacia el componente SPEI o transferencias fallidas, se considera falla_componente_critico (true) y las transferencias caídas afectan a todos."
}

print("Ejecutando prueba de tri_senales v2...")
res = flujo.ejecutar(caso, detener_en_error=False)

print(f"\n¿Pasó la validación del esquema?: {res.ok}")
print("\nSalida generada (JSON devuelto por el modelo):")
print(json.dumps(res.salidas.get("senales"), indent=2, ensure_ascii=False))