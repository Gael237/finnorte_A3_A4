from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ResultadoLogin:
    exitoso: bool
    mensaje: str
    usuario: str | None = None


class RepositorioUsuarios(Protocol):
    def obtener_credencial(self, usuario: str) -> tuple[bytes, bytes] | None: ...


class VerificadorCredenciales(Protocol):
    def verificar(self, password: str, sal: bytes, hash_esperado: bytes) -> bool: ...


class VerificadorPBKDF2:
    def __init__(self, iteraciones: int = 200_000) -> None:
        self.iteraciones = iteraciones

    def verificar(self, password: str, sal: bytes, hash_esperado: bytes) -> bool:
        calculado = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), sal, self.iteraciones)
        return hmac.compare_digest(calculado, hash_esperado)


class CasoUsoLogin:
    """Caso de uso desacoplado, fácilmente extensible y con contratos explícitos."""

    MENSAJE_EXITO = "access granted"
    MENSAJE_FALLO = "invalid credentials"

    def __init__(self, repositorio: RepositorioUsuarios, verificador: VerificadorCredenciales) -> None:
        self._repositorio = repositorio
        self._verificador = verificador

    def ejecutar(self, user: str, password: str) -> ResultadoLogin:
        usuario_limpio = (user or "").strip().lower()
        if not usuario_limpio or not password:
            return ResultadoLogin(exitoso=False, mensaje=self.MENSAJE_FALLO)

        credencial = self._repositorio.obtener_credencial(usuario_limpio)
        if credencial is None:
            return ResultadoLogin(exitoso=False, mensaje=self.MENSAJE_FALLO)

        sal, hash_esperado = credencial
        if not self._verificador.verificar(password, sal, hash_esperado):
            return ResultadoLogin(exitoso=False, mensaje=self.MENSAJE_FALLO)

        return ResultadoLogin(exitoso=True, mensaje=self.MENSAJE_EXITO, usuario=usuario_limpio)