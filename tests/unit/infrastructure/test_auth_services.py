"""Testes unitários para os serviços de segurança: PBKDF2 e tokens AES-256-GCM."""

import time
from uuid import uuid4

import pytest

from src.infrastructure.security.dependencies import get_password_hasher, get_session_service
from src.infrastructure.security.password_hasher import Pbkdf2PasswordHasher
from src.infrastructure.security.session_service import AesGcmSessionTokenService


@pytest.mark.unit
@pytest.mark.security
def test_pbkdf2_password_hasher_generates_unique_salts_and_verifies() -> None:
    """Valida geração de hash PBKDF2-HMAC-SHA256 com salt aleatório único e verificação válida.

    Vulnerabilidade prevenida: Ataques de rainbow table e correlação de senhas idênticas (CWE-916).
    Garantia de segurança: Cada chamada gera um salt criptográfico de 16 bytes distinto,
    produzindo digests diferentes para a mesma senha e validando corretamente em tempo constante.
    """
    hasher = Pbkdf2PasswordHasher(iterations=10_000)
    password = "SenhaSegura@2026!"

    hash_a = hasher.hash_password(password)
    hash_b = hasher.hash_password(password)

    assert hash_a != hash_b
    assert hash_a != password
    assert hash_a.startswith("pbkdf2_sha256$10000$")
    assert len(hash_a.split("$")) == 4

    assert hasher.verify_password(password, hash_a) is True
    assert hasher.verify_password(password, hash_b) is True
    assert hasher.verify_password("SenhaErrada@2026!", hash_a) is False


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.parametrize(
    "malformed_hash",
    [
        "",
        "plaintext",
        "pbkdf2_sha256$10000$onlythree",
        "bcrypt$10000$abcd$ef01",
        "pbkdf2_sha256$notanint$abcd$ef01",
        "pbkdf2_sha256$0$abcd$ef01",
        "pbkdf2_sha256$-5$abcd$ef01",
        "pbkdf2_sha256$1000$zzzz$ef01",
        "pbkdf2_sha256$1000$abcd$zzzz",
    ],
)
def test_pbkdf2_password_hasher_rejects_malformed_hashes(malformed_hash: str) -> None:
    """Valida rejeição segura de hashes malformados, algoritmos desconhecidos ou iterações inválidas.

    Vulnerabilidade prevenida: Downgrade de algoritmo, bypass de verificação e exceções não tratadas (CWE-327).
    Garantia de segurança: Qualquer formato divergente de pbkdf2_sha256$<iter>$<salt>$<dk> retorna False.
    """
    hasher = Pbkdf2PasswordHasher(iterations=10_000)
    assert hasher.verify_password("QualquerSenha123", malformed_hash) is False


@pytest.mark.unit
def test_pbkdf2_password_hasher_rejects_non_string_inputs() -> None:
    """Garante que entradas não textuais retornem False sem lançar exceções."""
    hasher = Pbkdf2PasswordHasher(iterations=1_000)
    valid_hash = hasher.hash_password("Senha12345")
    assert hasher.verify_password(None, valid_hash) is False  # type: ignore[arg-type]
    assert hasher.verify_password("Senha12345", None) is False  # type: ignore[arg-type]


@pytest.mark.unit
@pytest.mark.security
def test_aes_gcm_session_token_create_and_verify() -> None:
    """Valida ciclo completo de emissão e decifração de token de sessão AES-256-GCM.

    Vulnerabilidade prevenida: Falsificação de sessão, adulteração de identidade de usuário
    e vazamento de credenciais na rede.
    Garantia de segurança: O token é criptografado e autenticado via AEAD (AES-256-GCM),
    garantindo confidencialidade e integridade inviolável em tempo de execução.
    """
    secret = "minha-chave-secreta-muito-segura-32b"
    service = AesGcmSessionTokenService(secret_key=secret, ttl_seconds=3600)
    user_id = uuid4()
    email = "aluno@universidade.br"

    token = service.create_session_token(user_id=user_id, email=email)
    assert isinstance(token, str)
    assert len(token) > 50

    payload = service.verify_session_token(token)
    assert payload is not None
    assert payload.user_id == user_id
    assert payload.email == email
    assert payload.exp > payload.iat


@pytest.mark.unit
@pytest.mark.security
def test_aes_gcm_session_token_expired_rejected() -> None:
    """Valida rejeição imediata de tokens de sessão expirados no tempo.

    Vulnerabilidade prevenida: Replay attacks e reaproveitamento de sessões antigas ou roubadas.
    Garantia de segurança: Tokens cujo timestamp exp é menor ou igual ao tempo corrente
    são rejeitados retornando None.
    """
    secret = "chave-secreta-teste-expiracao-12345"
    service = AesGcmSessionTokenService(secret_key=secret, ttl_seconds=1)
    user_id = uuid4()

    token = service.create_session_token(user_id=user_id, email="teste@exp.com")
    time.sleep(1.1)

    assert service.verify_session_token(token) is None


@pytest.mark.unit
@pytest.mark.security
def test_aes_gcm_session_token_tampered_rejected() -> None:
    """Valida que tokens com bits adulterados sejam sumariamente rejeitados pela tag GCM.

    Vulnerabilidade prevenida: Ataques de bit-flipping, adulteração de payload e
    privilege escalation.
    Garantia de segurança: Qualquer modificação no ciphertext ou nonce viola a tag de
    autenticação GCM, impedindo decifração.
    """
    secret = "chave-secreta-integridade-teste"
    service = AesGcmSessionTokenService(secret_key=secret)
    token = service.create_session_token(user_id=uuid4(), email="legitimo@teste.com")

    tampered = token[:-4] + "AAAA"
    assert service.verify_session_token(tampered) is None
    assert service.verify_session_token("token-invalido-curto") is None


@pytest.mark.unit
def test_aes_gcm_session_service_with_bytes_key() -> None:
    """Valida inicialização do AesGcmSessionTokenService fornecendo chave em bytes brutos."""
    raw_key = b"0123456789abcdef0123456789abcdef"
    service = AesGcmSessionTokenService(secret_key=raw_key)
    uid = uuid4()
    token = service.create_session_token(uid, "bytes@teste.com")
    payload = service.verify_session_token(token)
    assert payload is not None
    assert payload.user_id == uid


@pytest.mark.unit
def test_security_dependencies_providers() -> None:
    """Valida resolução das dependências get_password_hasher e get_session_service."""
    hasher = get_password_hasher()
    session_service = get_session_service()

    assert isinstance(hasher, Pbkdf2PasswordHasher)
    assert isinstance(session_service, AesGcmSessionTokenService)
