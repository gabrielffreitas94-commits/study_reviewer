"""Casos de uso para a Árvore de Estudos RPG (Clean Architecture - Camada 2)."""

from datetime import UTC, date, datetime
from typing import Any
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
    UpdateStudyEdgeDTO,
    UpdateStudyNodeDTO,
)
from src.application.ports.repositories import (
    IClockService,
    IFlashcardRepository,
    IKnowledgeSourceRepository,
    INodeContentRepository,
    IQuestionProgressRepository,
    IQuestionRepository,
    IReviewAuditRepository,
    IStudyEdgeRepository,
    IStudyMapRepository,
    IStudyNodeRepository,
)
from src.domain.entities import (
    KnowledgeSource,
    Question,
    ReviewAuditLog,
    StudyEdge,
    StudyMap,
    StudyNode,
    UserQuestionProgress,
)
from src.domain.exceptions import (
    DomainValidationError,
    EntityNotFoundError,
    QuestionNotFoundError,
    ResourceOwnershipError,
    StudyEdgeNotFoundError,
    StudyMapNotFoundError,
    StudyNodeNotFoundError,
)
from src.domain.services import (
    DAGValidatorService,
    SpacingPolicyService,
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
                    theory_content=node.theory_content,
                )
            )

        edge_dtos = [
            StudyEdgeDTO(
                id=e.id,
                map_id=e.map_id,
                source_node_id=e.source_node_id,
                target_node_id=e.target_node_id,
                required_level=e.required_level,
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
            theory_content=dto.theory_content,
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
            theory_content=saved.theory_content,
        )


class UpdateStudyNodeUseCase:
    """Caso de uso para atualização de dados (título, descrição, ícone, teoria) de um nó."""

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
        if dto.theory_content is not None:
            node.update_theory(dto.theory_content)

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
            theory_content=saved.theory_content,
        )


