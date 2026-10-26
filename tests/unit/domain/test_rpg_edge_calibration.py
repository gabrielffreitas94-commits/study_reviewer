from uuid import uuid4

import pytest

from src.adapters.persistence.mappers import StudyEdgeMapper
from src.adapters.persistence.models import StudyEdgeModel
from src.domain.entities import StudyEdge
from src.domain.services import StudyTreeProgressionService


class TestStudyEdgeCalibration:
    """Testes de calibração de nível exigido por aresta (StudyEdge.required_level)."""

    def test_study_edge_default_required_level(self) -> None:
        edge = StudyEdge(
            map_id=uuid4(),
            source_node_id=uuid4(),
            target_node_id=uuid4(),
        )
        assert edge.required_level == 1

    def test_study_edge_custom_required_level(self) -> None:
        edge = StudyEdge(
            map_id=uuid4(),
            source_node_id=uuid4(),
            target_node_id=uuid4(),
            required_level=3,
        )
        assert edge.required_level == 3

    def test_study_edge_invalid_required_level_raises_error(self) -> None:
        with pytest.raises(ValueError, match="required_level deve ser maior ou igual a 1"):
            StudyEdge(
                map_id=uuid4(),
                source_node_id=uuid4(),
                target_node_id=uuid4(),
                required_level=0,
            )

        with pytest.raises(ValueError, match="required_level deve ser maior ou igual a 1"):
            StudyEdge(
                map_id=uuid4(),
                source_node_id=uuid4(),
                target_node_id=uuid4(),
                required_level=-1,
            )


class TestStudyTreeProgressionServiceEdgeCalibration:
    """Testes de avaliação de desbloqueio com calibração de nível por aresta."""

    def test_single_edge_required_level_1(self) -> None:
        service = StudyTreeProgressionService()
        node_a = uuid4()
        node_b = uuid4()
        edge = StudyEdge(
            map_id=uuid4(),
            source_node_id=node_a,
            target_node_id=node_b,
            required_level=1,
        )

        # Node A level 0 -> locked
        assert not service.evaluate_unlock_status(
            incoming_edges=[edge],
            prerequisites_levels={node_a: 0},
        )
        # Node A not in prerequisites_levels (default 0) -> locked
        assert not service.evaluate_unlock_status(
            incoming_edges=[edge],
            prerequisites_levels={},
        )
        # Node A level 1 -> unlocked
        assert service.evaluate_unlock_status(
            incoming_edges=[edge],
            prerequisites_levels={node_a: 1},
        )
        # Node A level 2 -> unlocked
        assert service.evaluate_unlock_status(
            incoming_edges=[edge],
            prerequisites_levels={node_a: 2},
        )

    def test_single_edge_required_level_3(self) -> None:
        service = StudyTreeProgressionService()
        node_a = uuid4()
        node_c = uuid4()
        edge = StudyEdge(
            map_id=uuid4(),
            source_node_id=node_a,
            target_node_id=node_c,
            required_level=3,
        )

        for lvl in [0, 1, 2]:
            assert not service.evaluate_unlock_status(
                incoming_edges=[edge],
                prerequisites_levels={node_a: lvl},
            ), f"Expected locked for level {lvl}"

        assert service.evaluate_unlock_status(
            incoming_edges=[edge],
            prerequisites_levels={node_a: 3},
        )
        assert service.evaluate_unlock_status(
            incoming_edges=[edge],
            prerequisites_levels={node_a: 5},
        )

    def test_multi_dependency_conjunctive_unlock(self) -> None:
        service = StudyTreeProgressionService()
        node_a = uuid4()
        node_b = uuid4()
        node_c = uuid4()

        edge_a_c = StudyEdge(
            map_id=uuid4(),
            source_node_id=node_a,
            target_node_id=node_c,
            required_level=3,
        )
        edge_b_c = StudyEdge(
            map_id=uuid4(),
            source_node_id=node_b,
            target_node_id=node_c,
            required_level=1,
        )
        edges = [edge_a_c, edge_b_c]

        # If A=2, B=1 -> Locked (A needs 3)
        assert not service.evaluate_unlock_status(
            incoming_edges=edges,
            prerequisites_levels={node_a: 2, node_b: 1},
        )

        # If A=3, B=0 -> Locked (B needs 1)
        assert not service.evaluate_unlock_status(
            incoming_edges=edges,
            prerequisites_levels={node_a: 3, node_b: 0},
        )

        # If A=3, B=1 -> Unlocked
        assert service.evaluate_unlock_status(
            incoming_edges=edges,
            prerequisites_levels={node_a: 3, node_b: 1},
        )

        # If A=4, B=2 -> Unlocked
        assert service.evaluate_unlock_status(
            incoming_edges=edges,
            prerequisites_levels={node_a: 4, node_b: 2},
        )


class TestStudyEdgeMapper:
    """Testes de mapeamento de StudyEdge e StudyEdgeModel."""

    def test_to_domain_maps_required_level(self) -> None:
        model = StudyEdgeModel(
            id=uuid4(),
            map_id=uuid4(),
            source_node_id=uuid4(),
            target_node_id=uuid4(),
            required_level=4,
        )
        domain = StudyEdgeMapper.to_domain(model)
        assert domain.required_level == 4

    def test_to_domain_fallback_when_required_level_none(self) -> None:
        model = StudyEdgeModel(
            id=uuid4(),
            map_id=uuid4(),
            source_node_id=uuid4(),
            target_node_id=uuid4(),
        )
        object.__setattr__(model, "required_level", None)
        domain = StudyEdgeMapper.to_domain(model)
        assert domain.required_level == 1

    def test_to_model_maps_required_level(self) -> None:
        entity = StudyEdge(
            id=uuid4(),
            map_id=uuid4(),
            source_node_id=uuid4(),
            target_node_id=uuid4(),
            required_level=5,
        )
        model = StudyEdgeMapper.to_model(entity)
        assert model.required_level == 5
