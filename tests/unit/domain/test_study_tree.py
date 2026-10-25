"""Testes unitários das entidades e serviços de domínio da Árvore de Estudos RPG (Clean Architecture - Camada 1)."""

from datetime import datetime
from uuid import uuid4

import pytest

from src.domain.entities import (
    StudyEdge,
    StudyMap,
    StudyNode,
    UserNodeProgress,
)
from src.domain.exceptions import (
    CrossMapEdgeError,
    CyclicDependencyError,
    DomainValidationError,
    SelfReferencingEdgeError,
)
from src.domain.services import (
    DAGValidatorService,
    StudyTreeProgressionService,
)


class TestStudyMapEntity:
    """Testes da entidade StudyMap."""

    def test_create_valid_study_map(self) -> None:
        owner_id = uuid4()
        s_map = StudyMap(
            owner_id=owner_id,
            title="Arquitetura de Software",
            description="Mapa de aprendizado em Clean Architecture",
        )
        assert s_map.id is not None
        assert s_map.owner_id == owner_id
        assert s_map.title == "Arquitetura de Software"
        assert s_map.description == "Mapa de aprendizado em Clean Architecture"
        assert s_map.is_public is False
        assert s_map.parent_node_id is None
        assert s_map.is_submap is False
        assert isinstance(s_map.created_at, datetime)

    def test_create_submap(self) -> None:
        owner_id = uuid4()
        parent_node_id = uuid4()
        s_map = StudyMap(
            owner_id=owner_id,
            title="Sub-mapa de Repositórios",
            parent_node_id=parent_node_id,
        )
        assert s_map.parent_node_id == parent_node_id
        assert s_map.is_submap is True

    def test_empty_or_whitespace_title_raises_error(self) -> None:
        with pytest.raises(
            DomainValidationError, match="Título do mapa de estudo não pode ser vazio."
        ):
            StudyMap(owner_id=uuid4(), title="   ")

    def test_title_longer_than_200_chars_raises_error(self) -> None:
        long_title = "A" * 201
        with pytest.raises(
            DomainValidationError,
            match="Título do mapa de estudo deve ter entre 1 e 200 caracteres.",
        ):
            StudyMap(owner_id=uuid4(), title=long_title)


class TestStudyNodeEntity:
    """Testes da entidade StudyNode."""

    def test_create_valid_study_node(self) -> None:
        map_id = uuid4()
        node = StudyNode(
            map_id=map_id,
            title="Camada de Domínio",
            description="Entidades puras e regras de negócio",
            pos_x=120.5,
            pos_y=250.0,
            icon="shield",
        )
        assert node.id is not None
        assert node.map_id == map_id
        assert node.title == "Camada de Domínio"
        assert node.pos_x == 120.5
        assert node.pos_y == 250.0
        assert node.icon == "shield"
        assert isinstance(node.created_at, datetime)

    def test_empty_node_title_raises_error(self) -> None:
        with pytest.raises(
            DomainValidationError, match="Título do nó de estudo não pode ser vazio."
        ):
            StudyNode(map_id=uuid4(), title=" ")

    def test_node_title_longer_than_150_chars_raises_error(self) -> None:
        long_title = "B" * 151
        with pytest.raises(
            DomainValidationError, match="Título do nó de estudo deve ter entre 1 e 150 caracteres."
        ):
            StudyNode(map_id=uuid4(), title=long_title)

    def test_update_position(self) -> None:
        node = StudyNode(map_id=uuid4(), title="Nó Móvel", pos_x=0.0, pos_y=0.0)
        old_updated_at = node.updated_at
        node.update_position(450.0, 320.0)
        assert node.pos_x == 450.0
        assert node.pos_y == 320.0
        assert node.updated_at >= old_updated_at


