"""Módulo de criptografia autenticada com AES-256-GCM (Camada 4 - Infraestrutura).

Garante confidencialidade e integridade (AEAD) para dados e segredos armazenados.
"""

import base64
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CryptoError(Exception):
    """Exceção levantada quando ocorre erro na cifragem ou validação de integridade."""


class AES256GCMCipher:
    """Implementa cifragem e decifragem autenticada usando AES-256 no modo GCM."""

    NONCE_SIZE = 12  # 96 bits recomendado pelo NIST para AES-GCM

    def __init__(self, key: bytes) -> None:
        if len(key) != 32:
            raise ValueError("A chave AES-256 deve possuir exatamente 32 bytes (256 bits).")
        self._key = key
        self._aesgcm = AESGCM(self._key)

    def encrypt(self, plaintext: str) -> str:
        """Cifra uma string em texto plano gerando payload contendo nonce + ciphertext

        autenticado em base64.
        """
        nonce = os.urandom(self.NONCE_SIZE)
        ciphertext_bytes = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        combined = nonce + ciphertext_bytes
        return base64.b64encode(combined).decode("utf-8")

    def decrypt(self, encoded_payload: str) -> str:
        """Decifra uma string base64 validando o nonce e a tag de autenticação GCM."""
        try:
            raw_data = base64.b64decode(encoded_payload, validate=True)
        except Exception as exc:
            raise CryptoError("Falha na decodificação base64 do dado cifrado.") from exc

        if len(raw_data) <= self.NONCE_SIZE:
            raise CryptoError("Tamanho do dado cifrado é menor que o nonce obrigatório.")

        nonce = raw_data[: self.NONCE_SIZE]
        ciphertext = raw_data[self.NONCE_SIZE :]

        try:
            decrypted_bytes = self._aesgcm.decrypt(nonce, ciphertext, None)
            return decrypted_bytes.decode("utf-8")
        except InvalidTag as exc:
            raise CryptoError("Falha na autenticação ou integridade do dado cifrado.") from exc
