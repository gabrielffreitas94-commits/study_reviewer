"""Testes de integração para os controladores Web da Árvore de Estudos RPG (Camada 3)."""

from collections.abc import Generator
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.adapters.persistence.repositories import (
    SqlAlchemyStudyMapRepository,
    SqlAlchemyStudyNodeRepository,
    SqlAlchemyUserRepository,
)
from src.domain.entities import StudyMap, StudyNode, User
from src.infrastructure.database import Base, get_db
from src.infrastructure.security.dependencies import get_current_user
from src.infrastructure.web.app import app


@pytest.fixture
def test_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-tree-web-1",
        email="tree.web@studyreviewer.local",
        name="Tree Web Hero",
    )


@pytest.fixture
def other_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-tree-web-2",
        email="other.web@studyreviewer.local",
        name="Other Hero",
    )


@pytest.fixture
def db_engine() -> Generator[Any]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Any) -> Generator[Session]:
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session, test_user: User) -> Generator[TestClient]:
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


class TestStudyTreeWebControllers:
    def test_list_study_maps_page(
        self, client: TestClient, db_session: Session, test_user: User
    ) -> None:
        map_repo = SqlAlchemyStudyMapRepository(db_session)
        node_repo = SqlAlchemyStudyNodeRepository(db_session)

        # Criar mapa raiz
        root_map = StudyMap(
            owner_id=test_user.id,
            title="Campanha de Python",
            description="Domínio completo do ecossistema",
            is_public=False,
        )
        map_repo.save(root_map)

        node = StudyNode(
            map_id=root_map.id,
            title="Sintaxe Básica",
            pos_x=100.0,
            pos_y=150.0,
        )
        node_repo.save(node)

        # Mapa pertencente a outro usuário não deve listar aqui
        other_map = StudyMap(
            owner_id=uuid4(),
            title="Outro Mapa Privado",
        )
        map_repo.save(other_map)

        response = client.get("/study-maps")
        assert response.status_code == 200
        assert "Campanha de Python" in response.text
        assert "Domínio completo do ecossistema" in response.text
        assert "Outro Mapa Privado" not in response.text

    def test_canvas_page_for_owner(
        self, client: TestClient, db_session: Session, test_user: User
    ) -> None:
        map_repo = SqlAlchemyStudyMapRepository(db_session)
        study_map = StudyMap(
            owner_id=test_user.id,
            title="Árvore de Engenharia de Dados",
            description="Trilha de aprendizado",
        )
        map_repo.save(study_map)

        response = client.get(f"/study-maps/{study_map.id}/canvas")
        assert response.status_code == 200
        assert "Árvore de Engenharia de Dados" in response.text
        assert "canvas-viewport" in response.text
        assert "edges-group" in response.text
        assert "nodes-layer" in response.text

    def test_canvas_page_nonexistent_map_returns_404(self, client: TestClient) -> None:
        random_id = uuid4()
        response = client.get(f"/study-maps/{random_id}/canvas")
        assert response.status_code == 404

    def test_canvas_page_unauthorized_private_map_returns_403(
        self, client: TestClient, db_session: Session, other_user: User
    ) -> None:
        user_repo = SqlAlchemyUserRepository(db_session)
        user_repo.save(other_user)

        map_repo = SqlAlchemyStudyMapRepository(db_session)
        private_map = StudyMap(
            owner_id=other_user.id,
            title="Segredos do Mago",
            is_public=False,
        )
        map_repo.save(private_map)

        response = client.get(f"/study-maps/{private_map.id}/canvas")
        assert response.status_code == 403

    def test_canvas_page_public_map_accessible_by_other_user(
        self, client: TestClient, db_session: Session, other_user: User
    ) -> None:
        user_repo = SqlAlchemyUserRepository(db_session)
        user_repo.save(other_user)

        map_repo = SqlAlchemyStudyMapRepository(db_session)
        public_map = StudyMap(
            owner_id=other_user.id,
            title="Trilha Pública de Estatística",
            is_public=True,
        )
        map_repo.save(public_map)

        response = client.get(f"/study-maps/{public_map.id}/canvas")
        assert response.status_code == 200
        assert "Trilha Pública de Estatística" in response.text

    def test_canvas_page_submap_breadcrumb(
        self, client: TestClient, db_session: Session, test_user: User
    ) -> None:
        map_repo = SqlAlchemyStudyMapRepository(db_session)
        node_repo = SqlAlchemyStudyNodeRepository(db_session)

        root_map = StudyMap(
            owner_id=test_user.id,
            title="Mapa Principal",
        )
        map_repo.save(root_map)

        parent_node = StudyNode(
            map_id=root_map.id,
            title="Nó Macro de Redes",
            pos_x=200.0,
            pos_y=200.0,
        )
        node_repo.save(parent_node)

        submap = StudyMap(
            owner_id=test_user.id,
            title="Submapa Detalhado de Roteamento",
            parent_node_id=parent_node.id,
        )
        map_repo.save(submap)

        response = client.get(f"/study-maps/{submap.id}/canvas")
        assert response.status_code == 200
        assert "Submapa Detalhado de Roteamento" in response.text
        assert "Nó Macro de Redes" in response.text
