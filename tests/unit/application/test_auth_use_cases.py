"""Testes unitários para os casos de uso de Autenticação, Usuários e Multi-tenancy (Sprint 02)."""

from uuid import UUID, uuid4

import pytest

from src.application.dto.auth_dto import (
    GoogleAuthInputDTO,
    GoogleUserInfoDTO,
    SessionPayloadDTO,
)
from src.application.dto.subject_dto import CreateSubjectDTO
from src.application.dto.topic_dto import CreateTopicDTO
from src.application.ports.auth import IGoogleAuthClient, ISessionTokenService
from src.application.ports.repositories import (
    ISubjectRepository,
    ITopicRepository,
    IUserRepository,
)
from src.application.use_cases.auth_use_cases import (
    AuthenticateWithGoogleUseCase,
    GetCurrentUserUseCase,
    LogoutUseCase,
    ToggleSubjectPublicUseCase,
)
from src.application.use_cases.subject_use_cases import (
    CreateSubjectUseCase,
    ListSubjectsUseCase,
)
from src.application.use_cases.topic_use_cases import CreateTopicUseCase
from src.domain.entities import Subject, Topic, User
from src.domain.exceptions import (
    DomainValidationError,
    EntityNotFoundError,
    ResourceOwnershipError,
    UnauthorizedError,
)


class InMemoryUserRepository(IUserRepository):
    """Repositório fake em memória para testes de User."""

    def __init__(self) -> None:
        self.users: dict[UUID, User] = {}

    def save(self, user: User) -> None:
        self.users[user.id] = user

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.users.get(user_id)

    def get_by_google_sub(self, google_sub: str) -> User | None:
        for u in self.users.values():
            if u.google_sub == google_sub:
                return u
        return None

    def get_by_email(self, email: str) -> User | None:
        for u in self.users.values():
            if u.email == email.lower().strip():
                return u
        return None


class FakeGoogleAuthClient(IGoogleAuthClient):
    """Cliente fake do Google OIDC para testes isolados."""

    def __init__(self) -> None:
        self.code_to_user_info: dict[str, GoogleUserInfoDTO] = {}
        self.token_to_user_info: dict[str, GoogleUserInfoDTO] = {}

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        return (
            f"https://accounts.google.com/o/oauth2/auth?state={state}&redirect_uri={redirect_uri}"
        )

    def exchange_code_for_user_info(self, code: str, redirect_uri: str) -> GoogleUserInfoDTO:
        if code in self.code_to_user_info:
            return self.code_to_user_info[code]
        raise ValueError("Invalid authorization code")

    def verify_id_token(self, id_token: str) -> GoogleUserInfoDTO:
        if id_token in self.token_to_user_info:
            return self.token_to_user_info[id_token]
        raise ValueError("Invalid id_token")


class FakeSessionTokenService(ISessionTokenService):
    """Serviço fake de token de sessão para testes de use cases."""

    def __init__(self) -> None:
        self.tokens: dict[str, SessionPayloadDTO] = {}

    def create_session_token(self, user_id: UUID, email: str) -> str:
        token = f"fake-session-{user_id}"
        self.tokens[token] = SessionPayloadDTO(
            user_id=user_id,
            email=email,
            iat=1000,
            exp=2000,
        )
        return token

    def verify_session_token(self, token: str) -> SessionPayloadDTO | None:
        return self.tokens.get(token)

    def create_oauth_state(self, next_url: str = "") -> str:
        return f"fake-state-{next_url}"

    def verify_oauth_state(self, state: str) -> str | None:
        if state.startswith("fake-state-"):
            return state.removeprefix("fake-state-")
        return None


class InMemorySubjectRepository(ISubjectRepository):
    """Repositório fake em memória para Matérias com suporte a multi-tenancy."""

    def __init__(self) -> None:
        self.subjects: dict[UUID, Subject] = {}

    def save(self, subject: Subject) -> None:
        self.subjects[subject.id] = subject

    def get_by_id(self, subject_id: UUID) -> Subject | None:
        return self.subjects.get(subject_id)

    def list_all(self) -> list[Subject]:
        return list(self.subjects.values())

    def list_by_owner(self, owner_id: UUID) -> list[Subject]:
        return [s for s in self.subjects.values() if s.owner_id == owner_id]

    def list_accessible(self, user_id: UUID) -> list[Subject]:
        return [s for s in self.subjects.values() if s.owner_id == user_id or s.is_public]

    def exists_by_name(self, name: str, owner_id: UUID | None = None) -> bool:
        clean = name.strip().lower()
        for s in self.subjects.values():
            if s.name.lower() == clean:
                if owner_id is None or s.owner_id == owner_id:
                    return True
        return False

    def list_all_with_topics(
        self, user_id: UUID | None = None
    ) -> list[tuple[Subject, list[Topic]]]:
        if user_id is None:
            return [(s, []) for s in self.subjects.values()]
        return [(s, []) for s in self.subjects.values() if s.owner_id == user_id or s.is_public]


