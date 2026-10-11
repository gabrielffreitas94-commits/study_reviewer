"""Testes de integração para o repositório SqlAlchemyUserRepository e multi-tenancy (Sprint 02)."""

from collections.abc import Generator
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.adapters.persistence.repositories import (
    SqlAlchemySubjectRepository,
    SqlAlchemyUserRepository,
)
from src.domain.entities import Subject, User
from src.infrastructure.database import Base


@pytest.fixture
def db_session() -> Generator[Session]:
    """Fixture de sessão de banco em memória para testes de repositório."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.mark.integration
def test_save_and_retrieve_user(db_session: Session) -> None:
    """Valida persistência e recuperação de usuário por ID, Google Sub e E-mail."""
    repo = SqlAlchemyUserRepository(db_session)
    user = User(
        google_sub="sub-integration-001",
        email="estudante@integration.com",
        name="Estudante Integração",
        avatar_url="https://avatar.google.com/pic.png",
    )

    repo.save(user)

    # Busca por ID
    retrieved_by_id = repo.get_by_id(user.id)
    assert retrieved_by_id is not None
    assert retrieved_by_id.id == user.id
    assert retrieved_by_id.email == "estudante@integration.com"
    assert retrieved_by_id.name == "Estudante Integração"
    assert retrieved_by_id.avatar_url == "https://avatar.google.com/pic.png"

    # Busca por Google Sub
    retrieved_by_sub = repo.get_by_google_sub("sub-integration-001")
    assert retrieved_by_sub is not None
    assert retrieved_by_sub.id == user.id

    # Busca por E-mail (case-insensitive)
    retrieved_by_email = repo.get_by_email("ESTUDANTE@INTEGRATION.COM")
    assert retrieved_by_email is not None
    assert retrieved_by_email.id == user.id


@pytest.mark.integration
def test_update_existing_user_profile(db_session: Session) -> None:
    """Valida sincronização de dados de perfil de usuário existente."""
    repo = SqlAlchemyUserRepository(db_session)
    user = User(
        google_sub="sub-update-002",
        email="antigo@update.com",
        name="Nome Antigo",
        avatar_url="https://antigo.png",
    )
    repo.save(user)

    user.name = "Nome Atualizado"
    user.avatar_url = "https://novo.png"
    repo.save(user)

    updated = repo.get_by_id(user.id)
    assert updated is not None
    assert updated.name == "Nome Atualizado"
    assert updated.avatar_url == "https://novo.png"


@pytest.mark.integration
def test_get_user_not_found_returns_none(db_session: Session) -> None:
    """Garante que consultas para usuários inexistentes retornem None."""
    repo = SqlAlchemyUserRepository(db_session)
    assert repo.get_by_id(uuid4()) is None
    assert repo.get_by_google_sub("nao-existe") is None
    assert repo.get_by_email("inexistente@teste.com") is None


@pytest.mark.integration
@pytest.mark.security
def test_multi_tenant_subject_scoping_and_visibility(db_session: Session) -> None:
    """Valida isolamento multi-tenant de matérias no banco relacional.

    Vulnerabilidade prevenida: Insecure Direct Object Reference (IDOR) e vazamento
    de matérias privadas entre contas diferentes.
    Garantia de segurança: list_by_owner e list_accessible filtram estritamente
    por owner_id e is_public, e exists_by_name respeita o escopo do proprietário.
    """
    user_repo = SqlAlchemyUserRepository(db_session)
    subject_repo = SqlAlchemySubjectRepository(db_session)

    user_a = User(google_sub="sub-a", email="a@teste.com", name="User A")
    user_b = User(google_sub="sub-b", email="b@teste.com", name="User B")
    user_repo.save(user_a)
    user_repo.save(user_b)

    # User A cria matéria privada e matéria pública
    sub_a_priv = Subject(name="Direito Penal", owner_id=user_a.id, is_public=False)
    sub_a_pub = Subject(name="Direito Civil", owner_id=user_a.id, is_public=True)
    subject_repo.save(sub_a_priv)
    subject_repo.save(sub_a_pub)

    # User B cria matéria com mesmo nome de User A ("Direito Penal"), privada
    sub_b_priv = Subject(name="Direito Penal", owner_id=user_b.id, is_public=False)
    subject_repo.save(sub_b_priv)

    # Validação de list_by_owner
    owner_a_subs = subject_repo.list_by_owner(user_a.id)
    assert len(owner_a_subs) == 2
    assert all(s.owner_id == user_a.id for s in owner_a_subs)

    owner_b_subs = subject_repo.list_by_owner(user_b.id)
    assert len(owner_b_subs) == 1
    assert owner_b_subs[0].id == sub_b_priv.id

    # Validação de list_accessible (User B vê sua privada + pública de A)
    accessible_b = subject_repo.list_accessible(user_b.id)
    assert len(accessible_b) == 2
    accessible_ids_b = {s.id for s in accessible_b}
    assert sub_b_priv.id in accessible_ids_b
    assert sub_a_pub.id in accessible_ids_b
    assert sub_a_priv.id not in accessible_ids_b

    # Validação de exists_by_name com owner_id
    assert subject_repo.exists_by_name("Direito Penal", owner_id=user_a.id) is True
    assert subject_repo.exists_by_name("Direito Civil", owner_id=user_b.id) is False


@pytest.mark.integration
@pytest.mark.security
def test_cascade_delete_user_removes_subjects(db_session: Session) -> None:
    """Valida exclusão em cascata (ON DELETE CASCADE) ao remover um usuário.

    Vulnerabilidade prevenida: Registros órfãos desassociados que possam causar
    anomalias de integridade ou vazamento inadvertido de dados em consultas futuras.
    Garantia de segurança: Deletar um usuário remove compulsoriamente suas matérias do banco.
    """
    user_repo = SqlAlchemyUserRepository(db_session)
    subject_repo = SqlAlchemySubjectRepository(db_session)

    user = User(google_sub="sub-cascade", email="cascade@teste.com", name="Cascade User")
    user_repo.save(user)

    subject = Subject(name="Matéria para Deletar", owner_id=user.id, is_public=False)
    subject_repo.save(subject)
    assert subject_repo.get_by_id(subject.id) is not None

    # Deleta usuário
    from src.adapters.persistence.models import UserModel

    u_mod = db_session.get(UserModel, user.id)
    assert u_mod is not None
    db_session.delete(u_mod)
    db_session.commit()

    assert subject_repo.get_by_id(subject.id) is None


@pytest.mark.integration
def test_delete_user_via_repository(db_session: Session) -> None:
    """Valida a exclusão de usuário diretamente pelo repositório SqlAlchemyUserRepository."""
    user_repo = SqlAlchemyUserRepository(db_session)
    user = User(google_sub="sub-delete-repo", email="repo_del@teste.com", name="User Repo Del")
    user_repo.save(user)
    assert user_repo.get_by_id(user.id) is not None

    user_repo.delete(user.id)
    db_session.commit()

    assert user_repo.get_by_id(user.id) is None

    # Deletar usuário inexistente não deve levantar exceção
    user_repo.delete(uuid4())
