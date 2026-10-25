"""Caso de Uso para Migração da Taxonomia Legada (Matérias e Temas) para Árvores de Estudo RPG."""

from dataclasses import dataclass
from uuid import UUID

from src.application.ports.repositories import (
    IFlashcardRepository,
    IKnowledgeSourceRepository,
    INodeContentRepository,
    IQuestionRepository,
    IStudyMapRepository,
    IStudyNodeRepository,
    ISubjectRepository,
    ITopicRepository,
)
from src.domain.entities import StudyMap, StudyNode


@dataclass(frozen=True, slots=True)
class MigrationReportDTO:
    """Relatório da migração de taxonomia legada para árvores RPG."""

    maps_created: int
    nodes_created: int
    questions_linked: int
    flashcards_linked: int
    sources_linked: int


class MigrateLegacyTaxonomyUseCase:
    """Converte Matérias (Subjects) em Mapas de Estudo e Temas (Topics) em Nós de Estudo RPG."""

    def __init__(
        self,
        subject_repo: ISubjectRepository,
        topic_repo: ITopicRepository,
        map_repo: IStudyMapRepository,
        node_repo: IStudyNodeRepository,
        content_repo: INodeContentRepository,
        question_repo: IQuestionRepository,
        flashcard_repo: IFlashcardRepository,
        knowledge_source_repo: IKnowledgeSourceRepository,
    ) -> None:
        self._subject_repo = subject_repo
        self._topic_repo = topic_repo
        self._map_repo = map_repo
        self._node_repo = node_repo
        self._content_repo = content_repo
        self._question_repo = question_repo
        self._flashcard_repo = flashcard_repo
        self._knowledge_source_repo = knowledge_source_repo

    def execute(self, user_id: UUID) -> MigrationReportDTO:
        subjects = self._subject_repo.list_by_owner(user_id)
        existing_maps = self._map_repo.list_by_owner(user_id)
        existing_map_titles = {m.title.lower(): m for m in existing_maps}

        maps_created = 0
        nodes_created = 0
        questions_linked = 0
        flashcards_linked = 0
        sources_linked = 0

        for subject in subjects:
            # Reutiliza mapa se já existir com mesmo título, ou cria novo
            title_key = subject.name.lower().strip()
            if title_key in existing_map_titles:
                study_map = existing_map_titles[title_key]
            else:
                study_map = self._map_repo.save(
                    StudyMap(
                        owner_id=user_id,
                        title=subject.name,
                        description=f"Mapa importado da matéria {subject.name}",
                        is_public=subject.is_public,
                    )
                )
                existing_map_titles[title_key] = study_map
                maps_created += 1

            # Busca nós existentes para evitar duplicatas
            existing_nodes = self._node_repo.list_by_map(study_map.id)
            existing_node_titles = {n.title.lower(): n for n in existing_nodes}

            topics = self._topic_repo.list_by_subject(subject.id)
            for idx, topic in enumerate(topics):
                topic_key = topic.name.lower().strip()
                if topic_key in existing_node_titles:
                    node = existing_node_titles[topic_key]
                else:
                    # Layout em grade fluida para o canvas RPG
                    pos_x = (idx % 4) * 260.0 + 100.0
                    pos_y = (idx // 4) * 200.0 + 120.0
                    node = self._node_repo.save(
                        StudyNode(
                            map_id=study_map.id,
                            title=topic.name,
                            description=f"Tópico importado: {topic.name}",
                            pos_x=pos_x,
                            pos_y=pos_y,
                            icon="brain",
                        )
                    )
                    existing_node_titles[topic_key] = node
                    nodes_created += 1

                # Vincula conteúdos do tópico ao nó
                questions = self._question_repo.list_by_topic(topic.id)
                for q in questions:
                    self._content_repo.attach_question(node.id, q.id)
                    questions_linked += 1

                flashcards = self._flashcard_repo.list_pool(
                    subject_id=subject.id, topic_id=topic.id
                )
                for fc in flashcards:
                    self._content_repo.attach_flashcard(node.id, fc.id)
                    flashcards_linked += 1

                sources = self._knowledge_source_repo.list_by_topic(topic.id)
                for src in sources:
                    self._content_repo.attach_knowledge_source(node.id, src.id)
                    sources_linked += 1

        return MigrationReportDTO(
            maps_created=maps_created,
            nodes_created=nodes_created,
            questions_linked=questions_linked,
            flashcards_linked=flashcards_linked,
            sources_linked=sources_linked,
        )
