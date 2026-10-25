"""Testes unitários dos casos de uso da Árvore de Estudos RPG (Clean Architecture - Camada 2)."""

from datetime import date
from uuid import UUID, uuid4

import pytest

from src.application.dto.study_tree_dto import (
    ConnectNodesDTO,
    CreateStudyMapDTO,
    CreateStudyNodeDTO,
    NodePositionDTO,
)
from src.application.ports.repositories import (
    INodeContentRepository,
    IQuestionProgressRepository,
    IStudyEdgeRepository,
    IStudyMapRepository,
    IStudyNodeRepository,
)
from src.application.use_cases.study_tree_use_cases import (
    AttachContentToNodeUseCase,
    ConnectStudyNodesUseCase,
    CreateStudyMapUseCase,
    CreateStudyNodeUseCase,
    DetachContentFromNodeUseCase,
    GetStudyMapGraphUseCase,
    UpdateNodePositionsBatchUseCase,
)
from src.domain.entities import (
    StudyEdge,
    StudyMap,
    StudyNode,
    UserQuestionProgress,
)
from src.domain.exceptions import (
    CyclicDependencyError,
    ResourceOwnershipError,
)


class FakeStudyMapRepository(IStudyMapRepository):
    def __init__(self) -> None:
        self.maps: dict[UUID, StudyMap] = {}

    def get_by_id(self, map_id: UUID) -> StudyMap | None:
        return self.maps.get(map_id)

    def list_by_owner(self, owner_id: UUID) -> list[StudyMap]:
        return [m for m in self.maps.values() if m.owner_id == owner_id]

    def save(self, study_map: StudyMap) -> StudyMap:
        self.maps[study_map.id] = study_map
        return study_map

    def delete(self, map_id: UUID) -> None:
        self.maps.pop(map_id, None)


class FakeStudyNodeRepository(IStudyNodeRepository):
    def __init__(self) -> None:
        self.nodes: dict[UUID, StudyNode] = {}

    def get_by_id(self, node_id: UUID) -> StudyNode | None:
        return self.nodes.get(node_id)

    def list_by_map(self, map_id: UUID) -> list[StudyNode]:
        return [n for n in self.nodes.values() if n.map_id == map_id]

    def save(self, node: StudyNode) -> StudyNode:
        self.nodes[node.id] = node
        return node

    def update_positions_batch(self, positions: list[tuple[UUID, float, float]]) -> None:
        for node_id, x, y in positions:
            if node_id in self.nodes:
                self.nodes[node_id].update_position(x, y)

    def delete(self, node_id: UUID) -> None:
        self.nodes.pop(node_id, None)


class FakeStudyEdgeRepository(IStudyEdgeRepository):
    def __init__(self) -> None:
        self.edges: dict[UUID, StudyEdge] = {}

    def list_by_map(self, map_id: UUID) -> list[StudyEdge]:
        return [e for e in self.edges.values() if e.map_id == map_id]

    def get_by_id(self, edge_id: UUID) -> StudyEdge | None:
        return self.edges.get(edge_id)

    def save(self, edge: StudyEdge) -> StudyEdge:
        self.edges[edge.id] = edge
        return edge

    def delete(self, edge_id: UUID) -> None:
        self.edges.pop(edge_id, None)


