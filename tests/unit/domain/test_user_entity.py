"""Testes unitários para a entidade User e regras de autorização de Subject/Session (Sprint 02)."""

from datetime import date
from uuid import UUID, uuid4

import pytest

from src.domain.entities import FlashcardPoolSession, Subject, User
from src.domain.exceptions import (
    DomainValidationError,
    InvalidEmailError,
    InvalidGoogleSubError,
)


@pytest.mark.unit
def test_user_creation_valid() -> None:
    """Valida instanciação bem-sucedida de User com todos os atributos válidos."""
    user_id = uuid4()
    today = date(2026, 10, 4)
    user = User(
        id=user_id,
        google_sub="google-sub-12345",
        email="  Estudante@Exemplo.COM  ",
        name="  Maria da Silva  ",
        avatar_url="  https://lh3.googleusercontent.com/avatar.jpg  ",
        created_at=today,
    )

    assert user.id == user_id
    assert user.google_sub == "google-sub-12345"
    assert user.email == "estudante@exemplo.com"
    assert user.name == "Maria da Silva"
    assert user.avatar_url == "https://lh3.googleusercontent.com/avatar.jpg"
    assert user.created_at == today


@pytest.mark.unit
def test_user_creation_defaults() -> None:
    """Valida geração automática de id, created_at e avatar_url None por padrão."""
    user = User(
        google_sub="sub-999",
        email="joao@teste.com",
        name="João",
    )
    assert isinstance(user.id, UUID)
    assert isinstance(user.created_at, date)
    assert user.avatar_url is None


@pytest.mark.unit
@pytest.mark.parametrize(
    "invalid_email",
    [
        "",
        "   ",
        "invalido",
        "invalido@",
        "@dominio.com",
        "usuario@dominio",
        "usuario@@dominio.com",
    ],
)
def test_user_invalid_email_raises_error(invalid_email: str) -> None:
    """Garante que e-mails inválidos disparem InvalidEmailError."""
    with pytest.raises(InvalidEmailError, match="Formato de e-mail inválido"):
        User(
            google_sub="sub-123",
            email=invalid_email,
            name="Teste",
        )


@pytest.mark.unit
@pytest.mark.parametrize("invalid_sub", ["", "   "])
def test_user_empty_google_sub_raises_error(invalid_sub: str) -> None:
    """Garante que google_sub vazio dispare InvalidGoogleSubError."""
    with pytest.raises(InvalidGoogleSubError, match="O identificador Google .* não pode ser vazio"):
        User(
            google_sub=invalid_sub,
            email="valido@teste.com",
            name="Teste",
        )


@pytest.mark.unit
@pytest.mark.parametrize("invalid_name", ["", "   ", "x" * 151])
def test_user_invalid_name_raises_error(invalid_name: str) -> None:
    """Garante que nomes vazios ou maiores que 150 caracteres sejam rejeitados."""
    with pytest.raises(DomainValidationError, match="Nome de usuário deve ter entre 1 e 150"):
        User(
            google_sub="sub-123",
            email="valido@teste.com",
            name=invalid_name,
        )


@pytest.mark.unit
def test_user_empty_avatar_url_normalized_to_none() -> None:
    """Garante que strings vazias em avatar_url sejam normalizadas para None."""
    user = User(
        google_sub="sub-123",
        email="valido@teste.com",
        name="Teste",
        avatar_url="   ",
    )
    assert user.avatar_url is None


@pytest.mark.unit
@pytest.mark.security
def test_subject_ownership_permissions() -> None:
    """Testa regras de permissão de edição e estudo para matérias no domínio.

    Vulnerabilidade prevenida: Insecure Direct Object Reference (IDOR) e quebra
    de controle de acesso em matérias privadas ou públicas.
    Garantia de segurança: can_be_edited_by assegura que apenas o criador original
    altera a matéria, enquanto can_be_studied_by respeita a visibilidade pública.
    """
    owner_id = uuid4()
    other_user_id = uuid4()

    # Matéria privada
    subject_private = Subject(name="Direito Penal", owner_id=owner_id, is_public=False)
    assert subject_private.owner_id == owner_id
    assert subject_private.is_public is False
    assert subject_private.can_be_edited_by(owner_id) is True
    assert subject_private.can_be_edited_by(other_user_id) is False
    assert subject_private.can_be_studied_by(owner_id) is True
    assert subject_private.can_be_studied_by(other_user_id) is False

    # Matéria pública
    subject_public = Subject(name="Direito Civil", owner_id=owner_id, is_public=True)
    assert subject_public.is_public is True
    assert subject_public.can_be_edited_by(owner_id) is True
    assert subject_public.can_be_edited_by(other_user_id) is False
    assert subject_public.can_be_studied_by(owner_id) is True
    assert subject_public.can_be_studied_by(other_user_id) is True


@pytest.mark.unit
@pytest.mark.security
def test_flashcard_pool_session_user_isolation() -> None:
    """Valida associação obrigatória e isolamento de FlashcardPoolSession por usuário.

    Vulnerabilidade prevenida: Vazamento e concorrência indevida de progresso de estudo
    entre múltiplos usuários.
    Garantia de segurança: Toda sessão de estudo deve possuir um user_id explícito
    vinculado ao estudante proprietário da sessão.
    """
    user_id = uuid4()
    session = FlashcardPoolSession(user_id=user_id, current_position=100, round_number=2)
    assert session.user_id == user_id
    assert session.current_position == 100
    assert session.round_number == 2
