"""Testes unitários para os casos de uso de Matéria (Camada 2 - Aplicação)."""

import pytest

from src.application.dto.subject_dto import CreateSubjectDTO
from src.application.use_cases.subject_use_cases import (
    CreateSubjectUseCase,
    ListSubjectsUseCase,
)
from src.domain.exceptions import DomainValidationError, DuplicateEntityError
from tests.unit.application.fakes import FakeSubjectRepository


@pytest.mark.unit
def test_create_subject_success() -> None:
    """Criação bem-sucedida de nova matéria."""
    repo = FakeSubjectRepository()
    use_case = CreateSubjectUseCase(repo)

    dto = use_case.execute(CreateSubjectDTO(name="Direito Constitucional"))

    assert dto.name == "Direito Constitucional"
    assert repo.exists_by_name("Direito Constitucional") is True


@pytest.mark.unit
def test_create_subject_duplicate_raises_error() -> None:
    """Tentativa de criar matéria com nome já cadastrado dispara DuplicateEntityError."""
    repo = FakeSubjectRepository()
    use_case = CreateSubjectUseCase(repo)

    use_case.execute(CreateSubjectDTO(name="Direito Constitucional"))

    with pytest.raises(DuplicateEntityError, match="já cadastrada"):
        use_case.execute(CreateSubjectDTO(name="direito constitucional"))


@pytest.mark.unit
def test_create_subject_invalid_name_raises_domain_error() -> None:
    """Tentativa de criar matéria com nome inválido propaga DomainValidationError."""
    repo = FakeSubjectRepository()
    use_case = CreateSubjectUseCase(repo)

    with pytest.raises(DomainValidationError):
        use_case.execute(CreateSubjectDTO(name=" "))


@pytest.mark.unit
def test_list_subjects_empty() -> None:
    """Listagem de matérias com repositório vazio retorna lista vazia."""
    repo = FakeSubjectRepository()
    use_case = ListSubjectsUseCase(repo)

    subjects = use_case.execute()
    assert subjects == []


@pytest.mark.unit
def test_list_subjects_ordered() -> None:
    """Listagem de matérias retorna itens ordenados alfabeticamente."""
    repo = FakeSubjectRepository()
    create_uc = CreateSubjectUseCase(repo)
    list_uc = ListSubjectsUseCase(repo)

    create_uc.execute(CreateSubjectDTO(name="Matemática"))
    create_uc.execute(CreateSubjectDTO(name="Biologia"))
    create_uc.execute(CreateSubjectDTO(name="Física"))

    subjects = list_uc.execute()
    assert [s.name for s in subjects] == ["Biologia", "Física", "Matemática"]
