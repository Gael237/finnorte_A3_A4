"""Interfaz del producto que consume el SERVICIO (no funciones locales).   streamlit run app/cliente_api.py

Antes: en otra terminal, uvicorn api.producto:app --reload
La URL del servicio se lee de API_URL: primero de la variable de entorno, luego del .env (por defecto http://127.0.0.1:8000).
A4: adapta esta interfaz a tu variante (modo «Mi variante», tu herramienta y tu validador visibles).

Diseño (T9): estados de espera y error visibles, fuentes desplegables, costo y latencia a la vista.
Agente (T10): lo sensible NO se ejecuta hasta que tú lo autorizas con los datos exactos a la vista.
"""
from __future__ import annotations

import os
from pathlib import Path

import requests
import streamlit as st


def _cargar_env(archivo: Path = Path(__file__).resolve().parents[1] / ".env") -> None:
    """Lee el .env de la raíz del repositorio (sin sobrescribir variables ya definidas)."""
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                clave, valor = linea.split("=", 1)
                os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


_cargar_env()
API = os.getenv("API_URL", "http://127.0.0.1:8000")
st.set_page_config(page_title="FinNorte · Producto", page_icon="🏦", layout="wide")


def llamar(metodo: str, ruta: str, **kw) -> tuple[int, dict]:
    """Llama al servicio con el token de la sesión; nunca truena la interfaz por un error de red."""
    h = {"Authorization": f"Bearer {st.session_state['token']}"} if st.session_state.get("token") else {}
    try:
        r = requests.request(metodo, f"{API}{ruta}", headers=h, timeout=90, **kw)
        return r.status_code, (r.json() if r.content else {})
    except requests.RequestException as e:
        return 0, {"title": "Servicio no disponible", "detail": f"¿Está corriendo uvicorn en {API}? ({type(e).__name__})"}


def mostrar_error(status: int, cuerpo: dict):
    if status == 401:
        st.session_state.pop("token", None)
        st.warning("Tu sesión expiró o no es válida. Vuelve a iniciar sesión.")
    elif status == 429:
        st.warning(f"{cuerpo.get('detail', 'Demasiadas solicitudes')}. Espera un minuto.")
    elif status == 503:
        st.error("El modelo (Gemini) no respondió a tiempo. Intenta de nuevo en unos segundos.")
    else:
        st.error(f"{cuerpo.get('title', 'Error')}: {cuerpo.get('detail', '')}")
    if cuerpo.get("trace_id"):
        st.caption(f"trace_id: {cuerpo['trace_id']}")


# ───────────────────────────── barra lateral: sesión ─────────────────────────────
s, salud = llamar("GET", "/salud")
st.sidebar.markdown(f"**Servicio:** {API}  \n" + (f"**Modelo:** {salud.get('llm')}  \n**Variante:** {salud.get('variante')}"
                                                  if s == 200 else "🔴 sin conexión"))
if not st.session_state.get("token"):
    st.sidebar.subheader("Iniciar sesión")
    email = st.sidebar.text_input("Correo")
    contrasena = st.sidebar.text_input("Contraseña", type="password")
    c1, c2 = st.sidebar.columns(2)
    if c1.button("Entrar", use_container_width=True):
        st_, cuerpo = llamar("POST", "/auth/login", json={"email": email, "contrasena": contrasena})
        if st_ == 200:
            st.session_state["token"] = cuerpo["token"]
            st.rerun()
        else:
            mostrar_error(st_, cuerpo)
    if c2.button("Registrarme", use_container_width=True):
        st_, cuerpo = llamar("POST", "/auth/registro", json={"email": email, "contrasena": contrasena})
        if st_ == 201:
            st.sidebar.success("Cuenta creada; ahora entra.")
        else:
            mostrar_error(st_, cuerpo)
    st.title("🏦 FinNorte · Producto")
    st.info("Inicia sesión para usar el asistente. Tu token dura 15 minutos.")
    st.stop()

if st.sidebar.button("Cerrar sesión"):
    st.session_state.clear()
    st.rerun()
modo = st.sidebar.radio("Modo", ["Preguntar (caso guía)", "Mi variante", "Agente"])
st.sidebar.caption("Ficticio · uso educativo · LSCA2318")

