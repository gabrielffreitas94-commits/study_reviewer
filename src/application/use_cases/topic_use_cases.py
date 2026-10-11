"""Casos de uso para Temas (Clean Architecture - Camada 2)."""

from uuid import UUID

from src.application.dto.topic_dto import CreateTopicDTO, TopicDTO
from src.application.ports.repositories import ISubjectRepository, ITopicRepository
from src.domain.entities import Topic
from src.domain.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    ResourceOwnershipError,
)


class CreateTopicUseCase:
    """Caso de uso para criação de tema vinculado a uma matéria com verificação de titularidade."""

    def __init__(self, subject_repo: ISubjectRepository, topic_repo: ITopicRepository) -> None:
        self._subject_repo = subject_repo
        self._topic_repo = topic_repo

    def execute(self, input_dto: CreateTopicDTO, user_id: UUID | None = None) -> TopicDTO:
        subject = self._subject_repo.get_by_id(input_dto.subject_id)
        if subject is None:
            raise EntityNotFoundError("Matéria não encontrada.")

        if user_id is not None and not subject.can_be_edited_by(user_id):
            raise ResourceOwnershipError(
                "Você não tem permissão para adicionar temas a esta matéria."
            )

        clean_name = input_dto.name.strip()
        if self._topic_repo.exists_by_name(input_dto.subject_id, clean_name):
            raise DuplicateEntityError(f"Tema '{clean_name}' já cadastrado nesta matéria.")

        topic = Topic(subject_id=input_dto.subject_id, name=clean_name)
        self._topic_repo.save(topic)

        return TopicDTO(
            id=topic.id,
            subject_id=topic.subject_id,
            name=topic.name,
            created_at=topic.created_at,
        )


class ListTopicsBySubjectUseCase:
    """Caso de uso para listagem de temas de uma matéria."""

    def __init__(self, topic_repo: ITopicRepository) -> None:
        self._topic_repo = topic_repo

    def execute(self, subject_id: UUID) -> list[TopicDTO]:
        topics = self._topic_repo.list_by_subject(subject_id)
        return [
            TopicDTO(
                id=t.id,
                subject_id=t.subject_id,
                name=t.name,
                created_at=t.created_at,
            )
            for t in topics
        ]
