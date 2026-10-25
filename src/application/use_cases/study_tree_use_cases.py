"""Casos de uso para a Árvore de Estudos RPG (Clean Architecture - Camada 2)."""

from datetime import date
from uuid import UUID

from src.application.dto.study_tree_dto import (
    ConnectNodesDTO,
    CreateStudyMapDTO,
    CreateStudyNodeDTO,
    NodePositionDTO,
    NodeStudyHubDTO,
    StudyEdgeDTO,
    StudyGraphDTO,
    StudyMapDTO,
    StudyNodeDTO,
    UpdateStudyNodeDTO,
)
from src.application.ports.repositories import (
    IFlashcardRepository,
    IKnowledgeSourceRepository,
    INodeContentRepository,
    IQuestionProgressRepository,
    IQuestionRepository,
    IStudyEdgeRepository,
    IStudyMapRepository,
    IStudyNodeRepository,
)
from src.domain.entities import (
    StudyEdge,
    StudyMap,
    StudyNode,
)
from src.domain.exceptions import (
    DomainValidationError,
    ResourceOwnershipError,
    StudyEdgeNotFoundError,
    StudyMapNotFoundError,
    StudyNodeNotFoundError,
)
from src.domain.services import (
    DAGValidatorService,
    StudyTreeProgressionService,
)


class CreateStudyMapUseCase:
    """Caso de uso para criação de um novo mapa de estudos raiz ou sub-mapa."""

    def __init__(
        self,
        map_repo: IStudyMapRepository,
        node_repo: IStudyNodeRepository | None = None,
    ) -> None:
        self.map_repo = map_repo
        self.node_repo = node_repo

    def execute(self, owner_id: UUID, dto: CreateStudyMapDTO) -> StudyMapDTO:
        if dto.parent_node_id is not None:
            if self.node_repo is not None:
                parent_node = self.node_repo.get_by_id(dto.parent_node_id)
                if parent_node is None:
                    raise StudyNodeNotFoundError(
                        f"Nó pai '{dto.parent_node_id}' não encontrado para o sub-mapa."
                    )

        study_map = StudyMap(
            owner_id=owner_id,
            title=dto.title,
            description=dto.description,
            is_public=dto.is_public,
            parent_node_id=dto.parent_node_id,
        )
        saved = self.map_repo.save(study_map)
        return StudyMapDTO(
            id=saved.id,
            owner_id=saved.owner_id,
            title=saved.title,
            description=saved.description,
            is_public=saved.is_public,
            parent_node_id=saved.parent_node_id,
            created_at=saved.created_at,
            updated_at=saved.updated_at,
        )