class FakeNodeContentRepository(INodeContentRepository):
    def __init__(self) -> None:
        self.materials: dict[UUID, set[UUID]] = {}
        self.questions: dict[UUID, set[UUID]] = {}
        self.flashcards: dict[UUID, set[UUID]] = {}

    def attach_knowledge_source(self, node_id: UUID, source_id: UUID) -> None:
        self.materials.setdefault(node_id, set()).add(source_id)

    def detach_knowledge_source(self, node_id: UUID, source_id: UUID) -> None:
        self.materials.get(node_id, set()).discard(source_id)

    def attach_question(self, node_id: UUID, question_id: UUID) -> None:
        self.questions.setdefault(node_id, set()).add(question_id)

    def detach_question(self, node_id: UUID, question_id: UUID) -> None:
        self.questions.get(node_id, set()).discard(question_id)

    def attach_flashcard(self, node_id: UUID, flashcard_id: UUID) -> None:
        self.flashcards.setdefault(node_id, set()).add(flashcard_id)

    def detach_flashcard(self, node_id: UUID, flashcard_id: UUID) -> None:
        self.flashcards.get(node_id, set()).discard(flashcard_id)

    def get_attached_ids(self, node_id: UUID) -> tuple[list[UUID], list[UUID], list[UUID]]:
        return (
            list(self.materials.get(node_id, set())),
            list(self.questions.get(node_id, set())),
            list(self.flashcards.get(node_id, set())),
        )


class FakeQuestionProgressRepository(IQuestionProgressRepository):
    def __init__(self) -> None:
        self.progresses: dict[tuple[UUID, UUID], UserQuestionProgress] = {}

    def get(self, user_id: UUID, question_id: UUID) -> UserQuestionProgress | None:
        return self.progresses.get((user_id, question_id))

    def save(self, progress: UserQuestionProgress) -> None:
        self.progresses[(progress.user_id, progress.question_id)] = progress

    def get_by_questions(
        self, user_id: UUID, question_ids: list[UUID]
    ) -> dict[UUID, UserQuestionProgress]:
        return {
            qid: self.progresses[(user_id, qid)]
            for qid in question_ids
            if (user_id, qid) in self.progresses
        }


# --- Testes dos Casos de Uso ---


class TestCreateStudyMapUseCase:
    def test_create_root_map_success(self) -> None:
        map_repo = FakeStudyMapRepository()
        use_case = CreateStudyMapUseCase(map_repo=map_repo)
        owner_id = uuid4()

        dto = CreateStudyMapDTO(title="Ciência da Computação", description="Mapa Principal")
        result = use_case.execute(owner_id=owner_id, dto=dto)

        assert result.title == "Ciência da Computação"
        assert result.owner_id == owner_id
        assert result.parent_node_id is None
        assert result.id in map_repo.maps

    def test_create_submap_success(self) -> None:
        map_repo = FakeStudyMapRepository()
        node_repo = FakeStudyNodeRepository()
        use_case = CreateStudyMapUseCase(map_repo=map_repo, node_repo=node_repo)
        owner_id = uuid4()
        root_map = map_repo.save(StudyMap(owner_id=owner_id, title="Root"))
        parent_node = node_repo.save(StudyNode(map_id=root_map.id, title="Macro Nó"))

        dto = CreateStudyMapDTO(title="Sub-mapa", parent_node_id=parent_node.id)
        result = use_case.execute(owner_id=owner_id, dto=dto)

        assert result.title == "Sub-mapa"
        assert result.parent_node_id == parent_node.id


