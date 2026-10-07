import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.adapters.persistence.repositories import SqlAlchemyUserRepository
from src.application.dto.auth_dto import GoogleAuthInputDTO, UserDTO
from src.application.ports.auth import IGoogleAuthClient, ISessionTokenService
from src.application.use_cases.auth_use_cases import (
    AuthenticateWithGoogleUseCase,
    DeleteAccountUseCase,
)
from src.domain.entities import User
from src.domain.exceptions import DomainException, EntityNotFoundError, UnauthorizedError
from src.infrastructure.config import settings
from src.infrastructure.database import get_db
from src.infrastructure.security.dependencies import (
    get_current_user,
    get_google_client,
    get_session_service,
)

logger = logging.getLogger("study_reviewer.auth_api")

api_auth_router = APIRouter(prefix="/api/v1/auth", tags=["API Auth"])


class GoogleAuthApiRequest(BaseModel):
    code: str | None = Field(default=None, description="Authorization code do Google OAuth2")
    id_token: str | None = Field(default=None, description="ID Token JWT emitido pelo Google")
    redirect_uri: str = Field(
        default="", description="URI de redirecionamento usada no fluxo de autorização"
    )


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
    user: UserDTO


class MessageResponse(BaseModel):
    message: str


@api_auth_router.post("/google", response_model=AuthTokenResponse, status_code=status.HTTP_200_OK)
def authenticate_google_api(
    payload: GoogleAuthApiRequest,
    db: Session = Depends(get_db),
    google_client: IGoogleAuthClient = Depends(get_google_client),
    session_service: ISessionTokenService = Depends(get_session_service),
) -> AuthTokenResponse:
    """Autentica cliente mobile/externo via Google OAuth2/OIDC e emite Bearer Token."""
    user_repo = SqlAlchemyUserRepository(db)
    use_case = AuthenticateWithGoogleUseCase(
        google_client=google_client,
        user_repo=user_repo,
        token_service=session_service,
    )

    try:
        result = use_case.execute(
            GoogleAuthInputDTO(
                code=payload.code,
                id_token=payload.id_token,
                redirect_uri=payload.redirect_uri or settings.GOOGLE_REDIRECT_URI,
            )
        )
        user = user_repo.get_by_id(result.user_id)
        if user is None:
            raise UnauthorizedError("Usuário não encontrado após provisionamento.")

        return AuthTokenResponse(
            access_token=result.session_token,
            token_type="bearer",  # noqa: S106
            user=UserDTO(
                id=user.id,
                email=user.email,
                name=user.name,
                avatar_url=user.avatar_url,
                created_at=user.created_at,
            ),
        )
    except UnauthorizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except DomainException as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Falha na autenticação com Google: {exc}",
        ) from exc


@api_auth_router.get("/me", response_model=UserDTO)
def get_me_api(
    current_user: User = Depends(get_current_user),
) -> UserDTO:
    """Retorna os dados do usuário autenticado a partir do Bearer Token."""
    return UserDTO(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
        created_at=current_user.created_at,
    )


@api_auth_router.delete("/account", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def delete_account_api(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Exclui a conta e dados pessoais do usuário autenticado (LGPD Art. 18 / Google Play).

    Segurança: Identidade extraída exclusivamente de current_user.id (anti-IDOR).
    """
    user_repo = SqlAlchemyUserRepository(db)
    use_case = DeleteAccountUseCase(user_repo=user_repo)
    try:
        use_case.execute(user_id=current_user.id)
        db.commit()
        logger.info(
            "Conta de usuário excluída via API REST com sucesso",
            extra={
                "event": "api_account_deleted",
                "user_id": str(current_user.id),
            },
        )
    except EntityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return MessageResponse(message="Conta e dados pessoais excluídos com sucesso.")


@api_auth_router.post("/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def logout_api(
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Efetua logout formal do usuário autenticado."""
    return MessageResponse(message="Logout efetuado com sucesso.")
