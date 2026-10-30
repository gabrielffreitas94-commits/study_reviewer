"""Testes de integração para a biblioteca de ícones vetoriais RPG (Game-Icons.net).

Valida a existência dos 21 glifos vetoriais, script rpg_icons.js,
inclusão no Canvas e renderização dos medalhões SVG no Grimório do Nó.
"""

from collections.abc import Generator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.adapters.persistence.repositories import (
    SqlAlchemyUserRepository,
)
from src.domain.entities import User
from src.infrastructure.database import Base, get_db
from src.infrastructure.security.dependencies import get_current_user
from src.infrastructure.web.app import app

EXPECTED_21_ICONS = [
    "calculator",
    "trending-up",
    "dice",
    "activity",
    "brain",
    "book",
    "code",
    "cpu",
    "database",
    "globe",
    "layers",
    "shield",
    "terminal",
    "zap",
    "award",
    "compass",
    "feather",
    "flame",
    "key",
    "scroll",
    "sword",
]


@pytest.fixture
def test_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-rpg-icons-tester",
        email="rpg.icons@test.com",
        name="Artífice de Runas",
    )


@pytest.fixture
def db_engine() -> Generator[Any]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Any) -> Generator[Session]:
    testing_session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def authenticated_client(db_session: Session, test_user: User) -> Generator[TestClient]:
    user_repo = SqlAlchemyUserRepository(db_session)
    user_repo.save(test_user)

    def override_get_db() -> Generator[Session]:
        yield db_session

    def override_get_current_user() -> User:
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.mark.integration
def test_rpg_icons_javascript_asset_and_all_21_icons_exist() -> None:
    """Verifica se o asset estático rpg_icons.js existe e define os 21 glifos com viewBox 0 0 512 512."""
    icons_file = Path("src/adapters/web/static/js/rpg_icons.js")
    assert icons_file.exists(), "src/adapters/web/static/js/rpg_icons.js deve existir!"

    content = icons_file.read_text(encoding="utf-8")
    assert "RPG_ICONS" in content
    assert "getRpgIconSvg" in content

    # Garante que cada um dos 21 ícones rúnicos está mapeado
    for icon_name in EXPECTED_21_ICONS:
        assert (
            f'"{icon_name}"' in content or f"'{icon_name}'" in content or f"{icon_name}:" in content
        ), f"Ícone '{icon_name}' não encontrado em rpg_icons.js!"

    assert 'viewBox="0 0 512 512"' in content
    assert "<path" in content


@pytest.mark.integration
def test_canvas_template_includes_rpg_icons_script_and_fantasy_options(
    authenticated_client: TestClient,
) -> None:
    """Verifica se o Canvas carrega rpg_icons.js antes de study_canvas.js e exibe nomes RPG nas opções."""
    map_res = authenticated_client.post(
        "/api/v1/study-maps",
        json={"title": "Tomo de Alquimia", "description": "Transmutação & Runas"},
    )
    assert map_res.status_code == 201
    map_id = map_res.json()["id"]

    canvas_res = authenticated_client.get(f"/study-maps/{map_id}/canvas")
    assert canvas_res.status_code == 200
    html = canvas_res.text

    # Verifica script rpg_icons.js incluído antes de study_canvas.js
    rpg_script_pos = html.find("/static/js/rpg_icons.js")
    canvas_script_pos = html.find("/static/js/study_canvas.js")
    assert rpg_script_pos != -1, "rpg_icons.js não incluído no canvas.html!"
    assert canvas_script_pos != -1, "study_canvas.js não incluído no canvas.html!"
    assert rpg_script_pos < canvas_script_pos, (
        "rpg_icons.js deve ser carregado antes de study_canvas.js!"
    )

    # Verifica nomes RPG de fantasia nas opções do select
    assert "Espada Rúnica" in html
    assert "Pergaminho Selado" in html
    assert "Égide de Cavaleiro" in html
    assert "Dado D20" in html
    assert "Grimório Ancestral" in html
    assert "Ábaco Arcano" in html


@pytest.mark.integration
def test_node_grimoire_page_renders_rpg_svg_icon_instead_of_emoji(
    authenticated_client: TestClient,
) -> None:
    """Verifica se o cabeçalho do Grimório do Nó renderiza SVG vetorial em vez de bare emojis."""
    map_res = authenticated_client.post(
        "/api/v1/study-maps",
        json={"title": "Grimório Místico", "description": "Feitiçaria Pura"},
    )
    map_id = map_res.json()["id"]

    icons_to_test = ["sword", "scroll", "shield", "dice", "calculator"]
    for icon_name in icons_to_test:
        node_res = authenticated_client.post(
            f"/api/v1/study-maps/{map_id}/nodes",
            json={
                "title": f"Habilidade {icon_name}",
                "icon": icon_name,
                "pos_x": 100,
                "pos_y": 100,
            },
        )
        assert node_res.status_code == 201
        node_id = node_res.json()["id"]

        grimoire_res = authenticated_client.get(f"/study-maps/{map_id}/nodes/{node_id}")
        assert grimoire_res.status_code == 200
        page_html = grimoire_res.text

        # Deve conter tag SVG com viewBox padrão do Game-Icons (512x512)
        assert "<svg" in page_html, f"Página do nó {icon_name} não renderizou SVG!"
        assert 'viewBox="0 0 512 512"' in page_html, (
            f"SVG do nó {icon_name} sem viewBox='0 0 512 512'!"
        )


@pytest.mark.integration
def test_node_grimoire_page_renders_fallback_svg_for_unknown_icon(
    authenticated_client: TestClient,
) -> None:
    """Garante fallback gracioso para SVG de scroll/book caso um ícone desconhecido seja fornecido."""
    map_res = authenticated_client.post(
        "/api/v1/study-maps",
        json={"title": "Grimório Desconhecido", "description": "Relíquias Ocultas"},
    )
    map_id = map_res.json()["id"]

    node_res = authenticated_client.post(
        f"/api/v1/study-maps/{map_id}/nodes",
        json={
            "title": "Relíquia Arcaica",
            "icon": "unknown-lost-relic",
            "pos_x": 100,
            "pos_y": 100,
        },
    )
    assert node_res.status_code == 201
    node_id = node_res.json()["id"]

    grimoire_res = authenticated_client.get(f"/study-maps/{map_id}/nodes/{node_id}")
    assert grimoire_res.status_code == 200
    page_html = grimoire_res.text

    assert "<svg" in page_html
    assert 'viewBox="0 0 512 512"' in page_html