class GetStudyMapGraphUseCase:
    """Caso de uso para carregar o grafo com níveis SRS e desbloqueios dinâmicos."""

    def __init__(
        self,
        map_repo: IStudyMapRepository,
        node_repo: IStudyNodeRepository,
        edge_repo: IStudyEdgeRepository,
        content_repo: INodeContentRepository,
        progress_repo: IQuestionProgressRepository,
    ) -> None:
        self.map_repo = map_repo
        self.node_repo = node_repo
        self.edge_repo = edge_repo
        self.content_repo = content_repo
        self.progress_repo = progress_repo

    def execute(self, map_id: UUID, user_id: UUID) -> StudyGraphDTO:
        study_map = self.map_repo.get_by_id(map_id)
        if study_map is None:
            raise StudyMapNotFoundError(f"Mapa de estudo '{map_id}' não encontrado.")

        if study_map.owner_id != user_id and not study_map.is_public:
            raise ResourceOwnershipError(
                "Usuário não possui permissão de acesso a este mapa de estudos."
            )

        nodes = self.node_repo.list_by_map(map_id)
        edges = self.edge_repo.list_by_map(map_id)

        # Mapeamento de conteúdo e níveis por nó
        node_levels: dict[UUID, int] = {}
        node_overdues: dict[UUID, int] = {}
        node_contents: dict[UUID, tuple[list[UUID], list[UUID], list[UUID]]] = {}
        today = date.today()

        for node in nodes:
            mat_ids, q_ids, f_ids = self.content_repo.get_attached_ids(node.id)
            node_contents[node.id] = (mat_ids, q_ids, f_ids)

            if q_ids:
                progress_map = self.progress_repo.get_by_questions(user_id, q_ids)
                srs_levels: list[int] = []
                overdue_count = 0
                for qid in q_ids:
                    prog = progress_map.get(qid)
                    if prog is not None:
                        srs_levels.append(prog.current_level)
                        if prog.next_review_date <= today:
                            overdue_count += 1
                    else:
                        srs_levels.append(0)
                        overdue_count += 1
                effective_level = StudyTreeProgressionService.calculate_node_level(srs_levels)
                node_levels[node.id] = effective_level
                node_overdues[node.id] = overdue_count
            else:
                node_levels[node.id] = 0
                node_overdues[node.id] = 0

        # Avaliação da regra de desbloqueio com base nas arestas de entrada
        node_dtos: list[StudyNodeDTO] = []
        for node in nodes:
            incoming_edges = [e for e in edges if e.target_node_id == node.id]
            is_unlocked = StudyTreeProgressionService.evaluate_unlock_status(
                incoming_edges, node_levels
            )
            mat_ids, q_ids, f_ids = node_contents[node.id]

            node_dtos.append(
                StudyNodeDTO(
                    id=node.id,
                    map_id=node.map_id,
                    title=node.title,
                    description=node.description,
                    pos_x=node.pos_x,
                    pos_y=node.pos_y,
                    icon=node.icon,
                    effective_level=node_levels[node.id],
                    is_unlocked=is_unlocked,
                    overdue_questions_count=node_overdues[node.id],
                    has_submap=False,
                    materials_count=len(mat_ids),
                    questions_count=len(q_ids),
                    flashcards_count=len(f_ids),
                )
            )

        edge_dtos = [
            StudyEdgeDTO(
                id=e.id,
                map_id=e.map_id,
                source_node_id=e.source_node_id,
                target_node_id=e.target_node_id,
            )
            for e in edges
        ]

        map_dto = StudyMapDTO(
            id=study_map.id,
            owner_id=study_map.owner_id,
            title=study_map.title,
            description=study_map.description,
            is_public=study_map.is_public,
            parent_node_id=study_map.parent_node_id,
            created_at=study_map.created_at,
            updated_at=study_map.updated_at,
        )

        return StudyGraphDTO(map=map_dto, nodes=node_dtos, edges=edge_dtos)


class CreateStudyNodeUseCase:
    """Caso de uso para adição de um nó de conhecimento ao canvas."""

    def __init__(
        self,
        map_repo: IStudyMapRepository,
        node_repo: IStudyNodeRepository,
    ) -> None:
        self.map_repo = map_repo
        self.node_repo = node_repo

    def execute(self, map_id: UUID, user_id: UUID, dto: CreateStudyNodeDTO) -> StudyNodeDTO:
        study_map = self.map_repo.get_by_id(map_id)
        if study_map is None:
            raise StudyMapNotFoundError(f"Mapa de estudo '{map_id}' não encontrado.")
        if study_map.owner_id != user_id:
            raise ResourceOwnershipError("Apenas o proprietário do mapa pode adicionar nós.")

        node = StudyNode(
            map_id=map_id,
            title=dto.title,
            description=dto.description,
            pos_x=dto.pos_x,
            pos_y=dto.pos_y,
            icon=dto.icon,
        )
        saved = self.node_repo.save(node)
        return StudyNodeDTO(
            id=saved.id,
            map_id=saved.map_id,
            title=saved.title,
            description=saved.description,
            pos_x=saved.pos_x,
            pos_y=saved.pos_y,
            icon=saved.icon,
            effective_level=0,
            is_unlocked=True,
            overdue_questions_count=0,
            has_submap=False,
            materials_count=0,
            questions_count=0,
            flashcards_count=0,
        )