class TestGetStudyMapGraphUseCase:
    def test_get_graph_with_progress_and_unlock_calculation(self) -> None:
        owner_id = uuid4()
        map_repo = FakeStudyMapRepository()
        node_repo = FakeStudyNodeRepository()
        edge_repo = FakeStudyEdgeRepository()
        content_repo = FakeNodeContentRepository()
        progress_repo = FakeQuestionProgressRepository()

        # Cria mapa com 2 nós: Node A -> Node B
        s_map = map_repo.save(StudyMap(owner_id=owner_id, title="Mapa RPG"))
        node_a = node_repo.save(StudyNode(map_id=s_map.id, title="Nó A", pos_x=0.0, pos_y=0.0))
        node_b = node_repo.save(StudyNode(map_id=s_map.id, title="Nó B", pos_x=100.0, pos_y=0.0))
        edge_repo.save(
            StudyEdge(map_id=s_map.id, source_node_id=node_a.id, target_node_id=node_b.id)
        )

        # Vincula pergunta a Node A com progresso nível 1
        q_id = uuid4()
        content_repo.attach_question(node_a.id, q_id)
        progress_repo.save(
            UserQuestionProgress(
                user_id=owner_id,
                question_id=q_id,
                current_level=1,
                next_review_date=date.today(),
            )
        )

        use_case = GetStudyMapGraphUseCase(
            map_repo=map_repo,
            node_repo=node_repo,
            edge_repo=edge_repo,
            content_repo=content_repo,
            progress_repo=progress_repo,
        )

        graph = use_case.execute(map_id=s_map.id, user_id=owner_id)

        assert graph.map.id == s_map.id
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1

        node_a_dto = next(n for n in graph.nodes if n.id == node_a.id)
        node_b_dto = next(n for n in graph.nodes if n.id == node_b.id)

        # Node A é raiz (sem pré-requisitos) e atingiu Nível 1
        assert node_a_dto.is_unlocked is True
        assert node_a_dto.effective_level == 1
        assert node_a_dto.overdue_questions_count == 1  # next_review_date == today

        # Node B tem pré-requisito Node A (que está nível 1), logo Node B está DESBLOQUEADO
        assert node_b_dto.is_unlocked is True
        assert node_b_dto.effective_level == 0

    def test_idor_protection_raises_ownership_error(self) -> None:
        owner_id = uuid4()
        other_user = uuid4()
        map_repo = FakeStudyMapRepository()
        s_map = map_repo.save(StudyMap(owner_id=owner_id, title="Mapa Privado", is_public=False))

        use_case = GetStudyMapGraphUseCase(
            map_repo=map_repo,
            node_repo=FakeStudyNodeRepository(),
            edge_repo=FakeStudyEdgeRepository(),
            content_repo=FakeNodeContentRepository(),
            progress_repo=FakeQuestionProgressRepository(),
        )

        with pytest.raises(ResourceOwnershipError):
            use_case.execute(map_id=s_map.id, user_id=other_user)


class TestCreateStudyNodeUseCase:
    def test_create_node_success(self) -> None:
        owner_id = uuid4()
        map_repo = FakeStudyMapRepository()
        node_repo = FakeStudyNodeRepository()
        s_map = map_repo.save(StudyMap(owner_id=owner_id, title="Mapa 1"))

        use_case = CreateStudyNodeUseCase(map_repo=map_repo, node_repo=node_repo)
        dto = CreateStudyNodeDTO(title="Novo Nó", pos_x=50.0, pos_y=75.0, icon="shield")

        result = use_case.execute(map_id=s_map.id, user_id=owner_id, dto=dto)

        assert result.title == "Novo Nó"
        assert result.pos_x == 50.0
        assert result.pos_y == 75.0
        assert result.icon == "shield"
        assert result.id in node_repo.nodes


class TestUpdateNodePositionsBatchUseCase:
    def test_update_positions_batch(self) -> None:
        owner_id = uuid4()
        map_repo = FakeStudyMapRepository()
        node_repo = FakeStudyNodeRepository()
        s_map = map_repo.save(StudyMap(owner_id=owner_id, title="Mapa 1"))
        n1 = node_repo.save(StudyNode(map_id=s_map.id, title="Nó 1", pos_x=0.0, pos_y=0.0))
        n2 = node_repo.save(StudyNode(map_id=s_map.id, title="Nó 2", pos_x=10.0, pos_y=10.0))

        use_case = UpdateNodePositionsBatchUseCase(map_repo=map_repo, node_repo=node_repo)
        dtos = [
            NodePositionDTO(node_id=n1.id, pos_x=120.0, pos_y=240.0),
            NodePositionDTO(node_id=n2.id, pos_x=300.0, pos_y=400.0),
        ]

        use_case.execute(map_id=s_map.id, user_id=owner_id, positions=dtos)

        assert node_repo.nodes[n1.id].pos_x == 120.0
        assert node_repo.nodes[n1.id].pos_y == 240.0
        assert node_repo.nodes[n2.id].pos_x == 300.0
        assert node_repo.nodes[n2.id].pos_y == 400.0


