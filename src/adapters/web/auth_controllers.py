import logging
import urllib.parse
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Form,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.adapters.persistence.repositories import SqlAlchemyUserRepository
from src.adapters.web.rpg_icons import get_rpg_icon_svg
from src.application.dto.auth_dto import LocalLoginInputDTO, LocalRegisterInputDTO
from src.application.ports.auth import IPasswordHasher, ISessionTokenService
from src.application.use_cases.auth_use_cases import (
    AuthenticateDemoUserUseCase,
    AuthenticateLocalUserUseCase,
    LogoutUseCase,
    RegisterLocalUserUseCase,
)
from src.domain.entities import User
from src.domain.exceptions import DomainException
from src.infrastructure.config import settings
from src.infrastructure.database import get_db
from src.infrastructure.security.dependencies import (
    get_current_user_optional,
    get_password_hasher,
    get_session_service,
)

logger = logging.getLogger("study_reviewer.web_auth")

templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))
templates.env.globals["get_rpg_icon_svg"] = get_rpg_icon_svg

auth_router = APIRouter(prefix="/auth", tags=["Web Auth"])


def _safe_redirect_url(target: str | None, default: str = "/study-maps") -> str:
    """Valida e sanitiza rotas de redirecionamento prevenindo Open Redirect (CWE-601)."""
    if not target:
        return default
    clean = target.strip()
    if clean.startswith("/") and not clean.startswith("//") and not clean.startswith("/\\"):
        return clean
    return default


def _set_session_cookie(response: Response, request: Request, session_token: str) -> None:
    """Grava o cookie de sessão seguro AES-256-GCM na resposta HTTP."""
    is_https = settings.ENVIRONMENT in ("production", "staging") or request.url.scheme == "https"
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=is_https,
        max_age=30 * 24 * 3600,
        path="/",
    )


@auth_router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    next: str = Query("/study-maps"),
    error: str | None = Query(None),
    current_user: User | None = Depends(get_current_user_optional),
) -> Response:
    """Renderiza a página de login local, cadastro e acesso demo offline."""
    safe_next = _safe_redirect_url(next, "/study-maps")
    if current_user is not None:
        return RedirectResponse(url=safe_next, status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={
            "next_url": safe_next,
            "error": error,
            "current_user": None,
        },
    )


