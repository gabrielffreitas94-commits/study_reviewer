"""Serviço de hash de senhas via PBKDF2-HMAC-SHA256 (Camada 4 - Infraestrutura)."""

import hashlib
import hmac
import os

from src.application.ports.auth import IPasswordHasher


class Pbkdf2PasswordHasher(IPasswordHasher):
    """Implementa IPasswordHasher utilizando PBKDF2-HMAC-SHA256 da biblioteca padrão."""

    def __init__(self, iterations: int = 100_000) -> None:
        self._iterations = iterations

    def hash_password(self, password: str) -> str:
        salt = os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, self._iterations)
        return f"pbkdf2_sha256${self._iterations}${salt.hex()}${dk.hex()}"

    def verify_password(self, password: str, stored_hash: str) -> bool:
        if not isinstance(password, str) or not isinstance(stored_hash, str):
            return False

        parts = stored_hash.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False

        _, iter_str, salt_hex, dk_hex = parts
        try:
            iterations = int(iter_str)
            if iterations <= 0:
                return False
            salt = bytes.fromhex(salt_hex)
            expected_dk = bytes.fromhex(dk_hex)
        except ValueError:
            return False

        derived_dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(derived_dk, expected_dk)
