"""Testes de segurança e integridade para a cifra AES-256-GCM (Camada 4 - Infraestrutura)."""

import os

import pytest

from src.infrastructure.security.crypto import AES256GCMCipher, CryptoError


@pytest.mark.security
def test_aes_gcm_encrypt_decrypt_roundtrip() -> None:
    """Vulnerabilidade prevenida: Exposição de dados sensíveis ou tokens em repouso

    sem criptografia.

    Garantia de segurança: Assegura que o texto plano seja encriptado com AES-256-GCM
    e decifrado fielmente com a chave correta.
    """
    key = os.urandom(32)  # 256 bits
    cipher = AES256GCMCipher(key)
    plaintext = "ChaveSecretaDeApiSuperConfidencial-12345"

    ciphertext = cipher.encrypt(plaintext)
    assert ciphertext != plaintext
    assert isinstance(ciphertext, str)

    decrypted = cipher.decrypt(ciphertext)
    assert decrypted == plaintext


@pytest.mark.security
def test_aes_gcm_ciphertext_tampering_fails() -> None:
    """Vulnerabilidade prevenida: Manipulação indevida ou adulteração de dados cifrados

    (Bit-flipping).

    Garantia de segurança: Assegura que o algoritmo de Criptografia Autenticada (AEAD)
    rejeite dados alterados através da validação da tag de autenticação GCM.
    """
    key = os.urandom(32)
    cipher = AES256GCMCipher(key)
    plaintext = "Mensagem ultra confidencial"

    ciphertext = cipher.encrypt(plaintext)

    # Modifica o último caractere do ciphertext codificado em base64
    tampered_bytes = bytearray(ciphertext.encode("utf-8"))
    tampered_bytes[-2] = ord("A") if tampered_bytes[-2] != ord("A") else ord("B")
    tampered_ciphertext = tampered_bytes.decode("utf-8")

    with pytest.raises(CryptoError, match="Falha na autenticação ou integridade do dado cifrado."):
        cipher.decrypt(tampered_ciphertext)


@pytest.mark.security
def test_aes_gcm_invalid_key_length() -> None:
    """Vulnerabilidade prevenida: Uso de chaves criptográficas fracas com tamanho inferior

    a 256 bits.

    Garantia de segurança: Assegura que o construtor da cifra rejeite chaves que não
    possuam rigorosamente 32 bytes (256 bits) de entropia.
    """
    weak_key = b"chave-curta-de-16"  # 17 bytes
    with pytest.raises(ValueError, match="A chave AES-256 deve possuir exatamente 32 bytes"):
        AES256GCMCipher(weak_key)


@pytest.mark.security
def test_aes_gcm_corrupted_payload_structure() -> None:
    """Vulnerabilidade prevenida: Negação de serviço ou injeção de payloads corrompidos

    no decodificador.

    Garantia de segurança: Assegura que strings inválidas em base64 ou com tamanho inferior
    ao nonce + tag disparem exceção sem causar crash no processo.
    """
    key = os.urandom(32)
    cipher = AES256GCMCipher(key)

    with pytest.raises(CryptoError):
        cipher.decrypt("not-valid-base64!!!")

    with pytest.raises(CryptoError):
        cipher.decrypt("AAAA")  # Base64 válido porém menor que o nonce obrigatório
