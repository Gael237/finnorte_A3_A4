from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegistroUsuario:
    sal: bytes
    hash_clave: bytes
    activo: bool = True


class ServicioLoginEficiente:
    """Almacén en memoria con acceso O(1) por índice hash y validación temprana de límites."""

    def __init__(self, iteraciones: int = 120_000) -> None:
        self._usuarios: dict[str, RegistroUsuario] = {}
        self._iteraciones = iteraciones

    def registrar(self, user: str, password: str, sal: bytes) -> None:
        clave = user.strip().lower()
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), sal, self._iteraciones)
        self._usuarios[clave] = RegistroUsuario(sal=sal, hash_clave=dk, activo=True)

    def login(self, user: str, password: str) -> str:
        # Validación rápida O(1) antes de ejecutar derivación criptográfica
        if not user or not password or len(user) > 120 or len(password) > 128:
            return "invalid credentials"

        registro = self._usuarios.get(user.strip().lower())
        if registro is None or not registro.activo:
            return "invalid credentials"

        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), registro.sal, self._iteraciones)
        if hmac.compare_digest(dk, registro.hash_clave):
            return "access granted"
        return "invalid credentials"