class TestStudyEdgeEntity:
    """Testes da entidade StudyEdge."""

    def test_create_valid_edge(self) -> None:
        map_id = uuid4()
        source_id = uuid4()
        target_id = uuid4()
        edge = StudyEdge(map_id=map_id, source_node_id=source_id, target_node_id=target_id)
        assert edge.id is not None
        assert edge.map_id == map_id
        assert edge.source_node_id == source_id
        assert edge.target_node_id == target_id

    def test_self_referencing_edge_raises_error(self) -> None:
        node_id = uuid4()
        with pytest.raises(
            SelfReferencingEdgeError, match="Um nó não pode ter dependência de si mesmo."
        ):
            StudyEdge(map_id=uuid4(), source_node_id=node_id, target_node_id=node_id)


class TestUserNodeProgressEntity:
    """Testes da entidade/Value Object UserNodeProgress."""

    def test_create_valid_progress(self) -> None:
        user_id = uuid4()
        node_id = uuid4()
        progress = UserNodeProgress(
            user_id=user_id,
            node_id=node_id,
            effective_level=3,
            is_unlocked=True,
            overdue_questions_count=1,
        )
        assert progress.user_id == user_id
        assert progress.node_id == node_id
        assert progress.effective_level == 3
        assert progress.is_unlocked is True
        assert progress.overdue_questions_count == 1

    def test_invalid_level_raises_error(self) -> None:
        with pytest.raises(DomainValidationError, match="Nível efetivo deve estar entre 0 e 6."):
            UserNodeProgress(user_id=uuid4(), node_id=uuid4(), effective_level=7, is_unlocked=True)

        with pytest.raises(DomainValidationError, match="Nível efetivo deve estar entre 0 e 6."):
            UserNodeProgress(
                user_id=uuid4(), node_id=uuid4(), effective_level=-1, is_unlocked=False
            )


class TestDAGValidatorService:
    """Testes do serviço de validação topológica de grafo acíclico dirigido."""

    def test_disallow_self_referencing_edge(self) -> None:
        validator = DAGValidatorService()
        node_a = uuid4()
        map_id = uuid4()
        with pytest.raises(SelfReferencingEdgeError):
            validator.validate_new_edge(
                existing_edges=[],
                map_id=map_id,
                source_node_id=node_a,
                target_node_id=node_a,
            )

    def test_disallow_cross_map_edge(self) -> None:
        validator = DAGValidatorService()
        map_a = uuid4()
        map_b = uuid4()
        node_a = uuid4()
        node_b = uuid4()
        edge = StudyEdge(map_id=map_a, source_node_id=node_a, target_node_id=node_b)
        with pytest.raises(
            CrossMapEdgeError, match="Arestas só podem conectar nós pertencentes ao mesmo mapa."
        ):
            validator.validate_new_edge(
                existing_edges=[edge],
                map_id=map_b,
                source_node_id=uuid4(),
                target_node_id=uuid4(),
            )

    def test_direct_cycle_raises_error(self) -> None:
        # A -> B already exists. Adding B -> A creates a direct cycle!
        validator = DAGValidatorService()
        map_id = uuid4()
        node_a = uuid4()
        node_b = uuid4()
        existing = [StudyEdge(map_id=map_id, source_node_id=node_a, target_node_id=node_b)]

        with pytest.raises(
            CyclicDependencyError, match="Aresta gera dependência cíclica no grafo de estudos."
        ):
            validator.validate_new_edge(
                existing_edges=existing,
                map_id=map_id,
                source_node_id=node_b,
                target_node_id=node_a,
            )

    def test_indirect_cycle_raises_error(self) -> None:
        # A -> B -> C -> D already exists. Adding D -> A creates an indirect cycle!
        validator = DAGValidatorService()
        map_id = uuid4()
        a, b, c, d = uuid4(), uuid4(), uuid4(), uuid4()
        existing = [
            StudyEdge(map_id=map_id, source_node_id=a, target_node_id=b),
            StudyEdge(map_id=map_id, source_node_id=b, target_node_id=c),
            StudyEdge(map_id=map_id, source_node_id=c, target_node_id=d),
        ]

        with pytest.raises(
            CyclicDependencyError, match="Aresta gera dependência cíclica no grafo de estudos."
        ):
            validator.validate_new_edge(
                existing_edges=existing,
                map_id=map_id,
                source_node_id=d,
                target_node_id=a,
            )

    def test_valid_dag_addition_succeeds(self) -> None:
        # Diamond DAG: A -> B, A -> C, B -> D, C -> D is valid!
        validator = DAGValidatorService()
        map_id = uuid4()
        a, b, c, d = uuid4(), uuid4(), uuid4(), uuid4()
        existing = [
            StudyEdge(map_id=map_id, source_node_id=a, target_node_id=b),
            StudyEdge(map_id=map_id, source_node_id=a, target_node_id=c),
            StudyEdge(map_id=map_id, source_node_id=b, target_node_id=d),
        ]
        # Adding C -> D
        assert (
            validator.validate_new_edge(
                existing_edges=existing,
                map_id=map_id,
                source_node_id=c,
                target_node_id=d,
            )
            is True
        )


