"""Testes para os serviços de segurança, tokens AES-256-GCM e Google OAuth (Sprint 02)."""

import time
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.application.dto.auth_dto import GoogleUserInfoDTO
from src.infrastructure.security.dependencies import get_google_client
from src.infrastructure.security.google_client import GoogleOAuthClient
from src.infrastructure.security.session_service import AesGcmSessionTokenService


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

    # Inverte os últimos caracteres do token em base64
    tampered = token[:-4] + "AAAA"
    assert service.verify_session_token(tampered) is None
    assert service.verify_session_token("token-invalido-curto") is None


@pytest.mark.unit
@pytest.mark.security
def test_oauth_state_generation_and_validation() -> None:
    """Valida criação e validação de state assinado com destino next_url para prevenção de CSRF.

    Vulnerabilidade prevenida: Cross-Site Request Forgery (CSRF) no fluxo de login federado
    OAuth 2.0.
    Garantia de segurança: O state contém payload assinado e criptografado com nonce,
    impedindo injeção de parâmetros ou login forçado por terceiros.
    """
    secret = "chave-para-validacao-csrf-state"
    service = AesGcmSessionTokenService(secret_key=secret, ttl_seconds=300)

    state = service.create_oauth_state(next_url="/flashcards/study")
    assert isinstance(state, str)

    resolved_next = service.verify_oauth_state(state)
    assert resolved_next == "/flashcards/study"

    # State inválido
    assert service.verify_oauth_state("state-falso-adulterado") is None


@pytest.mark.unit
def test_google_oauth_client_authorization_url() -> None:
    """Valida montagem correta da URL de autorização com escopos openid, email e profile."""
    client = GoogleOAuthClient(
        client_id="meu-client-id.apps.googleusercontent.com",
        client_secret="meu-secret",
    )
    url = client.get_authorization_url(
        state="xyz123", redirect_uri="http://localhost:8000/auth/callback"
    )

    assert "https://accounts.google.com/o/oauth2/auth" in url
    assert "client_id=meu-client-id.apps.googleusercontent.com" in url
    assert "state=xyz123" in url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fauth%2Fcallback" in url
    assert "response_type=code" in url
    assert "scope=" in url


@pytest.mark.unit
def test_google_oauth_client_exchange_code_success() -> None:
    """Valida troca de authorization code por dados do usuário com mock httpx."""
    client = GoogleOAuthClient(
        client_id="meu-client-id",
        client_secret="meu-secret",
    )

    fake_token_response = MagicMock()
    fake_token_response.status_code = 200
    fake_token_response.json.return_value = {"access_token": "fake-access-token"}

    fake_userinfo_response = MagicMock()
    fake_userinfo_response.status_code = 200
    fake_userinfo_response.json.return_value = {
        "sub": "google-sub-555",
        "email": "usuario@google.com",
        "name": "Nome Google",
        "picture": "https://lh3.google.com/avatar.jpg",
    }

    with patch("httpx.Client.post", return_value=fake_token_response):
        with patch("httpx.Client.get", return_value=fake_userinfo_response):
            user_info = client.exchange_code_for_user_info(
                code="auth-code-123",
                redirect_uri="http://localhost:8000/auth/callback",
            )

    assert isinstance(user_info, GoogleUserInfoDTO)
    assert user_info.sub == "google-sub-555"
    assert user_info.email == "usuario@google.com"
    assert user_info.name == "Nome Google"
    assert user_info.avatar_url == "https://lh3.google.com/avatar.jpg"


@pytest.mark.unit
def test_google_oauth_client_exchange_code_error_raises_exception() -> None:
    """Valida lançamento de exceção quando o Google retorna erro HTTP no token exchange."""
    client = GoogleOAuthClient(client_id="id", client_secret="secret")

    fake_response = MagicMock()
    fake_response.status_code = 400
    fake_response.text = "invalid_grant"

    with patch("httpx.Client.post", return_value=fake_response):
        with pytest.raises(ValueError, match="Erro ao trocar código com Google"):
            client.exchange_code_for_user_info("code-invalido", "http://callback")


@pytest.mark.unit
def test_google_oauth_client_exchange_code_userinfo_error() -> None:
    """Valida erro quando o endpoint de userinfo do Google responde com status != 200."""
    client = GoogleOAuthClient(client_id="id", client_secret="secret")

    fake_token_res = MagicMock()
    fake_token_res.status_code = 200
    fake_token_res.json.return_value = {"access_token": "token-xyz"}

    fake_userinfo_res = MagicMock()
    fake_userinfo_res.status_code = 401
    fake_userinfo_res.text = "unauthorized"

    with patch("httpx.Client.post", return_value=fake_token_res):
        with patch("httpx.Client.get", return_value=fake_userinfo_res):
            with pytest.raises(ValueError, match="Erro ao obter userinfo do Google"):
                client.exchange_code_for_user_info("code-123", "http://callback")


@pytest.mark.unit
def test_google_oauth_client_verify_id_token_success_and_error() -> None:
    """Valida método verify_id_token com resposta bem-sucedida e erro de validação."""
    client = GoogleOAuthClient(client_id="id", client_secret="secret")

    # Caso de Sucesso
    fake_success = MagicMock()
    fake_success.status_code = 200
    fake_success.json.return_value = {
        "sub": "sub-idtoken-123",
        "email": "idtoken@google.com",
        "name": "ID Token User",
        "picture": "https://picture.png",
    }
    with patch("httpx.Client.get", return_value=fake_success):
        info = client.verify_id_token("valid-jwt-token")
        assert info.sub == "sub-idtoken-123"
        assert info.email == "idtoken@google.com"

    # Caso de Erro
    fake_err = MagicMock()
    fake_err.status_code = 400
    fake_err.text = "invalid_id_token"
    with patch("httpx.Client.get", return_value=fake_err):
        with pytest.raises(ValueError, match="ID Token do Google inválido"):
            client.verify_id_token("bad-token")


@pytest.mark.unit
def test_aes_gcm_session_service_with_bytes_key() -> None:
    """Valida inicialização do AesGcmSessionTokenService fornecendo chave em bytes brutos."""
    raw_key = b"0123456789abcdef0123456789abcdef"  # 32 bytes
    service = AesGcmSessionTokenService(secret_key=raw_key)
    uid = uuid4()
    token = service.create_session_token(uid, "bytes@teste.com")
    payload = service.verify_session_token(token)
    assert payload is not None
    assert payload.user_id == uid


@pytest.mark.unit
def test_oauth_state_invalid_type_or_expired() -> None:
    """Valida rejeição de state expirado ou com payload de tipo incorreto."""
    import json

    service = AesGcmSessionTokenService(secret_key="segredo-qualquer")

    # 1. State expirado
    expired_payload = {
        "type": "oauth_state",
        "next": "/study",
        "exp": int(time.time()) - 10,
    }
    expired_state = service._cipher.encrypt(json.dumps(expired_payload))
    assert service.verify_oauth_state(expired_state) is None

    # 2. State com tipo inválido
    wrong_type_payload = {
        "type": "other_token",
        "next": "/study",
        "exp": int(time.time()) + 600,
    }
    wrong_state = service._cipher.encrypt(json.dumps(wrong_type_payload))
    assert service.verify_oauth_state(wrong_state) is None


@pytest.mark.unit
def test_get_google_client_dependency() -> None:
    """Valida resolução da dependência get_google_client do FastAPI."""
    client = get_google_client()
    assert isinstance(client, GoogleOAuthClient)
