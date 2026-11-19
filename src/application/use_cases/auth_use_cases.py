import logging
import secrets
from uuid import UUID

from src.application.dto.auth_dto import (
    AuthResultDTO,
    LocalLoginInputDTO,
    LocalRegisterInputDTO,
    UserDTO,
)
from src.application.dto.subject_dto import SubjectDTO
from src.application.ports.auth import IPasswordHasher, ISessionTokenService
from src.application.ports.repositories import ISubjectRepository, IUserRepository
from src.domain.entities import User
from src.domain.exceptions import (
    DomainValidationError,
    DuplicateEntityError,
    EntityNotFoundError,
    ResourceOwnershipError,
    UnauthorizedError,
)

logger = logging.getLogger("study_reviewer.auth")

DEMO_EMAIL = "demo@studyreviewer.local"
DEMO_NAME = "Estudante Demo"
DEMO_GOOGLE_SUB = "local:demo@studyreviewer.local"


class RegisterLocalUserUseCase:
    """Caso de uso para cadastro de nova conta local com e-mail e senha."""

    def __init__(
        self,
        user_repo: IUserRepository,
        password_hasher: IPasswordHasher,
        token_service: ISessionTokenService,
    ) -> None:
        self._user_repo = user_repo
        self._password_hasher = password_hasher
        self._token_service = token_service

    def execute(self, input_dto: LocalRegisterInputDTO) -> AuthResultDTO:
        if len(input_dto.password.strip()) < 8 or len(input_dto.password) > 128:
            raise DomainValidationError("A senha deve ter entre 8 e 128 caracteres.")

        clean_email = input_dto.email.strip().lower()
        clean_name = input_dto.name.strip()

        if self._user_repo.get_by_email(clean_email) is not None:
            raise DuplicateEntityError("Já existe uma conta cadastrada com este e-mail.")

        hashed_password = self._password_hasher.hash_password(input_dto.password)
        user = User(
            google_sub=f"local:{clean_email}",
            email=clean_email,
            name=clean_name,
            password_hash=hashed_password,
        )
        self._user_repo.save(user)

        session_token = self._token_service.create_session_token(
            user_id=user.id,
            email=user.email,
        )

        return AuthResultDTO(
            user_id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            session_token=session_token,
            is_new_user=True,
        )


class AuthenticateLocalUserUseCase:
    """Caso de uso para autenticação local com e-mail e senha."""

    def __init__(
        self,
        user_repo: IUserRepository,
        password_hasher: IPasswordHasher,
        token_service: ISessionTokenService,
    ) -> None:
        self._user_repo = user_repo
        self._password_hasher = password_hasher
        self._token_service = token_service

    def execute(self, input_dto: LocalLoginInputDTO) -> AuthResultDTO:
        clean_email = input_dto.email.strip().lower()
        user = self._user_repo.get_by_email(clean_email)

        if (
            user is None
            or not user.password_hash
            or not self._password_hasher.verify_password(input_dto.password, user.password_hash)
        ):
            raise UnauthorizedError("E-mail ou senha inválidos.")

        session_token = self._token_service.create_session_token(
            user_id=user.id,
            email=user.email,
        )

        return AuthResultDTO(
            user_id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            session_token=session_token,
            is_new_user=False,
        )


class AuthenticateDemoUserUseCase:
    """Caso de uso para acesso instantâneo offline como Estudante Demo."""

    DEMO_EMAIL = DEMO_EMAIL
    DEMO_NAME = DEMO_NAME
    DEMO_GOOGLE_SUB = DEMO_GOOGLE_SUB

    def __init__(
        self,
        user_repo: IUserRepository,
        password_hasher: IPasswordHasher,
        token_service: ISessionTokenService,
    ) -> None:
        self._user_repo = user_repo
        self._password_hasher = password_hasher
        self._token_service = token_service

    def execute(self) -> AuthResultDTO:
        user = self._user_repo.get_by_email(self.DEMO_EMAIL)
        if user is None:
            user = self._user_repo.get_by_google_sub(self.DEMO_GOOGLE_SUB)

        is_new_user = False
        if user is None:
            hashed_password = self._password_hasher.hash_password(secrets.token_urlsafe(24))
            user = User(
                google_sub=self.DEMO_GOOGLE_SUB,
                email=self.DEMO_EMAIL,
                name=self.DEMO_NAME,
                password_hash=hashed_password,
            )
            self._user_repo.save(user)
            is_new_user = True

        session_token = self._token_service.create_session_token(
            user_id=user.id,
            email=user.email,
        )

        return AuthResultDTO(
            user_id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            session_token=session_token,
            is_new_user=is_new_user,
        )


class GetCurrentUserUseCase:
    """Caso de uso para resolução do usuário ativo a partir do token de sessão."""

    def __init__(
        self,
        token_service: ISessionTokenService,
        user_repo: IUserRepository,
    ) -> None:
        self._token_service = token_service
        self._user_repo = user_repo

    def execute(self, token: str) -> UserDTO:
        payload = self._token_service.verify_session_token(token)
        if payload is None:
            raise UnauthorizedError("Sessão inválida ou expirada.")

        user = self._user_repo.get_by_id(payload.user_id)
        if user is None:
            raise UnauthorizedError("Usuário da sessão não encontrado no sistema.")

        return UserDTO(
            id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            created_at=user.created_at,
        )


class LogoutUseCase:
    """Caso de uso para invalidação e encerramento de sessão."""

    def __init__(self, token_service: ISessionTokenService) -> None:
        self._token_service = token_service

    def execute(self, token: str) -> None:
        # Em tokens stateless AES-256-GCM, o logout primário consiste na
        # exclusão do cookie de sessão no cliente.
        # Hook para eventual lista de revogação imediata
        pass


class DeleteAccountUseCase:
    """Caso de uso para exclusão de conta e dados pessoais (LGPD Art. 18 / Google Play Data Safety).

    Valida a existência do usuário e comanda a exclusão física da conta no repositório.
    Como o banco está configurado com ON DELETE SET NULL em review_audit_logs e study_events
    e CASCADE em subjects e user_question_progress, a exclusão remove integralmente os dados
    pessoais e cadastros mantendo os registros históricos anonimizados para estatísticas
    agregadas sob o Art. 16, IV da LGPD.
    """

    def __init__(
        self,
        user_repo: IUserRepository,
        session_token_service: ISessionTokenService | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._session_token_service = session_token_service

    def execute(self, user_id: UUID) -> None:
        user = self._user_repo.get_by_id(user_id)
        if user is None:
            raise EntityNotFoundError("Usuário não encontrado.")

        self._user_repo.delete(user_id)
        logger.info(
            "Conta de usuário excluída com sucesso",
            extra={
                "event": "account_deleted",
                "user_id": str(user_id),
            },
        )


class ToggleSubjectPublicUseCase:
    """Caso de uso para o proprietário alternar a visibilidade pública de sua matéria."""

    def __init__(self, subject_repo: ISubjectRepository) -> None:
        self._subject_repo = subject_repo

    def execute(self, user_id: UUID, subject_id: UUID, is_public: bool) -> SubjectDTO:
        subject = self._subject_repo.get_by_id(subject_id)
        if subject is None:
            raise EntityNotFoundError("Matéria não encontrada.")

        if not subject.can_be_edited_by(user_id):
            raise ResourceOwnershipError("Você não tem permissão para alterar esta matéria.")

        subject.is_public = is_public
        self._subject_repo.save(subject)

        return SubjectDTO(
            id=subject.id,
            name=subject.name,
            owner_id=subject.owner_id,
            is_public=subject.is_public,
            is_owner=True,
            created_at=subject.created_at,
        )