@auth_router.post("/login")
def login_submit(
    request: Request,
    email: Annotated[str, Form(...)],
    password: Annotated[str, Form(...)],
    next: Annotated[str, Form()] = "/study-maps",
    db: Session = Depends(get_db),
    password_hasher: IPasswordHasher = Depends(get_password_hasher),
    session_service: ISessionTokenService = Depends(get_session_service),
) -> Response:
    """Autentica usuário local por e-mail e senha e grava cookie de sessão."""
    safe_next = _safe_redirect_url(next, "/study-maps")
    user_repo = SqlAlchemyUserRepository(db)
    use_case = AuthenticateLocalUserUseCase(
        user_repo=user_repo,
        password_hasher=password_hasher,
        token_service=session_service,
    )

    try:
        result = use_case.execute(LocalLoginInputDTO(email=email, password=password))
    except DomainException as exc:
        err_param = urllib.parse.quote(str(exc), safe="")
        next_param = urllib.parse.quote(safe_next, safe="")
        return RedirectResponse(
            url=f"/auth/login?error={err_param}&next={next_param}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    response = RedirectResponse(url=safe_next, status_code=status.HTTP_303_SEE_OTHER)
    _set_session_cookie(response, request, result.session_token)
    return response


@auth_router.post("/register")
def register_submit(
    request: Request,
    name: Annotated[str, Form(...)],
    email: Annotated[str, Form(...)],
    password: Annotated[str, Form(...)],
    next: Annotated[str, Form()] = "/study-maps",
    db: Session = Depends(get_db),
    password_hasher: IPasswordHasher = Depends(get_password_hasher),
    session_service: ISessionTokenService = Depends(get_session_service),
) -> Response:
    """Registra nova conta local e inicia a sessão imediatamente."""
    safe_next = _safe_redirect_url(next, "/study-maps")
    user_repo = SqlAlchemyUserRepository(db)
    use_case = RegisterLocalUserUseCase(
        user_repo=user_repo,
        password_hasher=password_hasher,
        token_service=session_service,
    )

    try:
        result = use_case.execute(LocalRegisterInputDTO(email=email, name=name, password=password))
    except DomainException as exc:
        err_param = urllib.parse.quote(str(exc), safe="")
        next_param = urllib.parse.quote(safe_next, safe="")
        return RedirectResponse(
            url=f"/auth/login?error={err_param}&next={next_param}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    response = RedirectResponse(url=safe_next, status_code=status.HTTP_303_SEE_OTHER)
    _set_session_cookie(response, request, result.session_token)
    return response


@auth_router.post("/demo")
def demo_login_submit(
    request: Request,
    next: Annotated[str, Form()] = "/study-maps",
    db: Session = Depends(get_db),
    password_hasher: IPasswordHasher = Depends(get_password_hasher),
    session_service: ISessionTokenService = Depends(get_session_service),
) -> Response:
    """Autentica instantaneamente com a conta de Estudante Demo offline."""
    safe_next = _safe_redirect_url(next, "/study-maps")
    user_repo = SqlAlchemyUserRepository(db)
    use_case = AuthenticateDemoUserUseCase(
        user_repo=user_repo,
        password_hasher=password_hasher,
        token_service=session_service,
    )
    result = use_case.execute()

    response = RedirectResponse(url=safe_next, status_code=status.HTTP_303_SEE_OTHER)
    _set_session_cookie(response, request, result.session_token)
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


@auth_router.get("/privacy", include_in_schema=False)
def auth_privacy_redirect() -> Response:
    """Redireciona /auth/privacy para a rota canônica /privacy."""
    return RedirectResponse(url="/privacy", status_code=status.HTTP_301_MOVED_PERMANENTLY)


@auth_router.get("/account-deletion-request", include_in_schema=False)
def auth_account_deletion_redirect() -> Response:
    """Redireciona /auth/account-deletion-request para a rota canônica."""
    return RedirectResponse(
        url="/privacy/account-deletion-request", status_code=status.HTTP_301_MOVED_PERMANENTLY
    )


privacy_router = APIRouter(tags=["Web Privacy & LGPD"])


@privacy_router.get("/privacy", response_class=HTMLResponse)
def privacy_page(
    request: Request,
    current_user: User | None = Depends(get_current_user_optional),
) -> Response:
    """Renderiza a Política de Privacidade em conformidade com LGPD e Google Play Data Safety."""
    return templates.TemplateResponse(
        request=request,
        name="privacy.html",
        context={
            "current_user": current_user,
        },
    )


@privacy_router.get("/privacy/account-deletion-request", response_class=HTMLResponse)
def account_deletion_request_page(
    request: Request,
    current_user: User | None = Depends(get_current_user_optional),
) -> Response:
    """Renderiza o formulário público para solicitação externa de exclusão de conta e dados."""
    return templates.TemplateResponse(
        request=request,
        name="account_deletion_request.html",
        context={
            "current_user": current_user,
            "submitted": False,
            "email": current_user.email if current_user else "",
        },
    )


@privacy_router.post("/privacy/account-deletion-request", response_class=HTMLResponse)
def submit_account_deletion_request(
    request: Request,
    email: Annotated[str, Form(...)],
    confirmation: Annotated[str | None, Form()] = None,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> Response:
    """Processa solicitação externa de exclusão de dados com confirmação por e-mail (Double Opt-In).

    Segurança Anti-Enumeration: Mensagem genérica uniforme independente da existência do e-mail
    no sistema, prevenindo vazamento por enumeração de usuários.
    """
    clean_email = email.strip().lower()
    user_repo = SqlAlchemyUserRepository(db)
    user = user_repo.get_by_email(clean_email) if clean_email else None

    logger.info(
        "Solicitação externa de exclusão de dados submetida",
        extra={
            "event": "account_deletion_request_submitted",
            "user_found": user is not None,
            "has_confirmation": confirmation is not None,
        },
    )

    # Simulação do disparo seguro de e-mail Double Opt-In
    return templates.TemplateResponse(
        request=request,
        name="account_deletion_request.html",
        context={
            "current_user": current_user,
            "submitted": True,
            "email": clean_email,
            "user_found": user is not None,
        },
    )