class TestStudyTreeProgressionService:
    """Testes do serviço de cálculo de nível e regras de desbloqueio."""

    def test_node_level_is_min_of_questions(self) -> None:
        service = StudyTreeProgressionService()
        # Pergunta 1: Nível 3, Pergunta 2: Nível 1, Pergunta 3: Nível 4
        level = service.calculate_node_level(question_srs_levels=[3, 1, 4])
        assert level == 1

        # Todas nível 6 -> Nó nível 6 (Lendário)
        assert service.calculate_node_level(question_srs_levels=[6, 6, 6]) == 6

        # Uma nível 0 (ainda não consolidada) -> Nó nível 0
        assert service.calculate_node_level(question_srs_levels=[2, 0, 5]) == 0

    def test_node_level_inherits_from_submap_when_no_direct_questions(self) -> None:
        service = StudyTreeProgressionService()
        # Macro-nó sem perguntas próprias, mas com sub-mapa cujos nós têm níveis [2, 1, 3]
        level = service.calculate_node_level(question_srs_levels=[], sub_nodes_levels=[2, 1, 3])
        assert level == 1

        # Se algum sub-nó for 0 -> Macro-nó permanece 0
        level_zero = service.calculate_node_level(
            question_srs_levels=[], sub_nodes_levels=[2, 0, 3]
        )
        assert level_zero == 0

    def test_node_without_questions_and_submap_is_level_zero(self) -> None:
        service = StudyTreeProgressionService()
        assert service.calculate_node_level(question_srs_levels=[]) == 0
        assert service.calculate_node_level(question_srs_levels=[], sub_nodes_levels=[]) == 0

    def test_unlock_rule_root_node_is_always_unlocked(self) -> None:
        service = StudyTreeProgressionService()
        # Sem arestas de entrada -> Desbloqueado!
        assert service.evaluate_unlock_status(incoming_edges=[], prerequisites_levels={}) is True

    def test_unlock_rule_all_prerequisites_must_be_level_1_or_greater(self) -> None:
        service = StudyTreeProgressionService()
        target_id = uuid4()
        parent_1 = uuid4()
        parent_2 = uuid4()
        edges = [
            StudyEdge(map_id=uuid4(), source_node_id=parent_1, target_node_id=target_id),
            StudyEdge(map_id=uuid4(), source_node_id=parent_2, target_node_id=target_id),
        ]

        # Ambos os pais em nível >= 1 -> Desbloqueado
        assert (
            service.evaluate_unlock_status(
                incoming_edges=edges,
                prerequisites_levels={parent_1: 1, parent_2: 3},
            )
            is True
        )

        # Um dos pais em nível 0 -> Bloqueado
        assert (
            service.evaluate_unlock_status(
                incoming_edges=edges,
                prerequisites_levels={parent_1: 1, parent_2: 0},
            )
            is False
        )