class UpdateNodeTheoryUseCase:
    """Caso de uso para atualizar o texto do Tomo de Sabedoria de um nó."""

    def __init__(
        self,
        map_repo: IStudyMapRepository,
        node_repo: IStudyNodeRepository,
    ) -> None:
        self.map_repo = map_repo
        self.node_repo = node_repo

    def execute(
        self, map_id: UUID, node_id: UUID, user_id: UUID, theory_content: str
    ) -> StudyNodeDTO:
        study_map = self.map_repo.get_by_id(map_id)
        if study_map is None:
            raise StudyMapNotFoundError(f"Mapa de estudo '{map_id}' não encontrado.")
        if study_map.owner_id != user_id:
            raise ResourceOwnershipError("Apenas o proprietário do mapa pode alterar o tomo do nó.")

        node = self.node_repo.get_by_id(node_id)
        if node is None or node.map_id != map_id:
            raise StudyNodeNotFoundError(f"Nó '{node_id}' não encontrado no mapa.")

        node.update_theory(theory_content)
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
            theory_content=saved.theory_content,
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
            required_level=dto.required_level,
        )
        saved = self.edge_repo.save(edge)
        return StudyEdgeDTO(
            id=saved.id,
            map_id=saved.map_id,
            source_node_id=saved.source_node_id,
            target_node_id=saved.target_node_id,
            required_level=saved.required_level,
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


class UpdateStudyEdgeUseCase:
    """Caso de uso para atualizar o nível requerido de uma aresta de pré-requisito."""

    def __init__(
        self,
        map_repo: IStudyMapRepository,
        edge_repo: IStudyEdgeRepository,
    ) -> None:
        self.map_repo = map_repo
        self.edge_repo = edge_repo

    def execute(
        self, map_id: UUID, edge_id: UUID, user_id: UUID, dto: UpdateStudyEdgeDTO
    ) -> StudyEdgeDTO:
        study_map = self.map_repo.get_by_id(map_id)
        if study_map is None:
            raise StudyMapNotFoundError("Mapa não encontrado.")
        if study_map.owner_id != user_id:
            raise ResourceOwnershipError("Sem permissão para alterar dependências deste mapa.")

        edge = self.edge_repo.get_by_id(edge_id)
        if edge is None or edge.map_id != map_id:
            raise StudyEdgeNotFoundError(f"Aresta '{edge_id}' não encontrada no mapa.")

        if not (1 <= dto.required_level <= 6):
            raise DomainValidationError("Nível requerido deve estar entre 1 e 6.")

        edge.required_level = dto.required_level
        saved = self.edge_repo.save(edge)
        return StudyEdgeDTO(
            id=saved.id,
            map_id=saved.map_id,
            source_node_id=saved.source_node_id,
            target_node_id=saved.target_node_id,
            required_level=saved.required_level,
        )


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


class CreateNodeQuestionUseCase:
    """Caso de uso para criação inline de uma pergunta SRS associada a um nó da árvore."""

    def __init__(
        self,
        map_repo: IStudyMapRepository,
        node_repo: IStudyNodeRepository,
        question_repo: IQuestionRepository,
        progress_repo: IQuestionProgressRepository,
        content_repo: INodeContentRepository,
        clock: IClockService | None = None,
    ) -> None:
        self.map_repo = map_repo
        self.node_repo = node_repo
        self.question_repo = question_repo
        self.progress_repo = progress_repo
        self.content_repo = content_repo
        self.clock = clock

    def execute(
        self,
        map_id: UUID,
        node_id: UUID,
        user_id: UUID,
        prompt: str,
        expected_answer: str,
    ) -> dict[str, Any]:
        study_map = self.map_repo.get_by_id(map_id)
        if study_map is None:
            raise StudyMapNotFoundError(f"Mapa de estudo '{map_id}' não encontrado.")
        if study_map.owner_id != user_id:
            raise ResourceOwnershipError(
                "Apenas o proprietário do mapa pode criar perguntas neste nó."
            )

        node = self.node_repo.get_by_id(node_id)
        if node is None or node.map_id != map_id:
            raise StudyNodeNotFoundError(f"Nó '{node_id}' não encontrado no mapa.")

        today = self.clock.today() if self.clock is not None else date.today()

        question = Question(
            prompt=prompt,
            expected_answer=expected_answer,
            node_id=node.id,
            topic_ids=(node.id,),
            created_at=today,
        )

        initial_progress = UserQuestionProgress(
            user_id=user_id,
            question_id=question.id,
            current_level=0,
            next_review_date=today,
        )

        self.question_repo.save(question)
        self.content_repo.attach_question(node.id, question.id)
        self.progress_repo.save(initial_progress)

        return {
            "id": question.id,
            "question_id": str(question.id),
            "node_id": node.id,
            "prompt": question.prompt,
            "statement": question.prompt,
            "expected_answer": question.expected_answer,
            "current_level": 0,
            "next_review_date": today.isoformat(),
            "created_at": today.isoformat(),
        }


class DeleteNodeQuestionUseCase:
    """Caso de uso para exclusão de pergunta associada a um nó da árvore."""

    def __init__(
        self,
        map_repo: IStudyMapRepository,
        node_repo: IStudyNodeRepository,
        question_repo: IQuestionRepository,
        content_repo: INodeContentRepository,
    ) -> None:
        self.map_repo = map_repo
        self.node_repo = node_repo
        self.question_repo = question_repo
        self.content_repo = content_repo

    def execute(
        self,
        map_id: UUID,
        node_id: UUID,
        user_id: UUID,
        question_id: UUID,
    ) -> None:
        study_map = self.map_repo.get_by_id(map_id)
        if study_map is None:
            raise StudyMapNotFoundError(f"Mapa de estudo '{map_id}' não encontrado.")
        if study_map.owner_id != user_id:
            raise ResourceOwnershipError(
                "Apenas o proprietário do mapa pode excluir perguntas deste nó."
            )

        node = self.node_repo.get_by_id(node_id)
        if node is None or node.map_id != map_id:
            raise StudyNodeNotFoundError(f"Nó '{node_id}' não encontrado no mapa.")

        question = self.question_repo.get_by_id(question_id)
        if question is None:
            raise QuestionNotFoundError(f"Pergunta '{question_id}' não encontrada.")

        self.content_repo.detach_question(node.id, question_id)
        self.question_repo.delete(question_id)


class CreateNodeMaterialUseCase:
    """Caso de uso para criação inline de material (pergaminho) no nó da árvore."""

    def __init__(
        self,
        map_repo: IStudyMapRepository,
        node_repo: IStudyNodeRepository,
        source_repo: IKnowledgeSourceRepository,
        content_repo: INodeContentRepository,
        clock: IClockService | None = None,
    ) -> None:
        self.map_repo = map_repo
        self.node_repo = node_repo
        self.source_repo = source_repo
        self.content_repo = content_repo
        self.clock = clock

    def execute(
        self,
        map_id: UUID,
        node_id: UUID,
        user_id: UUID,
        title: str,
        raw_text: str,
        content_type: str = "TEXT",
    ) -> dict[str, Any]:
        study_map = self.map_repo.get_by_id(map_id)
        if study_map is None:
            raise StudyMapNotFoundError(f"Mapa de estudo '{map_id}' não encontrado.")
        if study_map.owner_id != user_id:
            raise ResourceOwnershipError(
                "Apenas o proprietário do mapa pode adicionar materiais a este nó."
            )

        node = self.node_repo.get_by_id(node_id)
        if node is None or node.map_id != map_id:
            raise StudyNodeNotFoundError(f"Nó '{node_id}' não encontrado no mapa.")

        today = self.clock.today() if self.clock is not None else date.today()
        clean_text = raw_text.strip() if raw_text else ""

        source = KnowledgeSource(
            title=title,
            content_type=content_type or "TEXT",
            raw_text=clean_text,
            node_id=node.id,
            topic_ids=(node.id,),
            char_count=len(clean_text),
            total_chunks=1 if clean_text else 0,
            created_at=today,
        )

        saved = self.source_repo.save(source)
        self.content_repo.attach_knowledge_source(node.id, saved.id)

        return {
            "id": saved.id,
            "material_id": str(saved.id),
            "node_id": node.id,
            "title": saved.title,
            "content_type": saved.content_type,
            "raw_text": saved.raw_text,
            "char_count": saved.char_count,
            "created_at": today.isoformat(),
        }


class DeleteNodeMaterialUseCase:
    """Caso de uso para remoção de material do nó da árvore."""

    def __init__(
        self,
        map_repo: IStudyMapRepository,
        node_repo: IStudyNodeRepository,
        source_repo: IKnowledgeSourceRepository,
        content_repo: INodeContentRepository,
    ) -> None:
        self.map_repo = map_repo
        self.node_repo = node_repo
        self.source_repo = source_repo
        self.content_repo = content_repo

    def execute(
        self,
        map_id: UUID,
        node_id: UUID,
        user_id: UUID,
        material_id: UUID,
    ) -> None:
        study_map = self.map_repo.get_by_id(map_id)
        if study_map is None:
            raise StudyMapNotFoundError(f"Mapa de estudo '{map_id}' não encontrado.")
        if study_map.owner_id != user_id:
            raise ResourceOwnershipError(
                "Apenas o proprietário do mapa pode excluir materiais deste nó."
            )

        node = self.node_repo.get_by_id(node_id)
        if node is None or node.map_id != map_id:
            raise StudyNodeNotFoundError(f"Nó '{node_id}' não encontrado no mapa.")

        source = self.source_repo.get_by_id(material_id)
        if source is None:
            raise EntityNotFoundError(f"Material '{material_id}' não encontrado.")

        self.content_repo.detach_knowledge_source(node.id, material_id)
        self.source_repo.delete(material_id)


class ReviewNodeQuestionUseCase:
    """Caso de uso para submissão de revisão SRS ancorada no nó com Modo Treino Livre."""

    def __init__(
        self,
        map_repo: IStudyMapRepository,
        node_repo: IStudyNodeRepository,
        question_repo: IQuestionRepository,
        progress_repo: IQuestionProgressRepository,
        content_repo: INodeContentRepository,
        edge_repo: IStudyEdgeRepository | None = None,
        audit_repo: IReviewAuditRepository | None = None,
        clock: IClockService | None = None,
    ) -> None:
        self.map_repo = map_repo
        self.node_repo = node_repo
        self.question_repo = question_repo
        self.progress_repo = progress_repo
        self.content_repo = content_repo
        self.edge_repo = edge_repo
        self.audit_repo = audit_repo
        self.clock = clock

    def execute(
        self,
        map_id: UUID,
        node_id: UUID,
        user_id: UUID,
        question_id: UUID,
        score: int = 100,
        difficulty: str | None = None,
    ) -> dict[str, Any]:
        study_map = self.map_repo.get_by_id(map_id)
        if study_map is None:
            raise StudyMapNotFoundError(f"Mapa de estudo '{map_id}' não encontrado.")
        if study_map.owner_id != user_id and not study_map.is_public:
            raise ResourceOwnershipError("Sem permissão para revisar provações deste mapa.")

        node = self.node_repo.get_by_id(node_id)
        if node is None or node.map_id != map_id:
            raise StudyNodeNotFoundError(f"Nó '{node_id}' não encontrado no mapa.")

        question = self.question_repo.get_by_id(question_id)
        if question is None:
            raise QuestionNotFoundError(f"Pergunta '{question_id}' não encontrada.")

        today = self.clock.today() if self.clock is not None else date.today()
        now = self.clock.now() if self.clock is not None else datetime.now(UTC)

        effective_score = score
        if difficulty is not None and score == 100:
            diff_upper = difficulty.upper().strip()
            if diff_upper in ("EASY", "GOOD", "PERFECT"):
                effective_score = 100
            elif diff_upper == "HARD":
                effective_score = 50
            elif diff_upper == "AGAIN":
                effective_score = 0

        # Coleta todas as perguntas do nó
        _, q_ids, _ = self.content_repo.get_attached_ids(node_id)
        all_node_q_ids = set(q_ids)
        if hasattr(self.question_repo, "list_by_node"):
            for nq in self.question_repo.list_by_node(node_id):
                all_node_q_ids.add(nq.id)
        all_node_q_ids.add(question_id)

        all_q_list = list(all_node_q_ids)
        progress_map = self.progress_repo.get_by_questions(user_id, all_q_list)

        # Nível inicial do nó antes da revisão
        old_levels = [
            progress_map[qid].current_level if qid in progress_map else 0 for qid in all_q_list
        ]
        old_node_level = StudyTreeProgressionService.calculate_node_level(old_levels)

        progress = progress_map.get(question_id)
        if progress is None:
            progress = UserQuestionProgress(
                user_id=user_id,
                question_id=question_id,
                current_level=0,
                next_review_date=today,
            )

        old_q_level = progress.current_level

        # MODO TREINO LIVRE: Quando progress.current_level > 0 e progress.next_review_date > today,
        # nunca lança QuestionNotDueError, não altera banco e retorna is_training_only=True
        is_training_only = progress.current_level > 0 and progress.next_review_date > today

        if is_training_only:
            new_q_level = progress.current_level
            next_date = progress.next_review_date
            interval_days = SpacingPolicyService.get_interval(progress.current_level)
            new_node_level = old_node_level
            leveled_up = False
            unlocked_node_ids: list[UUID] = []
        else:
            new_q_level, next_date = SpacingPolicyService.calculate_next_schedule(
                current_level=progress.current_level,
                score=effective_score,
                review_date=today,
            )
            interval_days = SpacingPolicyService.get_interval(new_q_level)
            progress.apply_review(new_level=new_q_level, next_date=next_date, reviewed_at=now)

            self.progress_repo.save(progress)
            if self.audit_repo is not None:
                audit_log = ReviewAuditLog(
                    user_id=user_id,
                    question_id=question_id,
                    subject_id=None,
                    topic_id=None,
                    historical_subject_name=study_map.title,
                    historical_topic_name=node.title,
                    review_date=today,
                    score=effective_score,
                    level_before=old_q_level,
                    level_after=new_q_level,
                    evaluation_mode="MANUAL",
                    logged_at=now,
                )
                self.audit_repo.save(audit_log)

            # Recalcula níveis das questões do nó
            updated_levels = [
                new_q_level
                if qid == question_id
                else (progress_map[qid].current_level if qid in progress_map else 0)
                for qid in all_q_list
            ]
            new_node_level = StudyTreeProgressionService.calculate_node_level(updated_levels)
            leveled_up = new_node_level > old_node_level

            # Verifica destrancamento de nós dependentes a jusante
            unlocked_node_ids = []
            if self.edge_repo is not None:
                map_edges = self.edge_repo.list_by_map(map_id)
                target_node_ids = [
                    e.target_node_id for e in map_edges if e.source_node_id == node_id
                ]
                if target_node_ids:
                    all_nodes = self.node_repo.list_by_map(map_id)
                    node_levels_before: dict[UUID, int] = {}
                    node_levels_after: dict[UUID, int] = {}
                    for n in all_nodes:
                        if n.id == node_id:
                            node_levels_before[n.id] = old_node_level
                            node_levels_after[n.id] = new_node_level
                        else:
                            _, n_q_ids, _ = self.content_repo.get_attached_ids(n.id)
                            if n_q_ids:
                                n_prog_map = self.progress_repo.get_by_questions(user_id, n_q_ids)
                                lvl = StudyTreeProgressionService.calculate_node_level(
                                    [
                                        n_prog_map[qid].current_level if qid in n_prog_map else 0
                                        for qid in n_q_ids
                                    ]
                                )
                            else:
                                lvl = 0
                            node_levels_before[n.id] = lvl
                            node_levels_after[n.id] = lvl

                    for tid in target_node_ids:
                        inc_edges = [e for e in map_edges if e.target_node_id == tid]
                        unlocked_before = StudyTreeProgressionService.evaluate_unlock_status(
                            inc_edges, node_levels_before
                        )
                        unlocked_after = StudyTreeProgressionService.evaluate_unlock_status(
                            inc_edges, node_levels_after
                        )
                        if not unlocked_before and unlocked_after:
                            unlocked_node_ids.append(tid)

        current_levels_for_percent = [
            new_q_level
            if qid == question_id
            else (progress_map[qid].current_level if qid in progress_map else 0)
            for qid in all_q_list
        ]
        mastered_count = sum(1 for lvl in current_levels_for_percent if lvl >= 1)
        node_progress_percent = (
            round((mastered_count / len(current_levels_for_percent)) * 100, 1)
            if current_levels_for_percent
            else 0.0
        )

        return {
            "question_id": str(question_id),
            "id": question_id,
            "previous_level": old_q_level,
            "new_level": new_q_level,
            "current_question_level": new_q_level,
            "next_review_date": (
                next_date.isoformat() if hasattr(next_date, "isoformat") else str(next_date)
            ),
            "interval_days": interval_days,
            "is_promoted": new_q_level > old_q_level,
            "is_training_only": is_training_only,
            "old_node_level": old_node_level,
            "new_node_level": new_node_level,
            "node_effective_level": new_node_level,
            "leveled_up": leveled_up,
            "node_is_mastered": new_node_level >= 1,
            "node_progress_percent": node_progress_percent,
            "unlocked_node_ids": [str(uid) for uid in unlocked_node_ids],
        }


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

        # Coleta todas as perguntas (content_repo + vinculação direta) sem duplicatas
        all_q_ids_set = set(q_ids)
        if self.question_repo is not None and hasattr(self.question_repo, "list_by_node"):
            for q in self.question_repo.list_by_node(node_id):
                all_q_ids_set.add(q.id)
        all_q_ids = list(all_q_ids_set)

        # Coleta todos os materiais (content_repo + vinculação direta) sem duplicatas
        all_mat_ids_set = set(mat_ids)
        if self.knowledge_repo is not None and hasattr(self.knowledge_repo, "list_by_node"):
            for m in self.knowledge_repo.list_by_node(node_id):
                all_mat_ids_set.add(m.id)
        all_mat_ids = list(all_mat_ids_set)

        progress_map = self.progress_repo.get_by_questions(user_id, all_q_ids) if all_q_ids else {}
        srs_levels = [
            progress_map[qid].current_level if qid in progress_map else 0 for qid in all_q_ids
        ]
        effective_level = StudyTreeProgressionService.calculate_node_level(srs_levels)
        overdue_count = sum(
            1
            for qid in all_q_ids
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
            materials_count=len(all_mat_ids),
            questions_count=len(all_q_ids),
            flashcards_count=len(f_ids),
            theory_content=node.theory_content,
        )

        all_questions_list: list[dict[str, object]] = []
        due_questions_list: list[dict[str, object]] = []
        if self.question_repo is not None and all_q_ids:
            for qid in all_q_ids:
                q_obj = self.question_repo.get_by_id(qid)
                if q_obj is not None:
                    q = q_obj
                    prog = progress_map.get(qid)
                    cur_lvl = prog.current_level if prog else 0
                    nxt_dt = prog.next_review_date.isoformat() if prog else today.isoformat()
                    is_due = prog is None or prog.next_review_date <= today
                    item = {
                        "id": str(q.id),
                        "prompt": q.prompt,
                        "statement": q.prompt,
                        "expected_answer": q.expected_answer,
                        "current_level": cur_lvl,
                        "next_review_date": nxt_dt,
                        "is_due": is_due,
                        "difficulty": "GOOD",
                    }
                    all_questions_list.append(item)
                    if is_due:
                        due_questions_list.append(item)

        materials_list: list[dict[str, object]] = []
        if self.knowledge_repo is not None and all_mat_ids:
            for mid in all_mat_ids:
                m_obj = self.knowledge_repo.get_by_id(mid)
                if m_obj is not None:
                    m = m_obj
                    materials_list.append(
                        {
                            "id": str(m.id),
                            "title": m.title,
                            "content_type": m.content_type,
                            "raw_text": m.raw_text,
                            "char_count": m.char_count,
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