class UpdateStudyNodeUseCase:
    """Caso de uso para atualização de dados (título, descrição, ícone) de um nó."""

    def __init__(
        self,
        map_repo: IStudyMapRepository,
        node_repo: IStudyNodeRepository,
    ) -> None:
        self.map_repo = map_repo
        self.node_repo = node_repo

    def execute(
        self, map_id: UUID, user_id: UUID, node_id: UUID, dto: UpdateStudyNodeDTO
    ) -> StudyNodeDTO:
        study_map = self.map_repo.get_by_id(map_id)
        if study_map is None:
            raise StudyMapNotFoundError("Mapa não encontrado.")
        if study_map.owner_id != user_id:
            raise ResourceOwnershipError("Sem permissão para atualizar nós deste mapa.")

        node = self.node_repo.get_by_id(node_id)
        if node is None or node.map_id != map_id:
            raise StudyNodeNotFoundError(f"Nó '{node_id}' não encontrado no mapa.")

        if dto.title is not None:
            node.title = dto.title
        if dto.description is not None:
            node.description = dto.description
        if dto.icon is not None:
            node.icon = dto.icon

        node.__post_init__()
        saved = self.node_repo.save(node)
        return StudyNodeDTO(
            id=saved.id,
            map_id=saved.map_id,
            title=saved.title,
            description=saved.description,
            pos_x=saved.pos_x,
            pos_y=saved.pos_y,
            icon=saved.icon,
            effective_level=0,
            is_unlocked=True,
            overdue_questions_count=0,
            has_submap=False,
            materials_count=0,
            questions_count=0,
            flashcards_count=0,
        )


class UpdateNodePositionsBatchUseCase:
    """Caso de uso para atualizar posições (x, y) de múltiplos nós após arraste no canvas."""

    def __init__(
        self,
        map_repo: IStudyMapRepository,
        node_repo: IStudyNodeRepository,
    ) -> None:
        self.map_repo = map_repo
        self.node_repo = node_repo

    def execute(self, map_id: UUID, user_id: UUID, positions: list[NodePositionDTO]) -> None:
        study_map = self.map_repo.get_by_id(map_id)
        if study_map is None:
            raise StudyMapNotFoundError("Mapa nao encontrado.")
        if study_map.owner_id != user_id:
            raise ResourceOwnershipError("Sem permissão para alterar posições neste mapa.")

        coords = [(p.node_id, p.pos_x, p.pos_y) for p in positions]
        self.node_repo.update_positions_batch(coords)


class DeleteStudyNodeUseCase:
    """Caso de uso para remoção de um nó e suas arestas associadas."""

    def __init__(
        self,
        map_repo: IStudyMapRepository,
        node_repo: IStudyNodeRepository,
    ) -> None:
        self.map_repo = map_repo
        self.node_repo = node_repo

    def execute(self, map_id: UUID, user_id: UUID, node_id: UUID) -> None:
        study_map = self.map_repo.get_by_id(map_id)
        if study_map is None:
            raise StudyMapNotFoundError("Mapa não encontrado.")
        if study_map.owner_id != user_id:
            raise ResourceOwnershipError("Sem permissão para excluir nós deste mapa.")

        node = self.node_repo.get_by_id(node_id)
        if node is None or node.map_id != map_id:
            raise StudyNodeNotFoundError(f"Nó '{node_id}' não encontrado no mapa.")

        self.node_repo.delete(node_id)


class ConnectStudyNodesUseCase:
    """Caso de uso para conectar dois nós via aresta orientada com validação topológica de DAG."""

    def __init__(
        self,
        map_repo: IStudyMapRepository,
        node_repo: IStudyNodeRepository,
        edge_repo: IStudyEdgeRepository,
    ) -> None:
        self.map_repo = map_repo
        self.node_repo = node_repo
        self.edge_repo = edge_repo

    def execute(self, map_id: UUID, user_id: UUID, dto: ConnectNodesDTO) -> StudyEdgeDTO:
        study_map = self.map_repo.get_by_id(map_id)
        if study_map is None:
            raise StudyMapNotFoundError("Mapa não encontrado.")
        if study_map.owner_id != user_id:
            raise ResourceOwnershipError("Sem permissão para alterar dependências deste mapa.")

        source_node = self.node_repo.get_by_id(dto.source_node_id)
        target_node = self.node_repo.get_by_id(dto.target_node_id)
        if source_node is None or source_node.map_id != map_id:
            raise StudyNodeNotFoundError(f"Nó de origem '{dto.source_node_id}' inválido.")
        if target_node is None or target_node.map_id != map_id:
            raise StudyNodeNotFoundError(f"Nó de destino '{dto.target_node_id}' inválido.")

        existing_edges = self.edge_repo.list_by_map(map_id)
        DAGValidatorService.validate_new_edge(
            existing_edges=existing_edges,
            map_id=map_id,
            source_node_id=dto.source_node_id,
            target_node_id=dto.target_node_id,
        )

        edge = StudyEdge(
            map_id=map_id,
            source_node_id=dto.source_node_id,
            target_node_id=dto.target_node_id,
        )
        saved = self.edge_repo.save(edge)
        return StudyEdgeDTO(
            id=saved.id,
            map_id=saved.map_id,
            source_node_id=saved.source_node_id,
            target_node_id=saved.target_node_id,
        )