class InMemoryTopicRepository(ITopicRepository):
    """Repositório fake em memória para Temas."""

    def __init__(self) -> None:
        self.topics: dict[UUID, Topic] = {}

    def save(self, topic: Topic) -> None:
        self.topics[topic.id] = topic

    def get_by_id(self, topic_id: UUID) -> Topic | None:
        return self.topics.get(topic_id)

    def list_by_subject(self, subject_id: UUID) -> list[Topic]:
        return [t for t in self.topics.values() if t.subject_id == subject_id]

    def exists_by_name(self, subject_id: UUID, name: str) -> bool:
        clean = name.strip().lower()
        for t in self.topics.values():
            if t.subject_id == subject_id and t.name.lower() == clean:
                return True
        return False


@pytest.mark.unit
def test_authenticate_with_google_first_time_jit_provisioning() -> None:
    """Valida provisionamento JIT de novo usuário a partir de authorization code do Google."""
    user_repo = InMemoryUserRepository()
    google_client = FakeGoogleAuthClient()
    token_service = FakeSessionTokenService()

    google_client.code_to_user_info["valid-code"] = GoogleUserInfoDTO(
        sub="google-sub-123",
        email="novo@estudante.com",
        name="Estudante Novo",
        avatar_url="https://avatar.google.com/novo.png",
    )

    use_case = AuthenticateWithGoogleUseCase(
        google_client=google_client,
        user_repo=user_repo,
        token_service=token_service,
    )

    result = use_case.execute(GoogleAuthInputDTO(code="valid-code"))

    assert result.is_new_user is True
    assert result.email == "novo@estudante.com"
    assert result.name == "Estudante Novo"
    assert result.avatar_url == "https://avatar.google.com/novo.png"
    assert result.session_token.startswith("fake-session-")

    saved_user = user_repo.get_by_google_sub("google-sub-123")
    assert saved_user is not None
    assert saved_user.id == result.user_id


@pytest.mark.unit
def test_authenticate_with_google_existing_user_syncs_profile() -> None:
    """Valida que usuário já cadastrado tem seus dados mutáveis (nome/avatar) sincronizados."""
    user_repo = InMemoryUserRepository()
    google_client = FakeGoogleAuthClient()
    token_service = FakeSessionTokenService()

    existing_user = User(
        google_sub="google-sub-456",
        email="maria@estudo.com",
        name="Maria Antiga",
        avatar_url="https://antigo.png",
    )
    user_repo.save(existing_user)

    google_client.code_to_user_info["code-maria"] = GoogleUserInfoDTO(
        sub="google-sub-456",
        email="maria@estudo.com",
        name="Maria Atualizada",
        avatar_url="https://novo.png",
    )

    use_case = AuthenticateWithGoogleUseCase(
        google_client=google_client,
        user_repo=user_repo,
        token_service=token_service,
    )

    result = use_case.execute(GoogleAuthInputDTO(code="code-maria"))

    assert result.is_new_user is False
    assert result.user_id == existing_user.id
    assert result.name == "Maria Atualizada"
    assert result.avatar_url == "https://novo.png"

    updated_user = user_repo.get_by_id(existing_user.id)
    assert updated_user is not None
    assert updated_user.name == "Maria Atualizada"
    assert updated_user.avatar_url == "https://novo.png"


@pytest.mark.unit
def test_authenticate_with_google_via_id_token() -> None:
    """Valida autenticação com id_token para consumo por API REST / Mobile Flutter."""
    user_repo = InMemoryUserRepository()
    google_client = FakeGoogleAuthClient()
    token_service = FakeSessionTokenService()

    google_client.token_to_user_info["valid-id-token"] = GoogleUserInfoDTO(
        sub="mobile-sub-789",
        email="flutter@app.com",
        name="Mobile User",
    )

    use_case = AuthenticateWithGoogleUseCase(
        google_client=google_client,
        user_repo=user_repo,
        token_service=token_service,
    )

    result = use_case.execute(GoogleAuthInputDTO(id_token="valid-id-token"))
    assert result.is_new_user is True
    assert result.email == "flutter@app.com"