# ───────────────────────────── modos ─────────────────────────────
if modo.startswith("Preguntar"):
    st.title("📘 Manual de Ingeniería")
    st.caption("Respondo solo con el manual y cito la fuente. Si no está en el manual, te lo digo.")
    pregunta = st.text_input("Tu pregunta", placeholder="¿Cada cuánto se rotan los secretos de producción?", max_chars=500)
    if st.button("Preguntar", type="primary", disabled=len(pregunta.strip()) < 3):
        with st.spinner("Buscando en el manual y consultando a Gemini…"):
            st_, out = llamar("POST", "/v1/preguntas", json={"pregunta": pregunta})
        if st_ != 200:
            mostrar_error(st_, out)
        else:
            (st.warning if out["abstuvo"] else st.success)(out["respuesta"])
            if out["fuentes"]:
                with st.expander(f"Fuentes ({len(out['fuentes'])})"):
                    st.write(out["fuentes"])
            st.caption(f"⏱ {out['latencia_ms']:.0f} ms · 💲 US${out['costo_usd']:.5f}")

elif modo == "Mi variante":
    st.title(f"🚨 Triage de Incidentes · {salud.get('variante', 'v5-triage')}")
    servicio = st.text_input("Microservicio afectado (opcional)", placeholder="pagos-api")
    texto = st.text_area("Traza de logs o descripción del incidente", height=200,
                         placeholder="2026-11-24T10:05:12 [ERROR] pagos-api: Timeout 504 contra gateway-spei...")
    if st.button("Ejecutar triage", type="primary", disabled=len(texto.strip()) < 10):
        with st.spinner("Recuperando runbooks, ejecutando pipeline de 4 etapas y validando PII/citas…"):
            payload = {"log": texto}
            if servicio.strip():
                payload["servicio"] = servicio.strip()
            st_, out = llamar("POST", "/v1/triage", json=payload)
        if st_ != 200:
            mostrar_error(st_, out)
        else:
            (st.warning if out.get("abstuvo") else st.success)(out.get("respuesta", ""))
            if out.get("fuentes"):
                with st.expander(f"Runbooks y postmortems citados ({len(out['fuentes'])})"):
                    st.write(out["fuentes"])
            if out.get("artefacto"):
                with st.expander("Artefacto estructurado de Triage (JSON)"):
                    st.json(out["artefacto"])
            if out.get("errores_citas"):
                st.error(f"Citas con problema: {out['errores_citas']}")
            st.caption(f"⏱ {out.get('latencia_ms', 0):.0f} ms · 💲 US${out.get('costo_usd', 0):.5f}")

else:
    st.title("🤖 Agente de Triage v5 con Confirmación Humana")
    st.caption("Consulta logs (máx. 2h, PII enmascarada) y runbooks. Crear tickets de incidente requiere TU autorización.")
    tarea = st.text_area(
        "Tarea de investigación / triage",
        "Revisa los logs de pagos-api entre 2026-11-24T10:00:00 y 2026-11-24T11:30:00 con patrón ERROR, "
        "consulta los runbooks de severidad y si amerita abre un ticket de incidente.",
    )
    if st.button("Ejecutar agente", type="primary"):
        with st.spinner("El agente está consultando herramientas y validando reglas de triage…"):
            st_, out = llamar("POST", "/v1/agente", json={"tarea": tarea})
        if st_ != 200:
            mostrar_error(st_, out)
        else:
            st.session_state["agente"] = out
            st.session_state.pop("ultimo", None)
    out = st.session_state.get("agente")
    if out:
        (st.success if out["terminado"] else st.error)(out["respuesta"])
        if out.get("fuentes"):
            with st.expander(f"Fuentes citadas ({len(out['fuentes'])})"):
                st.write(out["fuentes"])
        v = out["validador"]
        (st.success if v["ok"] else st.error)(
            "Validador v5-triage: OK" if v["ok"] else "Validador v5-triage bloqueó la acción: " + " · ".join(v["hallazgos"])
        )
        for p in out["pasos"]:
            with st.expander(f"Paso {p['n']} · {p['accion']} {p['herramienta'] or ''} · {p['estado']}"):
                st.json(p)
        for p in out["pendientes"]:
            st.warning(f"**Acción sensible pendiente:** `{p['herramienta']}`")
            st.json(p["argumentos"])
            c1, c2 = st.columns(2)
            for col, aprobar, etiqueta in ((c1, True, "✅ Autorizar ticket"), (c2, False, "⛔ Rechazar ticket")):
                if col.button(etiqueta, key=f"{p['id']}-{aprobar}", use_container_width=True):
                    st_, r = llamar("POST", f"/v1/agente/confirmar/{p['id']}", json={"aprobar": aprobar})
                    if st_ != 200:
                        mostrar_error(st_, r)
                    else:
                        st.session_state["agente"]["pendientes"] = []
                        st.session_state["ultimo"] = r
                        st.rerun()
        if st.session_state.get("ultimo"):
            r = st.session_state["ultimo"]
            (st.success if r["estado"] == "ejecutada" else st.info)(f"Acción {r['estado']}: {r.get('resultado', r.get('argumentos'))}")