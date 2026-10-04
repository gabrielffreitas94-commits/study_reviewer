"""Controladores de API REST para autenticação via Google OAuth2 / OIDC e perfil (Camada 3)."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.adapters.persistence.repositories import SqlAlchemyUserRepository
from src.application.dto.auth_dto import GoogleAuthInputDTO, UserDTO
from src.application.ports.auth import IGoogleAuthClient, ISessionTokenService
from src.application.use_cases.auth_use_cases import AuthenticateWithGoogleUseCase
from src.domain.entities import User
from src.domain.exceptions import DomainException, UnauthorizedError
from src.infrastructure.config import settings
from src.infrastructure.database import get_db
from src.infrastructure.security.dependencies import (
    get_current_user,
    get_google_client,
    get_session_service,
)

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