@pytest.mark.unit
def test_authenticate_with_google_missing_credentials_raises_error() -> None:
    """Garante que requisição sem code e sem id_token seja rejeitada."""
    user_repo = InMemoryUserRepository()
    google_client = FakeGoogleAuthClient()
    token_service = FakeSessionTokenService()

    use_case = AuthenticateWithGoogleUseCase(
        google_client=google_client,
        user_repo=user_repo,
        token_service=token_service,
    )

    with pytest.raises(DomainValidationError, match="Código ou ID Token do Google é obrigatório"):
        use_case.execute(GoogleAuthInputDTO())


@pytest.mark.unit
def test_get_current_user_success() -> None:
    """Valida resolução da entidade do usuário logado a partir de token válido."""
    user_repo = InMemoryUserRepository()
    token_service = FakeSessionTokenService()

    user = User(google_sub="sub-1", email="user@teste.com", name="User Teste")
    user_repo.save(user)
    token = token_service.create_session_token(user.id, user.email)

    use_case = GetCurrentUserUseCase(token_service=token_service, user_repo=user_repo)
    user_dto = use_case.execute(token)

    assert user_dto.id == user.id
    assert user_dto.email == "user@teste.com"
    assert user_dto.name == "User Teste"


@pytest.mark.unit
def test_get_current_user_invalid_or_expired_token_raises_unauthorized() -> None:
    """Garante que token inválido dispare UnauthorizedError."""
    user_repo = InMemoryUserRepository()
    token_service = FakeSessionTokenService()

    use_case = GetCurrentUserUseCase(token_service=token_service, user_repo=user_repo)
    with pytest.raises(UnauthorizedError, match="Sessão inválida ou expirada"):
        use_case.execute("token-inexistente")


@pytest.mark.unit
def test_get_current_user_deleted_user_raises_unauthorized() -> None:
    """Garante que token válido para usuário removido do banco dispare UnauthorizedError."""
    user_repo = InMemoryUserRepository()
    token_service = FakeSessionTokenService()

    user_id = uuid4()
    token = token_service.create_session_token(user_id, "apagado@teste.com")

    use_case = GetCurrentUserUseCase(token_service=token_service, user_repo=user_repo)
    with pytest.raises(UnauthorizedError, match="Usuário da sessão não encontrado"):
        use_case.execute(token)


@pytest.mark.unit
def test_logout_use_case() -> None:
    """Valida execução limpa do caso de uso de logout."""
    token_service = FakeSessionTokenService()
    use_case = LogoutUseCase(token_service=token_service)
    # Não deve lançar exceção
    use_case.execute("any-token")


@pytest.mark.unit
@pytest.mark.security
def test_toggle_subject_public_by_owner() -> None:
    """Testa alternância de visibilidade pública de matéria pelo proprietário legítimo.

    Vulnerabilidade prevenida: Exposição indevida de dados ou perda de controle de privacidade.
    Garantia de segurança: Apenas o owner_id da matéria tem permissão para
    torná-la pública ou privada.
    """
    subject_repo = InMemorySubjectRepository()
    owner_id = uuid4()
    subject = Subject(name="Direito Constitucional", owner_id=owner_id, is_public=False)
    subject_repo.save(subject)

    use_case = ToggleSubjectPublicUseCase(subject_repo=subject_repo)
    dto = use_case.execute(user_id=owner_id, subject_id=subject.id, is_public=True)

    assert dto.is_public is True
    saved_subj = subject_repo.get_by_id(subject.id)
    assert saved_subj is not None
    assert saved_subj.is_public is True


@pytest.mark.unit
@pytest.mark.security
def test_toggle_subject_public_by_non_owner_raises_ownership_error() -> None:
    """Garante que não-proprietários não consigam alterar a visibilidade de matérias de terceiros.

    Vulnerabilidade prevenida: Insecure Direct Object Reference (IDOR) e adulteração não autorizada.
    Garantia de segurança: Lança ResourceOwnershipError e rejeita mutação caso user_id != owner_id.
    """
    subject_repo = InMemorySubjectRepository()
    owner_id = uuid4()
    attacker_id = uuid4()
    subject = Subject(name="Direito Tributário", owner_id=owner_id, is_public=False)
    subject_repo.save(subject)

    use_case = ToggleSubjectPublicUseCase(subject_repo=subject_repo)
    with pytest.raises(
        ResourceOwnershipError, match="Você não tem permissão para alterar esta matéria"
    ):
        use_case.execute(user_id=attacker_id, subject_id=subject.id, is_public=True)

    saved_subj = subject_repo.get_by_id(subject.id)
    assert saved_subj is not None
    assert saved_subj.is_public is False


@pytest.mark.unit
def test_toggle_subject_public_non_existent_raises_not_found() -> None:
    """Garante que matéria inexistente dispare EntityNotFoundError."""
    subject_repo = InMemorySubjectRepository()
    use_case = ToggleSubjectPublicUseCase(subject_repo=subject_repo)
    with pytest.raises(EntityNotFoundError, match="Matéria não encontrada"):
        use_case.execute(user_id=uuid4(), subject_id=uuid4(), is_public=True)


