"""Casos de uso para Matérias (Clean Architecture - Camada 2)."""

from uuid import UUID, uuid4

from src.application.dto.subject_dto import CreateSubjectDTO, SubjectDTO
from src.application.ports.repositories import ISubjectRepository
from src.domain.entities import Subject
from src.domain.exceptions import DuplicateEntityError


class CreateSubjectUseCase:
    """Caso de uso para criação de uma nova matéria com suporte a multi-tenancy e visibilidade."""

    def __init__(self, subject_repo: ISubjectRepository) -> None:
        self._subject_repo = subject_repo

    def execute(self, input_dto: CreateSubjectDTO, owner_id: UUID | None = None) -> SubjectDTO:
        clean_name = input_dto.name.strip()
        if self._subject_repo.exists_by_name(clean_name, owner_id=owner_id):
            raise DuplicateEntityError(f"Matéria com nome '{clean_name}' já cadastrada.")

        resolved_owner = owner_id if owner_id is not None else uuid4()
        subject = Subject(
            name=clean_name,
            owner_id=resolved_owner,
            is_public=input_dto.is_public,
        )
        self._subject_repo.save(subject)

        return SubjectDTO(
            id=subject.id,
            name=subject.name,
            owner_id=subject.owner_id,
            is_public=subject.is_public,
            is_owner=True,
            created_at=subject.created_at,
        )


class ListSubjectsUseCase:
    """Caso de uso para listagem de matérias acessíveis (próprias + públicas)."""

    def __init__(self, subject_repo: ISubjectRepository) -> None:
        self._subject_repo = subject_repo

    def execute(self, user_id: UUID | None = None) -> list[SubjectDTO]:
        if user_id is not None:
            subjects = self._subject_repo.list_accessible(user_id)
        else:
            subjects = self._subject_repo.list_all()

        return [
            SubjectDTO(
                id=s.id,
                name=s.name,
                owner_id=s.owner_id,
                is_public=s.is_public,
                is_owner=(s.owner_id == user_id if user_id is not None else True),
                created_at=s.created_at,
            )
            for s in subjects
        ]