class DisconnectStudyNodesUseCase:
    """Caso de uso para remover uma dependência de pré-requisito."""

    def __init__(
        self,
        map_repo: IStudyMapRepository,
        edge_repo: IStudyEdgeRepository,
    ) -> None:
        self.map_repo = map_repo
        self.edge_repo = edge_repo

    def execute(self, map_id: UUID, user_id: UUID, edge_id: UUID) -> None:
        study_map = self.map_repo.get_by_id(map_id)
        if study_map is None:
            raise StudyMapNotFoundError("Mapa não encontrado.")
        if study_map.owner_id != user_id:
            raise ResourceOwnershipError("Sem permissão para alterar dependências deste mapa.")

        edge = self.edge_repo.get_by_id(edge_id)
        if edge is None or edge.map_id != map_id:
            raise StudyEdgeNotFoundError(f"Aresta '{edge_id}' não encontrada no mapa.")

        self.edge_repo.delete(edge_id)


class AttachContentToNodeUseCase:
    """Caso de uso para vincular material, pergunta ou flashcard ao nó."""

    def __init__(
        self,
        map_repo: IStudyMapRepository,
        node_repo: IStudyNodeRepository,
        content_repo: INodeContentRepository,
    ) -> None:
        self.map_repo = map_repo
        self.node_repo = node_repo
        self.content_repo = content_repo

    def execute(
        self,
        map_id: UUID,
        user_id: UUID,
        node_id: UUID,
        content_type: str,
        content_id: UUID,
    ) -> None:
        study_map = self.map_repo.get_by_id(map_id)
        if study_map is None:
            raise StudyMapNotFoundError("Mapa não encontrado.")
        if study_map.owner_id != user_id:
            raise ResourceOwnershipError("Sem permissão para alterar conteúdos deste nó.")

        node = self.node_repo.get_by_id(node_id)
        if node is None or node.map_id != map_id:
            raise StudyNodeNotFoundError(f"Nó '{node_id}' não encontrado no mapa.")

        clean_type = content_type.lower().strip()
        if clean_type in ("material", "knowledge_source"):
            self.content_repo.attach_knowledge_source(node_id, content_id)
        elif clean_type in ("question", "open_question"):
            self.content_repo.attach_question(node_id, content_id)
        elif clean_type in ("flashcard",):
            self.content_repo.attach_flashcard(node_id, content_id)
        else:
            raise DomainValidationError(
                f"Tipo de conteúdo inválido para vinculação: '{content_type}'."
            )


class DetachContentFromNodeUseCase:
    """Caso de uso para desvincular material, pergunta ou flashcard de um nó."""

    def __init__(
        self,
        map_repo: IStudyMapRepository,
        node_repo: IStudyNodeRepository,
        content_repo: INodeContentRepository,
    ) -> None:
        self.map_repo = map_repo
        self.node_repo = node_repo
        self.content_repo = content_repo

    def execute(
        self,
        map_id: UUID,
        user_id: UUID,
        node_id: UUID,
        content_type: str,
        content_id: UUID,
    ) -> None:
        study_map = self.map_repo.get_by_id(map_id)
        if study_map is None:
            raise StudyMapNotFoundError("Mapa não encontrado.")
        if study_map.owner_id != user_id:
            raise ResourceOwnershipError("Sem permissão para alterar conteúdos deste nó.")

        node = self.node_repo.get_by_id(node_id)
        if node is None or node.map_id != map_id:
            raise StudyNodeNotFoundError(f"Nó '{node_id}' não encontrado no mapa.")

        clean_type = content_type.lower().strip()
        if clean_type in ("material", "knowledge_source"):
            self.content_repo.detach_knowledge_source(node_id, content_id)
        elif clean_type in ("question", "open_question"):
            self.content_repo.detach_question(node_id, content_id)
        elif clean_type in ("flashcard",):
            self.content_repo.detach_flashcard(node_id, content_id)
        else:
            raise DomainValidationError(
                f"Tipo de conteúdo inválido para desvinculação: '{content_type}'."
            )


