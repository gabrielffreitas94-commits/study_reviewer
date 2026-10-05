"""Casos de uso para Autenticação, Usuários e Gestão de Sessões (Clean Architecture - Camada 2)."""

from uuid import UUID

from src.application.dto.auth_dto import (
    AuthResultDTO,
    GoogleAuthInputDTO,
    GoogleUserInfoDTO,
    UserDTO,
)
from src.application.dto.subject_dto import SubjectDTO
from src.application.ports.auth import IGoogleAuthClient, ISessionTokenService
from src.application.ports.repositories import ISubjectRepository, IUserRepository
from src.domain.entities import User
from src.domain.exceptions import (
    DomainValidationError,
    EntityNotFoundError,
    ResourceOwnershipError,
    UnauthorizedError,
)


class AuthenticateWithGoogleUseCase:
    """Caso de uso para autenticação via Google OAuth2 / OIDC com JIT Provisioning."""

    def __init__(
        self,
        google_client: IGoogleAuthClient,
        user_repo: IUserRepository,
        token_service: ISessionTokenService,
    ) -> None:
        self._google_client = google_client
        self._user_repo = user_repo
        self._token_service = token_service

    def execute(self, input_dto: GoogleAuthInputDTO) -> AuthResultDTO:
        user_info: GoogleUserInfoDTO
        if input_dto.code:
            user_info = self._google_client.exchange_code_for_user_info(
                code=input_dto.code,
                redirect_uri=input_dto.redirect_uri,
            )
        elif input_dto.id_token:
            user_info = self._google_client.verify_id_token(input_dto.id_token)
        else:
            raise DomainValidationError(
                "Código ou ID Token do Google é obrigatório para autenticação."
            )

        # Localiza por google_sub ou email
        user = self._user_repo.get_by_google_sub(user_info.sub)
        is_new_user = False

        if user is None:
            # Tenta vincular por e-mail caso exista
            user = self._user_repo.get_by_email(user_info.email)

        if user is None:
            # JIT Provisioning de novo usuário
            user = User(
                google_sub=user_info.sub,
                email=user_info.email,
                name=user_info.name,
                avatar_url=user_info.avatar_url,
            )
            self._user_repo.save(user)
            is_new_user = True
        else:
            # Sincronização de perfil para usuário existente
            changed = False
            if user.google_sub != user_info.sub:
                user.google_sub = user_info.sub
                changed = True
            if user_info.name and user.name != user_info.name:
                user.name = user_info.name.strip()
                changed = True
            if user_info.avatar_url is not None and user.avatar_url != user_info.avatar_url:
                user.avatar_url = user_info.avatar_url.strip() or None
                changed = True
            if changed:
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
