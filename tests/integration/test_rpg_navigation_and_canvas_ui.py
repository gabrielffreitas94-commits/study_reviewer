"""Testes de integração para a Navegação RPG Grimoire, Códice de Habilidades,
HUD da Forja e Canvas de Medalhões."""

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
    SqlAlchemyStudyMapRepository,
    SqlAlchemyUserRepository,
)
from src.domain.entities import StudyMap, User
from src.infrastructure.database import Base, get_db
from src.infrastructure.security.dependencies import get_current_user
from src.infrastructure.web.app import app


@pytest.fixture
def test_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-rpg-navigator",
        email="rpg.navigator@test.com",
        name="Mestre da Forja",
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
def test_rpg_grimoire_topbar_and_navigation(authenticated_client: TestClient) -> None:
    """Verifica se /study-maps renderiza as 3 abas RPG, fontes Cinzel/Cormorant e exclui itens legados."""
    res = authenticated_client.get("/study-maps")
    assert res.status_code == 200

    # Fontes do Grimório
    assert "Cinzel" in res.text
    assert "Cormorant+Garamond" in res.text or "Cormorant Garamond" in res.text

    # 3 Abas RPG
    assert "Códice de Habilidades" in res.text
    assert "Provações Diárias" in res.text
    assert "Crônicas & Atributos" in res.text

    # Remoção do legado corporativo da barra de navegação e páginas
    assert 'id="cadastros-menu-btn"' not in res.text
    assert "Cadastros" not in res.text
    assert "Matérias e Temas" not in res.text
    assert "Vincular da Biblioteca" not in res.text
    assert "Sub-mapa" not in res.text


@pytest.mark.integration
def test_rpg_forge_canvas_hud_and_no_legacy_drawers(
    authenticated_client: TestClient, db_session: Session, test_user: User
) -> None:
    """Verifica se /study-maps/{map_id}/canvas renderiza a HUD da Forja sem drawer ou modal de vincular."""
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    study_map = StudyMap(
        owner_id=test_user.id,
        title="Trilha do Alquimista",
        description="Árvore de Forja Ancestral",
    )
    map_repo.save(study_map)

    res = authenticated_client.get(f"/study-maps/{study_map.id}/canvas")
    assert res.status_code == 200

    # HUD RPG
    assert "Modo Jornada" in res.text
    assert "Modo Forja" in res.text
    assert "Tomo de Habilidades" in res.text

    # Remoção do drawer lateral do hub antigo e modal de vinculação
    assert 'id="node-drawer"' not in res.text
    assert 'id="attach-modal"' not in res.text
    assert "Vincular da Biblioteca" not in res.text


def test_study_canvas_js_navigation_and_icon_map() -> None:
    """Verifica se study_canvas.js navega para a página do nó e possui todos os ícones RPG."""
    js_path = (
        Path(__file__).parents[2] / "src" / "adapters" / "web" / "static" / "js" / "study_canvas.js"
    )
    assert js_path.exists(), "study_canvas.js não encontrado"
    content = js_path.read_text(encoding="utf-8")

    # Navegação em Modo Jornada/Estudo para /study-maps/.../nodes/...
    assert "/study-maps/" in content
    assert "/nodes/" in content
    assert (
        "`/study-maps/${state.mapId}/nodes/${node.id}`" in content
        or "`/study-maps/${state.mapId}/nodes/${nodeId}`" in content
        or "/study-maps/" in content
        and "/nodes/" in content
    )

    # Todos os ícones obrigatórios em ICON_MAP
    required_icons = [
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
    for icon in required_icons:
        assert f"'{icon}'" in content or f'"{icon}"' in content or f"{icon}:" in content, (
            f"Ícone ausente no ICON_MAP: {icon}"
        )