class GetNodeStudyHubUseCase:
    """Caso de uso para carregar os conteúdos de estudo de um nó."""

    def __init__(
        self,
        map_repo: IStudyMapRepository,
        node_repo: IStudyNodeRepository,
        content_repo: INodeContentRepository,
        progress_repo: IQuestionProgressRepository,
        question_repo: IQuestionRepository | None = None,
        knowledge_repo: IKnowledgeSourceRepository | None = None,
        flashcard_repo: IFlashcardRepository | None = None,
    ) -> None:
        self.map_repo = map_repo
        self.node_repo = node_repo
        self.content_repo = content_repo
        self.progress_repo = progress_repo
        self.question_repo = question_repo
        self.knowledge_repo = knowledge_repo
        self.flashcard_repo = flashcard_repo

    def execute(self, map_id: UUID, user_id: UUID, node_id: UUID) -> NodeStudyHubDTO:
        study_map = self.map_repo.get_by_id(map_id)
        if study_map is None:
            raise StudyMapNotFoundError(f"Mapa de estudo '{map_id}' não encontrado.")
        if study_map.owner_id != user_id and not study_map.is_public:
            raise ResourceOwnershipError("Sem permissão para acessar os conteúdos deste nó.")

        node = self.node_repo.get_by_id(node_id)
        if node is None or node.map_id != map_id:
            raise StudyNodeNotFoundError(f"Nó '{node_id}' não encontrado no mapa.")

        mat_ids, q_ids, f_ids = self.content_repo.get_attached_ids(node_id)
        today = date.today()

        progress_map = self.progress_repo.get_by_questions(user_id, q_ids) if q_ids else {}
        srs_levels = [
            progress_map[qid].current_level if qid in progress_map else 0 for qid in q_ids
        ]
        effective_level = StudyTreeProgressionService.calculate_node_level(srs_levels)
        overdue_count = sum(
            1
            for qid in q_ids
            if qid in progress_map and progress_map[qid].next_review_date <= today
        )

        node_dto = StudyNodeDTO(
            id=node.id,
            map_id=node.map_id,
            title=node.title,
            description=node.description,
            pos_x=node.pos_x,
            pos_y=node.pos_y,
            icon=node.icon,
            effective_level=effective_level,
            is_unlocked=True,
            overdue_questions_count=overdue_count,
            has_submap=False,
            materials_count=len(mat_ids),
            questions_count=len(q_ids),
            flashcards_count=len(f_ids),
        )

        all_questions_list: list[dict[str, object]] = []
        due_questions_list: list[dict[str, object]] = []
        if self.question_repo is not None and q_ids:
            for qid in q_ids:
                q = self.question_repo.get_by_id(qid)
                if q:
                    prog = progress_map.get(qid)
                    cur_lvl = prog.current_level if prog else 0
                    nxt_dt = prog.next_review_date.isoformat() if prog else today.isoformat()
                    item = {
                        "id": str(q.id),
                        "prompt": q.prompt,
                        "expected_answer": q.expected_answer,
                        "current_level": cur_lvl,
                        "next_review_date": nxt_dt,
                    }
                    all_questions_list.append(item)
                    if prog is None or prog.next_review_date <= today:
                        due_questions_list.append(item)

        materials_list: list[dict[str, object]] = []
        if self.knowledge_repo is not None and mat_ids:
            for mid in mat_ids:
                m = self.knowledge_repo.get_by_id(mid)
                if m:
                    materials_list.append(
                        {
                            "id": str(m.id),
                            "title": m.title,
                            "content_type": m.content_type,
                        }
                    )

        flashcards_list: list[dict[str, object]] = []
        if self.flashcard_repo is not None and f_ids:
            for fid in f_ids:
                fc = self.flashcard_repo.get_by_id(fid)
                if fc:
                    flashcards_list.append(
                        {
                            "id": str(fc.id),
                            "front": fc.front,
                            "back": fc.back,
                        }
                    )

        return NodeStudyHubDTO(
            node=node_dto,
            materials=materials_list,
            due_questions=due_questions_list,
            all_questions=all_questions_list,
            flashcards=flashcards_list,
        )
