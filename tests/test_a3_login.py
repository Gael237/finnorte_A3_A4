from __future__ import annotations

import os
import time
import pytest
from fastapi.testclient import TestClient

from a3 import login_eficiencia, login_mantenible, login_seguridad
from api.auth import Autenticador, ErrorAuth, emitir_token, validar_token


# ─── 3 PRUEBAS OFICIALES (login exitoso, contraseña incorrecta, usuario inexistente) ───

def test_a3_oficial_login_exitoso():
    sal, dk = login_seguridad.generar_hash("ClaveSegura#2026", b"0123456789abcdef")
    db = {"admin": (sal, dk)}
    res = login_seguridad.login("admin", "ClaveSegura#2026", db, ahora=1000.0)
    assert res["ok"] is True
    assert res["mensaje"] == "access granted"


def test_a3_oficial_contrasena_incorrecta():
    sal, dk = login_seguridad.generar_hash("ClaveSegura#2026", b"0123456789abcdef")
    db = {"admin": (sal, dk)}
    res = login_seguridad.login("admin", "incorrecta", db, ahora=1000.0)
    assert res["ok"] is False
    assert res["codigo"] == 401
    assert res["mensaje"] == "Credenciales inválidas"


def test_a3_oficial_usuario_inexistente_mismo_mensaje():
    sal, dk = login_seguridad.generar_hash("ClaveSegura#2026", b"0123456789abcdef")
    db = {"admin": (sal, dk)}
    res_inexistente = login_seguridad.login("fantasma", "cualquiera", db, ahora=1000.0)
    res_clave_mala = login_seguridad.login("admin", "cualquiera", db, ahora=1000.0)
    assert res_inexistente["ok"] is False
    assert res_inexistente["mensaje"] == res_clave_mala["mensaje"]


# ─── PRUEBAS PROPIAS (token expirado, token alterado, bloqueo y endpoint /v1/triage) ───

def test_a3_propia_token_expirado(monkeypatch):
    monkeypatch.setenv("TOKEN_SECRET", "a" * 64)
    t0 = 1_700_000_000.0
    token = emitir_token("gael@finnorte.mx", ahora=t0)
    with pytest.raises(ErrorAuth) as exc:
        validar_token(token, ahora=t0 + 901)  # 15 min + 1 seg
    assert exc.value.status == 401


def test_a3_propia_token_alterado(monkeypatch):
    monkeypatch.setenv("TOKEN_SECRET", "b" * 64)
    token = emitir_token("gael@finnorte.mx", ahora=time.time())
    alterado = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(ErrorAuth) as exc:
        validar_token(alterado)
    assert exc.value.status == 401


def test_a3_propia_bloqueo_intentos_fallidos(monkeypatch):
    monkeypatch.setenv("TOKEN_SECRET", "c" * 64)
    auth = Autenticador(":memory:")
    auth.registrar("operador@finnorte.mx", "SuperClave123")
    for _ in range(5):
        with pytest.raises(ErrorAuth) as exc:
            auth.login("operador@finnorte.mx", "MalaClave", ahora=2000.0)
        assert exc.value.status == 401
    with pytest.raises(ErrorAuth) as exc_bloqueo:
        auth.login("operador@finnorte.mx", "SuperClave123", ahora=2005.0)
    assert exc_bloqueo.value.status == 429


def test_a3_propia_endpoint_triage_protegido_y_validado(monkeypatch):
    monkeypatch.setenv("TOKEN_SECRET", "d" * 64)
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("EMB_PROVIDER", "hash")
    import api.producto as prod

    client = TestClient(prod.app)
    # Sin token devuelve 401 problem+json
    r_sin = client.post("/v1/triage", json={"log": "ERROR 500 timeout en pagos-api"})
    assert r_sin.status_code == 401

    # Con token válido pero entrada muy corta devuelve 422
    token = emitir_token("gael@finnorte.mx")
    r_422 = client.post(
        "/v1/triage",
        json={"log": "corto"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_422.status_code == 422


def test_a3_versiones_eficiencia_y_mantenible():
    srv = login_eficiencia.ServicioLoginEficiente(iteraciones=10_000)
    srv.registrar("gael@finnorte.mx", "Clave1234", b"sal_de_16_bytes!")
    assert srv.login("gael@finnorte.mx", "Clave1234") == "access granted"
    assert srv.login("gael@finnorte.mx", "otra") == "invalid credentials"

    class RepoMock:
        def obtener_credencial(self, usuario: str):
            if usuario == "gael@finnorte.mx":
                sal = b"sal_de_16_bytes!"
                dk = login_mantenible.hashlib.pbkdf2_hmac("sha256", b"Clave1234", sal, 10_000)
                return sal, dk
            return None

    caso = login_mantenible.CasoUsoLogin(RepoMock(), login_mantenible.VerificadorPBKDF2(iteraciones=10_000))
    assert caso.ejecutar("gael@finnorte.mx", "Clave1234").exitoso is True
    assert caso.ejecutar("no@finnorte.mx", "Clave1234").exitoso is False