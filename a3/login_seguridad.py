from __future__ import annotations

import hashlib
import hmac
import os
import time

ITERACIONES = 200_000
MAX_INTENTOS = 5
VENTANA_BLOQUEO_S = 900
MENSAJE_ERROR = "Credenciales inválidas"


def generar_hash(password: str, sal: bytes | None = None) -> tuple[bytes, bytes]:
    sal = sal or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), sal, ITERACIONES)
    return sal, dk


def login(
    user: str,
    password: str,
    usuarios_db: dict[str, tuple[bytes, bytes]],
    intentos_fallidos: dict[str, list[float]] | None = None,
    ahora: float | None = None,
) -> dict[str, object]:
    """Autenticación segura con PBKDF2, comparación en tiempo constante, mensaje unificado y bloqueo."""
    if not isinstance(user, str) or not isinstance(password, str):
        return {"ok": False, "mensaje": MENSAJE_ERROR, "codigo": 422}

    usuario_norm = user.strip().lower()
    t = ahora if ahora is not None else time.time()
    registro = intentos_fallidos if intentos_fallidos is not None else {}

    recientes = [ts for ts in registro.get(usuario_norm, []) if t - ts < VENTANA_BLOQUEO_S]
    registro[usuario_norm] = recientes
    if len(recientes) >= MAX_INTENTOS:
        return {"ok": False, "mensaje": "Cuenta bloqueada temporalmente por múltiples intentos", "codigo": 429}

    datos = usuarios_db.get(usuario_norm)
    sal_dummy = b"\x00" * 16
    hash_dummy = b"\x00" * 32
    sal, hash_esperado = datos if datos is not None else (sal_dummy, hash_dummy)

    _, hash_calculado = generar_hash(password, sal)
    coincide = hmac.compare_digest(hash_calculado, hash_esperado) and (datos is not None)

    if not coincide:
        registro[usuario_norm].append(t)
        return {"ok": False, "mensaje": MENSAJE_ERROR, "codigo": 401}

    registro[usuario_norm] = []
    return {"ok": True, "mensaje": "access granted", "codigo": 200, "usuario": usuario_norm}