@pytest.mark.unit
@pytest.mark.security
def test_create_topic_with_ownership_validation() -> None:
    """Valida que apenas o dono da matéria possa cadastrar tópicos nela.

    Vulnerabilidade prevenida: Injeção de tópicos não autorizados em matéria alheia (IDOR).
    Garantia de segurança: CreateTopicUseCase verifica can_be_edited_by antes de persistir o tópico.
    """
    subject_repo = InMemorySubjectRepository()
    topic_repo = InMemoryTopicRepository()
    owner_id = uuid4()
    other_user_id = uuid4()

    subject = Subject(name="História", owner_id=owner_id, is_public=True)
    subject_repo.save(subject)

    use_case = CreateTopicUseCase(topic_repo=topic_repo, subject_repo=subject_repo)

    # Não-dono tentando criar tópico mesmo em matéria pública
    with pytest.raises(ResourceOwnershipError, match="Você não tem permissão para adicionar temas"):
        use_case.execute(
            CreateTopicDTO(subject_id=subject.id, name="Revolução Francesa"),
            user_id=other_user_id,
        )

    # Dono criando tópico
    dto = use_case.execute(
        CreateTopicDTO(subject_id=subject.id, name="Revolução Francesa"),
        user_id=owner_id,
    )
    assert dto.name == "Revolução Francesa"
    assert dto.subject_id == subject.id


@pytest.mark.unit
def test_create_and_list_subjects_multi_tenant() -> None:
    """Valida isolamento multi-tenant e listagem de matérias acessíveis (próprias + públicas)."""
    subject_repo = InMemorySubjectRepository()
    create_uc = CreateSubjectUseCase(subject_repo=subject_repo)
    list_uc = ListSubjectsUseCase(subject_repo=subject_repo)

    user_a = uuid4()
    user_b = uuid4()

    # User A cria 1 privada e 1 pública
    create_uc.execute(CreateSubjectDTO(name="Matéria A Privada", is_public=False), owner_id=user_a)
    create_uc.execute(CreateSubjectDTO(name="Matéria A Pública", is_public=True), owner_id=user_a)

    # User B cria 1 privada
    create_uc.execute(CreateSubjectDTO(name="Matéria B Privada", is_public=False), owner_id=user_b)

    # Listagem de User A: vê suas 2
    subs_a = list_uc.execute(user_id=user_a)
    assert len(subs_a) == 2
    assert all(s.is_owner for s in subs_a)

    # Listagem de User B: vê sua própria privada + a pública de A
    subs_b = list_uc.execute(user_id=user_b)
    assert len(subs_b) == 2
    names_b = {s.name for s in subs_b}
    assert "Matéria B Privada" in names_b
    assert "Matéria A Pública" in names_b
    public_from_a = next(s for s in subs_b if s.name == "Matéria A Pública")
    assert public_from_a.is_owner is False


@pytest.mark.unit
def test_authenticate_google_existing_user_linked_by_email_updates_sub() -> None:
    """Valida que quando um usuário é localizado por e-mail, seu google_sub é
    devidamente atualizado.
    """
    google_client = FakeGoogleAuthClient()
    user_repo = InMemoryUserRepository()
    token_service = FakeSessionTokenService()

    # Usuário pré-existente (ex: vindo de migração) com sub genérico
    existing_user = User(
        google_sub="system-migration-sub",
        email="migrado@aluno.com",
        name="Aluno Antigo",
        avatar_url="https://antigo.png",
    )
    user_repo.save(existing_user)

    # Google retorna o mesmo e-mail, mas novo sub oficial
    google_client.code_to_user_info["code-123"] = GoogleUserInfoDTO(
        sub="google-official-sub-999",
        email="migrado@aluno.com",
        name="Aluno Atualizado",
        avatar_url="https://novo.png",
    )

    use_case = AuthenticateWithGoogleUseCase(
        google_client=google_client,
        user_repo=user_repo,
        token_service=token_service,
    )
    result = use_case.execute(
        GoogleAuthInputDTO(code="code-123", redirect_uri="http://localhost:8000/auth/callback")
    )

    assert result.user_id == existing_user.id
    assert result.is_new_user is False
    assert result.name == "Aluno Atualizado"

    # Confirma que no repositório o google_sub foi atualizado
    updated_user = user_repo.get_by_id(existing_user.id)
    assert updated_user is not None
    assert updated_user.google_sub == "google-official-sub-999"
    assert updated_user.name == "Aluno Atualizado"
    assert updated_user.avatar_url == "https://novo.png"