class TestConnectStudyNodesUseCase:
    def test_connect_nodes_success(self) -> None:
        owner_id = uuid4()
        map_repo = FakeStudyMapRepository()
        node_repo = FakeStudyNodeRepository()
        edge_repo = FakeStudyEdgeRepository()
        s_map = map_repo.save(StudyMap(owner_id=owner_id, title="Mapa 1"))
        n1 = node_repo.save(StudyNode(map_id=s_map.id, title="Nó 1"))
        n2 = node_repo.save(StudyNode(map_id=s_map.id, title="Nó 2"))

        use_case = ConnectStudyNodesUseCase(
            map_repo=map_repo, node_repo=node_repo, edge_repo=edge_repo
        )
        edge_dto = use_case.execute(
            map_id=s_map.id,
            user_id=owner_id,
            dto=ConnectNodesDTO(source_node_id=n1.id, target_node_id=n2.id),
        )

        assert edge_dto.source_node_id == n1.id
        assert edge_dto.target_node_id == n2.id
        assert len(edge_repo.edges) == 1

    def test_connect_nodes_rejects_cycle(self) -> None:
        owner_id = uuid4()
        map_repo = FakeStudyMapRepository()
        node_repo = FakeStudyNodeRepository()
        edge_repo = FakeStudyEdgeRepository()
        s_map = map_repo.save(StudyMap(owner_id=owner_id, title="Mapa 1"))
        n1 = node_repo.save(StudyNode(map_id=s_map.id, title="Nó 1"))
        n2 = node_repo.save(StudyNode(map_id=s_map.id, title="Nó 2"))
        edge_repo.save(StudyEdge(map_id=s_map.id, source_node_id=n1.id, target_node_id=n2.id))

        use_case = ConnectStudyNodesUseCase(
            map_repo=map_repo, node_repo=node_repo, edge_repo=edge_repo
        )
        with pytest.raises(CyclicDependencyError):
            use_case.execute(
                map_id=s_map.id,
                user_id=owner_id,
                dto=ConnectNodesDTO(source_node_id=n2.id, target_node_id=n1.id),
            )


class TestAttachAndDetachContentUseCase:
    def test_attach_and_detach_content(self) -> None:
        owner_id = uuid4()
        map_repo = FakeStudyMapRepository()
        node_repo = FakeStudyNodeRepository()
        content_repo = FakeNodeContentRepository()
        s_map = map_repo.save(StudyMap(owner_id=owner_id, title="Mapa 1"))
        node = node_repo.save(StudyNode(map_id=s_map.id, title="Nó 1"))

        attach_uc = AttachContentToNodeUseCase(
            map_repo=map_repo, node_repo=node_repo, content_repo=content_repo
        )
        detach_uc = DetachContentFromNodeUseCase(
            map_repo=map_repo, node_repo=node_repo, content_repo=content_repo
        )

        q_id = uuid4()
        m_id = uuid4()
        f_id = uuid4()

        attach_uc.execute(
            map_id=s_map.id,
            user_id=owner_id,
            node_id=node.id,
            content_type="question",
            content_id=q_id,
        )
        attach_uc.execute(
            map_id=s_map.id,
            user_id=owner_id,
            node_id=node.id,
            content_type="material",
            content_id=m_id,
        )
        attach_uc.execute(
            map_id=s_map.id,
            user_id=owner_id,
            node_id=node.id,
            content_type="flashcard",
            content_id=f_id,
        )

        mats, ques, flashs = content_repo.get_attached_ids(node.id)
        assert q_id in ques
        assert m_id in mats
        assert f_id in flashs

        detach_uc.execute(
            map_id=s_map.id,
            user_id=owner_id,
            node_id=node.id,
            content_type="question",
            content_id=q_id,
        )
        _, ques_after, _ = content_repo.get_attached_ids(node.id)
        assert q_id not in ques_after
