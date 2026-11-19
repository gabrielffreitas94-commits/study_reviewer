"""Script de seed offline para criação do usuário demo e mapa de estudos inicial."""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

import src.adapters.persistence.models  # noqa: F401
from src.adapters.persistence.repositories import (
    SqlAlchemyFlashcardRepository,
    SqlAlchemyKnowledgeSourceRepository,
    SqlAlchemyNodeContentRepository,
    SqlAlchemyQuestionRepository,
    SqlAlchemyStudyEdgeRepository,
    SqlAlchemyStudyMapRepository,
    SqlAlchemyStudyNodeRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyTopicRepository,
    SqlAlchemyUserRepository,
)
from src.application.use_cases.auth_use_cases import (
    DEMO_EMAIL,
    DEMO_GOOGLE_SUB,
    DEMO_NAME,
)
from src.application.use_cases.sample_study_map_use_case import (
    CreateSampleMathStudyMapUseCase,
)
from src.domain.entities import User
from src.infrastructure.database import Base, SessionLocal, engine
from src.infrastructure.security.password_hasher import Pbkdf2PasswordHasher

logger = logging.getLogger("study_reviewer.seed_demo")

DEMO_DEFAULT_PASSWORD = "DemoPass123!"  # noqa: S105


def seed_demo(db: Session | None = None) -> UUID:
    """Garante a existência da conta demo offline e do mapa de estudos de exemplo."""
    owns_session = db is None
    session = db if db is not None else SessionLocal()
    if owns_session:
        Base.metadata.create_all(bind=engine)

    try:
        user_repo = SqlAlchemyUserRepository(session)
        password_hasher = Pbkdf2PasswordHasher()

        user = user_repo.get_by_email(DEMO_EMAIL)
        if user is None:
            user = User(
                google_sub=DEMO_GOOGLE_SUB,
                email=DEMO_EMAIL,
                name=DEMO_NAME,
                password_hash=password_hasher.hash_password(DEMO_DEFAULT_PASSWORD),
            )
            user_repo.save(user)

        map_repo = SqlAlchemyStudyMapRepository(session)
        if not map_repo.list_by_owner(user.id):
            CreateSampleMathStudyMapUseCase(
                map_repo=map_repo,
                node_repo=SqlAlchemyStudyNodeRepository(session),
                edge_repo=SqlAlchemyStudyEdgeRepository(session),
                content_repo=SqlAlchemyNodeContentRepository(session),
                source_repo=SqlAlchemyKnowledgeSourceRepository(session),
                question_repo=SqlAlchemyQuestionRepository(session),
                flashcard_repo=SqlAlchemyFlashcardRepository(session),
                subject_repo=SqlAlchemySubjectRepository(session),
                topic_repo=SqlAlchemyTopicRepository(session),
            ).execute(user.id)

        session.commit()
        return user.id
    finally:
        if owns_session:
            session.close()


def main() -> None:
    """Ponto de entrada CLI para popular a conta e mapa de demonstração."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    user_id = seed_demo()
    logger.info("Seed demo concluído com sucesso para user_id=%s (%s)", user_id, DEMO_EMAIL)


if __name__ == "__main__":
    main()
