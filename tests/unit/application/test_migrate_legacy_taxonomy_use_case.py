"""Testes unitários para o Caso de Uso de Migração de Taxonomia Legada para Árvore RPG."""

from unittest.mock import MagicMock
from uuid import uuid4

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
from src.application.use_cases.migrate_legacy_taxonomy_use_case import (
    MigrateLegacyTaxonomyUseCase,
)
from src.domain.entities import (
    Flashcard,
    KnowledgeSource,
    Question,
    StudyMap,
    StudyNode,
    Subject,
    Topic,
)


class TestMigrateLegacyTaxonomyUseCase:
    def test_migrate_subjects_and_topics_successfully(self) -> None:
        user_id = uuid4()

        subject_repo = MagicMock(spec=ISubjectRepository)
        topic_repo = MagicMock(spec=ITopicRepository)
        map_repo = MagicMock(spec=IStudyMapRepository)
        node_repo = MagicMock(spec=IStudyNodeRepository)
        content_repo = MagicMock(spec=INodeContentRepository)
        question_repo = MagicMock(spec=IQuestionRepository)
        flashcard_repo = MagicMock(spec=IFlashcardRepository)
        knowledge_source_repo = MagicMock(spec=IKnowledgeSourceRepository)

        # Configura matéria e tópico com perguntas e flashcards
        subject = Subject(id=uuid4(), name="Arquitetura de Software", owner_id=user_id)
        topic = Topic(id=uuid4(), subject_id=subject.id, name="Clean Architecture")

        q1 = Question(
            id=uuid4(),
            topic_id=topic.id,
            prompt="O que é a regra da dependência?",
            expected_answer="Dependências apontam para dentro",
        )
        fc1 = Flashcard(
            id=uuid4(),
            topic_id=topic.id,
            front="Entidades",
            back="Regras de negócio corporativas",
        )
        src1 = KnowledgeSource(
            id=uuid4(),
            title="Livro Clean Arch",
            topic_ids=(topic.id,),
        )

        subject_repo.list_by_owner.return_value = [subject]
        map_repo.list_by_owner.return_value = []
        map_repo.save.side_effect = lambda m: m
        node_repo.list_by_map.return_value = []
        node_repo.save.side_effect = lambda n: n
        topic_repo.list_by_subject.return_value = [topic]

        question_repo.list_by_topic.return_value = [q1]
        flashcard_repo.list_pool.return_value = [fc1]
        knowledge_source_repo.list_by_topic.return_value = [src1]

        use_case = MigrateLegacyTaxonomyUseCase(
            subject_repo=subject_repo,
            topic_repo=topic_repo,
            map_repo=map_repo,
            node_repo=node_repo,
            content_repo=content_repo,
            question_repo=question_repo,
            flashcard_repo=flashcard_repo,
            knowledge_source_repo=knowledge_source_repo,
        )

        report = use_case.execute(user_id=user_id)

        assert report.maps_created == 1
        assert report.nodes_created == 1
        assert report.questions_linked == 1
        assert report.flashcards_linked == 1
        assert report.sources_linked == 1

        map_repo.save.assert_called_once()
        node_repo.save.assert_called_once()
        content_repo.attach_question.assert_called_once_with(
            node_repo.save.call_args[0][0].id, q1.id
        )
        content_repo.attach_flashcard.assert_called_once_with(
            node_repo.save.call_args[0][0].id, fc1.id
        )
        content_repo.attach_knowledge_source.assert_called_once_with(
            node_repo.save.call_args[0][0].id, src1.id
        )

    def test_idempotent_when_maps_and_nodes_already_exist(self) -> None:
        user_id = uuid4()

        subject_repo = MagicMock(spec=ISubjectRepository)
        topic_repo = MagicMock(spec=ITopicRepository)
        map_repo = MagicMock(spec=IStudyMapRepository)
        node_repo = MagicMock(spec=IStudyNodeRepository)
        content_repo = MagicMock(spec=INodeContentRepository)
        question_repo = MagicMock(spec=IQuestionRepository)
        flashcard_repo = MagicMock(spec=IFlashcardRepository)
        knowledge_source_repo = MagicMock(spec=IKnowledgeSourceRepository)

        subject = Subject(id=uuid4(), name="Matemática", owner_id=user_id)
        topic = Topic(id=uuid4(), subject_id=subject.id, name="Álgebra Linear")

        existing_map = StudyMap(id=uuid4(), owner_id=user_id, title="Matemática")
        existing_node = StudyNode(id=uuid4(), map_id=existing_map.id, title="Álgebra Linear")

        subject_repo.list_by_owner.return_value = [subject]
        map_repo.list_by_owner.return_value = [existing_map]
        node_repo.list_by_map.return_value = [existing_node]
        topic_repo.list_by_subject.return_value = [topic]

        question_repo.list_by_topic.return_value = []
        flashcard_repo.list_pool.return_value = []
        knowledge_source_repo.list_by_topic.return_value = []

        use_case = MigrateLegacyTaxonomyUseCase(
            subject_repo=subject_repo,
            topic_repo=topic_repo,
            map_repo=map_repo,
            node_repo=node_repo,
            content_repo=content_repo,
            question_repo=question_repo,
            flashcard_repo=flashcard_repo,
            knowledge_source_repo=knowledge_source_repo,
        )

        report = use_case.execute(user_id=user_id)

        assert report.maps_created == 0
        assert report.nodes_created == 0
        map_repo.save.assert_not_called()
        node_repo.save.assert_not_called()
