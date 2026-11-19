import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.adapters.persistence.repositories import SqlAlchemyUserRepository
from src.application.dto.auth_dto import (
    AuthResultDTO,
    LocalLoginInputDTO,
    LocalRegisterInputDTO,
    UserDTO,
)
from src.application.ports.auth import IPasswordHasher, ISessionTokenService
from src.application.use_cases.auth_use_cases import (
    AuthenticateDemoUserUseCase,
    AuthenticateLocalUserUseCase,
    DeleteAccountUseCase,
    RegisterLocalUserUseCase,
)
from src.domain.entities import User
from src.domain.exceptions import (
    DomainException,
    DuplicateEntityError,
    EntityNotFoundError,
    UnauthorizedError,
)
from src.infrastructure.database import get_db
from src.infrastructure.security.dependencies import (
    get_current_user,
    get_password_hasher,
    get_session_service,
)

logger = logging.getLogger("study_reviewer.auth_api")

api_auth_router = APIRouter(prefix="/api/v1/auth", tags=["API Auth"])


class LocalRegisterApiRequest(BaseModel):
    email: str = Field(..., description="E-mail da nova conta local")
    name: str = Field(..., description="Nome de exibição do usuário")
    password: str = Field(..., description="Senha de acesso (8 a 128 caracteres)")


class LocalLoginApiRequest(BaseModel):
    email: str = Field(..., description="E-mail cadastrado")
    password: str = Field(..., description="Senha de acesso")


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
    user: UserDTO


class MessageResponse(BaseModel):
    message: str


def _build_auth_token_response(
    result: AuthResultDTO,
    user_repo: SqlAlchemyUserRepository,
) -> AuthTokenResponse:
    """Constrói a resposta padronizada com Bearer Token e dados públicos do usuário."""
    user = user_repo.get_by_id(result.user_id)
    created_at = user.created_at if user is not None else date.today()
    return AuthTokenResponse(
        access_token=result.session_token,
        token_type="bearer",  # noqa: S106
        user=UserDTO(
            id=result.user_id,
            email=result.email,
            name=result.name,
            avatar_url=result.avatar_url,
            created_at=created_at,
        ),
    )


@api_auth_router.post(
    "/register",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_local_api(
    payload: LocalRegisterApiRequest,
    db: Session = Depends(get_db),
    password_hasher: IPasswordHasher = Depends(get_password_hasher),
    session_service: ISessionTokenService = Depends(get_session_service),
) -> AuthTokenResponse:
    """Registra nova conta local e retorna Bearer Token de sessão."""
    user_repo = SqlAlchemyUserRepository(db)
    use_case = RegisterLocalUserUseCase(
        user_repo=user_repo,
        password_hasher=password_hasher,
        token_service=session_service,
    )
    try:
        result = use_case.execute(
            LocalRegisterInputDTO(
                email=payload.email,
                name=payload.name,
                password=payload.password,
            )
        )
        return _build_auth_token_response(result, user_repo)
    except DuplicateEntityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except DomainException as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@api_auth_router.post(
    "/login",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_200_OK,
)
def login_local_api(
    payload: LocalLoginApiRequest,
    db: Session = Depends(get_db),
    password_hasher: IPasswordHasher = Depends(get_password_hasher),
    session_service: ISessionTokenService = Depends(get_session_service),
) -> AuthTokenResponse:
    """Autentica usuário local via e-mail e senha e retorna Bearer Token."""
    user_repo = SqlAlchemyUserRepository(db)
    use_case = AuthenticateLocalUserUseCase(
        user_repo=user_repo,
        password_hasher=password_hasher,
        token_service=session_service,
    )
    try:
        result = use_case.execute(
            LocalLoginInputDTO(email=payload.email, password=payload.password)
        )
        return _build_auth_token_response(result, user_repo)
    except UnauthorizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@api_auth_router.post(
    "/demo",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_200_OK,
)
def demo_login_api(
    db: Session = Depends(get_db),
    password_hasher: IPasswordHasher = Depends(get_password_hasher),
    session_service: ISessionTokenService = Depends(get_session_service),
) -> AuthTokenResponse:
    """Autentica instantaneamente com o perfil Estudante Demo e retorna Bearer Token."""
    user_repo = SqlAlchemyUserRepository(db)
    use_case = AuthenticateDemoUserUseCase(
        user_repo=user_repo,
        password_hasher=password_hasher,
        token_service=session_service,
    )
    result = use_case.execute()
    return _build_auth_token_response(result, user_repo)


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
