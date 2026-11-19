"""Testes unitários para os casos de uso de Autenticação Local, Demo, Usuários e Multi-tenancy."""

from uuid import UUID, uuid4

import pytest

from src.application.dto.auth_dto import (
    LocalLoginInputDTO,
    LocalRegisterInputDTO,
    SessionPayloadDTO,
)
from src.application.dto.subject_dto import CreateSubjectDTO
from src.application.dto.topic_dto import CreateTopicDTO
from src.application.ports.auth import IPasswordHasher, ISessionTokenService
from src.application.ports.repositories import (
    ISubjectRepository,
    ITopicRepository,
    IUserRepository,
)
from src.application.use_cases.auth_use_cases import (
    DEMO_EMAIL,
    DEMO_GOOGLE_SUB,
    DEMO_NAME,
    AuthenticateDemoUserUseCase,
    AuthenticateLocalUserUseCase,
    DeleteAccountUseCase,
    GetCurrentUserUseCase,
    LogoutUseCase,
    RegisterLocalUserUseCase,
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
    DuplicateEntityError,
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
        clean = email.lower().strip()
        for u in self.users.values():
            if u.email == clean:
                return u
        return None

    def delete(self, user_id: UUID) -> None:
        self.users.pop(user_id, None)


class FakePasswordHasher(IPasswordHasher):
    """Hasher fake determinístico para testes unitários de autenticação."""

    def hash_password(self, password: str) -> str:
        return f"hashed::{password}"

    def verify_password(self, password: str, stored_hash: str) -> bool:
        return stored_hash == f"hashed::{password}"


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
def test_register_local_user_success() -> None:
    """Valida cadastro de conta local com normalização de dados, hash de senha e emissão de sessão."""
    user_repo = InMemoryUserRepository()
    hasher = FakePasswordHasher()
    token_service = FakeSessionTokenService()

    use_case = RegisterLocalUserUseCase(
        user_repo=user_repo,
        password_hasher=hasher,
        token_service=token_service,
    )

    result = use_case.execute(
        LocalRegisterInputDTO(
            email="  Novo.Aluno@Exemplo.COM ",
            name="  Estudante Novo  ",
            password="SenhaForte123!",
        )
    )

    assert result.is_new_user is True
    assert result.email == "novo.aluno@exemplo.com"
    assert result.name == "Estudante Novo"
    assert result.avatar_url is None
    assert result.session_token.startswith("fake-session-")

    saved = user_repo.get_by_email("novo.aluno@exemplo.com")
    assert saved is not None
    assert saved.id == result.user_id
    assert saved.google_sub == "local:novo.aluno@exemplo.com"
    assert saved.password_hash == "hashed::SenhaForte123!"


@pytest.mark.unit
@pytest.mark.parametrize("bad_password", ["", "1234567", "   1234567   ", "x" * 129])
def test_register_local_user_invalid_password_length_raises_error(bad_password: str) -> None:
    """Garante que senhas menores que 8 ou maiores que 128 caracteres sejam rejeitadas."""
    use_case = RegisterLocalUserUseCase(
        user_repo=InMemoryUserRepository(),
        password_hasher=FakePasswordHasher(),
        token_service=FakeSessionTokenService(),
    )

    with pytest.raises(DomainValidationError, match="entre 8 e 128 caracteres"):
        use_case.execute(
            LocalRegisterInputDTO(
                email="aluno@teste.com",
                name="Aluno",
                password=bad_password,
            )
        )


@pytest.mark.unit
def test_register_local_user_duplicate_email_raises_error() -> None:
    """Garante que cadastro com e-mail já existente (case-insensitive) dispare DuplicateEntityError."""
    user_repo = InMemoryUserRepository()
    user_repo.save(
        User(
            google_sub="local:duplicado@teste.com",
            email="duplicado@teste.com",
            name="Existente",
            password_hash="hashed::Senha1234",
        )
    )

    use_case = RegisterLocalUserUseCase(
        user_repo=user_repo,
        password_hasher=FakePasswordHasher(),
        token_service=FakeSessionTokenService(),
    )

    with pytest.raises(DuplicateEntityError, match="Já existe uma conta cadastrada"):
        use_case.execute(
            LocalRegisterInputDTO(
                email="  DUPLICADO@Teste.COM  ",
                name="Novo",
                password="SenhaValida123",
            )
        )


@pytest.mark.unit
@pytest.mark.security
def test_register_local_user_never_stores_plaintext_password() -> None:
    """Valida que a senha informada no registro é sempre convertida em hash criptográfico.

    Vulnerabilidade prevenida: Exposição de senhas em texto claro em caso de vazamento de banco de dados (CWE-256).
    Garantia de segurança: RegisterLocalUserUseCase invoca IPasswordHasher e persiste somente o digest resultante.
    """
    user_repo = InMemoryUserRepository()
    hasher = FakePasswordHasher()
    token_service = FakeSessionTokenService()
    raw_password = "MinhaSenhaUltraSecreta99!"

    use_case = RegisterLocalUserUseCase(
        user_repo=user_repo,
        password_hasher=hasher,
        token_service=token_service,
    )
    res = use_case.execute(
        LocalRegisterInputDTO(
            email="seguro@teste.com",
            name="Usuário Seguro",
            password=raw_password,
        )
    )

    saved = user_repo.get_by_id(res.user_id)
    assert saved is not None
    assert saved.password_hash is not None
    assert saved.password_hash != raw_password
    assert hasher.verify_password(raw_password, saved.password_hash) is True


@pytest.mark.unit
def test_authenticate_local_user_success() -> None:
    """Valida autenticação local bem-sucedida com normalização do e-mail e emissão de token."""
    user_repo = InMemoryUserRepository()
    hasher = FakePasswordHasher()
    token_service = FakeSessionTokenService()

    existing = User(
        google_sub="local:maria@estudo.com",
        email="maria@estudo.com",
        name="Maria",
        password_hash=hasher.hash_password("SenhaCorreta123"),
    )
    user_repo.save(existing)

    use_case = AuthenticateLocalUserUseCase(
        user_repo=user_repo,
        password_hasher=hasher,
        token_service=token_service,
    )
    res = use_case.execute(
        LocalLoginInputDTO(email="  MARIA@Estudo.COM ", password="SenhaCorreta123")
    )

    assert res.user_id == existing.id
    assert res.email == "maria@estudo.com"
    assert res.name == "Maria"
    assert res.is_new_user is False
    assert res.session_token == f"fake-session-{existing.id}"


@pytest.mark.unit
@pytest.mark.security
def test_authenticate_local_user_anti_enumeration_uniform_error() -> None:
    """Valida resposta uniforme para e-mail inexistente, conta sem hash e senha incorreta.

    Vulnerabilidade prevenida: Enumeração de usuários por mensagens de erro distintas ou discrepância de fluxo (CWE-204).
    Garantia de segurança: Todos os cenários de falha de login disparam UnauthorizedError com a mesma mensagem genérica.
    """
    user_repo = InMemoryUserRepository()
    hasher = FakePasswordHasher()
    token_service = FakeSessionTokenService()

    user_with_hash = User(
        google_sub="local:comsenha@teste.com",
        email="comsenha@teste.com",
        name="Com Senha",
        password_hash=hasher.hash_password("SenhaCorreta123"),
    )
    user_without_hash = User(
        google_sub="legacy:semhash",
        email="semhash@teste.com",
        name="Sem Hash",
        password_hash=None,
    )
    user_repo.save(user_with_hash)
    user_repo.save(user_without_hash)

    use_case = AuthenticateLocalUserUseCase(
        user_repo=user_repo,
        password_hasher=hasher,
        token_service=token_service,
    )

    scenarios = [
        LocalLoginInputDTO(email="naoexiste@teste.com", password="QualquerSenha123"),
        LocalLoginInputDTO(email="semhash@teste.com", password="QualquerSenha123"),
        LocalLoginInputDTO(email="comsenha@teste.com", password="SenhaErrada123"),
    ]
    messages: list[str] = []
    for dto in scenarios:
        with pytest.raises(UnauthorizedError) as exc_info:
            use_case.execute(dto)
        messages.append(str(exc_info.value))

    assert len(set(messages)) == 1
    assert messages[0] == "E-mail ou senha inválidos."


@pytest.mark.unit
def test_authenticate_demo_user_creates_and_reuses_demo_account() -> None:
    """Valida criação na primeira chamada e reutilização subsequente do usuário Demo offline."""
    user_repo = InMemoryUserRepository()
    hasher = FakePasswordHasher()
    token_service = FakeSessionTokenService()

    use_case = AuthenticateDemoUserUseCase(
        user_repo=user_repo,
        password_hasher=hasher,
        token_service=token_service,
    )

    # Primeiro acesso: cria usuário demo
    first = use_case.execute()
    assert first.is_new_user is True
    assert first.email == DEMO_EMAIL
    assert first.name == DEMO_NAME
    assert first.session_token == f"fake-session-{first.user_id}"

    saved_demo = user_repo.get_by_google_sub(DEMO_GOOGLE_SUB)
    assert saved_demo is not None
    assert saved_demo.password_hash is not None

    # Segundo acesso (encontrado por e-mail): reutiliza sem recriar
    second = use_case.execute()
    assert second.is_new_user is False
    assert second.user_id == first.user_id


@pytest.mark.unit
def test_authenticate_demo_user_fallback_lookup_by_google_sub() -> None:
    """Valida fallback de busca por DEMO_GOOGLE_SUB quando e-mail do usuário demo foi alterado."""
    user_repo = InMemoryUserRepository()
    demo_existing = User(
        google_sub=DEMO_GOOGLE_SUB,
        email="alias-demo@studyreviewer.local",
        name=DEMO_NAME,
        password_hash="hashed::random",
    )
    user_repo.save(demo_existing)

    use_case = AuthenticateDemoUserUseCase(
        user_repo=user_repo,
        password_hasher=FakePasswordHasher(),
        token_service=FakeSessionTokenService(),
    )
    res = use_case.execute()

    assert res.is_new_user is False
    assert res.user_id == demo_existing.id


@pytest.mark.unit
def test_get_current_user_success() -> None:
    """Valida resolução da entidade do usuário logado a partir de token válido."""
    user_repo = InMemoryUserRepository()
    token_service = FakeSessionTokenService()

    user = User(google_sub="local:user@teste.com", email="user@teste.com", name="User Teste")
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

    with pytest.raises(ResourceOwnershipError, match="Você não tem permissão para adicionar temas"):
        use_case.execute(
            CreateTopicDTO(subject_id=subject.id, name="Revolução Francesa"),
            user_id=other_user_id,
        )

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

    create_uc.execute(CreateSubjectDTO(name="Matéria A Privada", is_public=False), owner_id=user_a)
    create_uc.execute(CreateSubjectDTO(name="Matéria A Pública", is_public=True), owner_id=user_a)
    create_uc.execute(CreateSubjectDTO(name="Matéria B Privada", is_public=False), owner_id=user_b)

    subs_a = list_uc.execute(user_id=user_a)
    assert len(subs_a) == 2
    assert all(s.is_owner for s in subs_a)

    subs_b = list_uc.execute(user_id=user_b)
    assert len(subs_b) == 2
    names_b = {s.name for s in subs_b}
    assert "Matéria B Privada" in names_b
    assert "Matéria A Pública" in names_b
    public_from_a = next(s for s in subs_b if s.name == "Matéria A Pública")
    assert public_from_a.is_owner is False


@pytest.mark.unit
def test_delete_account_use_case_success() -> None:
    """Valida a exclusão bem-sucedida de usuário existente via DeleteAccountUseCase."""
    user_repo = InMemoryUserRepository()
    user = User(
        google_sub="local:delete_me@teste.com",
        email="delete_me@teste.com",
        name="Usuário A Ser Excluído",
    )
    user_repo.save(user)
    assert user_repo.get_by_id(user.id) is not None

    use_case = DeleteAccountUseCase(user_repo=user_repo)
    use_case.execute(user.id)

    assert user_repo.get_by_id(user.id) is None


@pytest.mark.unit
def test_delete_account_use_case_not_found_raises_exception() -> None:
    """Valida que tentar excluir um usuário inexistente levanta EntityNotFoundError."""
    user_repo = InMemoryUserRepository()
    use_case = DeleteAccountUseCase(user_repo=user_repo)
    non_existent_id = uuid4()

    with pytest.raises(EntityNotFoundError, match="Usuário não encontrado."):
        use_case.execute(non_existent_id)


@pytest.mark.unit
@pytest.mark.security
def test_delete_account_security_entity_validation_and_tampering() -> None:
    """Vulnerabilidade prevenida: Impede exclusão indevida ou adulteração de contas inexistentes.

    Garantia de segurança: Assegura que o caso de uso valide estritamente a existência
    prévia da entidade antes de acionar a porta de exclusão e isole o impacto de chave
    primária sob LGPD Art. 18.
    """
    user_repo = InMemoryUserRepository()
    target_user = User(
        google_sub="local:vitima@seguranca.com",
        email="vitima@seguranca.com",
        name="Conta Alvo",
    )
    user_repo.save(target_user)

    token_service = FakeSessionTokenService()
    use_case = DeleteAccountUseCase(user_repo=user_repo, session_token_service=token_service)

    tampered_id = uuid4()
    with pytest.raises(EntityNotFoundError):
        use_case.execute(tampered_id)

    assert user_repo.get_by_id(target_user.id) is not None

    use_case.execute(target_user.id)
    assert user_repo.get_by_id(target_user.id) is None
