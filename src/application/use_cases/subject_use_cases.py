"""Casos de uso para Matérias (Clean Architecture - Camada 2)."""

from src.application.dto.subject_dto import CreateSubjectDTO, SubjectDTO
from src.application.ports.repositories import ISubjectRepository
from src.domain.entities import Subject
from src.domain.exceptions import DuplicateEntityError


class CreateSubjectUseCase:
    """Caso de uso para criação de uma nova matéria."""

    def __init__(self, subject_repo: ISubjectRepository) -> None:
        self._subject_repo = subject_repo

    def execute(self, input_dto: CreateSubjectDTO) -> SubjectDTO:
        clean_name = input_dto.name.strip()
        if self._subject_repo.exists_by_name(clean_name):
            raise DuplicateEntityError(f"Matéria com nome '{clean_name}' já cadastrada.")

        subject = Subject(name=clean_name)
        self._subject_repo.save(subject)

        return SubjectDTO(
            id=subject.id,
            name=subject.name,
            created_at=subject.created_at,
        )


class ListSubjectsUseCase:
    """Caso de uso para listagem de todas as matérias."""

    def __init__(self, subject_repo: ISubjectRepository) -> None:
        self._subject_repo = subject_repo

    def execute(self) -> list[SubjectDTO]:
        subjects = self._subject_repo.list_all()
        return [SubjectDTO(id=s.id, name=s.name, created_at=s.created_at) for s in subjects]
