"""Controlador Web para autenticação via Google OAuth2 / OIDC (Camada 3 - Adaptadores)."""

import urllib.parse
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.adapters.persistence.repositories import SqlAlchemyUserRepository
from src.application.dto.auth_dto import GoogleAuthInputDTO
from src.application.ports.auth import IGoogleAuthClient, ISessionTokenService
from src.application.use_cases.auth_use_cases import (
    AuthenticateWithGoogleUseCase,
    LogoutUseCase,
)
from src.domain.entities import User
from src.infrastructure.config import settings
from src.infrastructure.database import get_db
from src.infrastructure.security.dependencies import (
    get_current_user_optional,
    get_google_client,
    get_session_service,
)

templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

auth_router = APIRouter(prefix="/auth", tags=["Web Auth"])


@auth_router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    next: str = Query("/study"),
    error: str | None = Query(None),
    current_user: User | None = Depends(get_current_user_optional),
) -> Response:
    """Renderiza a página de login com botão Google e tratamento de redirecionamento."""
    if current_user is not None:
        return RedirectResponse(url=next or "/study", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={
            "next_url": next,
            "error": error,
            "current_user": None,
        },
    )


@auth_router.get("/google")
def google_login_redirect(
    request: Request,
    next: str = Query("/study"),
    google_client: IGoogleAuthClient = Depends(get_google_client),
    session_service: ISessionTokenService = Depends(get_session_service),
) -> Response:
    """Gera state CSRF criptografado e redireciona o usuário para o Google Consent."""
    # Cria o state contendo next_url criptografado
    state = getattr(session_service, "create_oauth_state", lambda n: "state")(next)

    redirect_uri = settings.GOOGLE_REDIRECT_URI or str(request.url_for("google_oauth_callback"))
    auth_url = google_client.get_authorization_url(state=state, redirect_uri=redirect_uri)

    response = RedirectResponse(url=auth_url, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        samesite="lax",
        secure=(settings.ENVIRONMENT == "production"),
        max_age=600,
        path="/",
    )
    return response


@auth_router.get("/callback", name="google_oauth_callback")
def google_oauth_callback(
    request: Request,
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
    google_client: IGoogleAuthClient = Depends(get_google_client),
    session_service: ISessionTokenService = Depends(get_session_service),
) -> Response:
    """Processa o retorno do Google, valida state CSRF, autentica/provisiona e grava cookie."""
    if error or not code:
        err_msg = error or "Código de autorização não fornecido pelo Google."
        return RedirectResponse(
            url=f"/auth/login?error={urllib.parse.quote(err_msg)}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Validação do state CSRF
    expected_state = request.cookies.get("oauth_state")
    clean_state = (state or "").strip().strip('"')
    clean_expected = (expected_state or "").strip().strip('"')
    if not clean_state or not clean_expected or clean_state != clean_expected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Parâmetro state de segurança inválido ou divergente (possível tentativa de CSRF)."
            ),
        )

    # Recupera rota de destino original a partir do state
    next_url = (
        getattr(session_service, "verify_oauth_state", lambda s: "/study")(clean_state) or "/study"
    )

    redirect_uri = settings.GOOGLE_REDIRECT_URI or str(request.url_for("google_oauth_callback"))

    try:
        user_repo = SqlAlchemyUserRepository(db)
        use_case = AuthenticateWithGoogleUseCase(
            google_client=google_client,
            user_repo=user_repo,
            token_service=session_service,
        )
        result = use_case.execute(GoogleAuthInputDTO(code=code, redirect_uri=redirect_uri))
    except Exception as exc:
        return RedirectResponse(
            url=f"/auth/login?error={urllib.parse.quote(str(exc))}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    response = RedirectResponse(url=next_url, status_code=status.HTTP_303_SEE_OTHER)
    # Grava cookie de sessão seguro com AES-256-GCM
    response.set_cookie(
        key="session_token",
        value=result.session_token,
        httponly=True,
        samesite="lax",
        secure=(settings.ENVIRONMENT == "production"),
        max_age=30 * 24 * 3600,  # 30 dias
        path="/",
    )
    # Remove cookie temporário de state
    response.delete_cookie(key="oauth_state", path="/")
    return response


@auth_router.post("/logout")
def logout(
    request: Request,
    session_service: ISessionTokenService = Depends(get_session_service),
) -> Response:
    """Encerra a sessão do usuário e remove o cookie de autenticação."""
    token = request.cookies.get("session_token")
    if token:
        LogoutUseCase(session_service).execute(token)

    response = RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="session_token", path="/")
    return response
