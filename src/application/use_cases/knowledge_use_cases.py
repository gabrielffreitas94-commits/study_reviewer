"""Casos de uso para gestão da base de conhecimento e validação factual via RAG (Sprint 07)."""

from uuid import UUID

import nh3

from src.application.dto.knowledge_dto import (
    CreateKnowledgeSourceRequest,
    KnowledgeSourceResponse,
    ValidateQuestionWithKnowledgeRequest,
    ValidationResultResponse,
)
from src.application.ports.repositories import (
    IKnowledgeChunkRepository,
    IKnowledgeSourceRepository,
    ISubjectRepository,
    ITopicRepository,
)
from src.domain.entities import KnowledgeChunk, KnowledgeSource, ValidationResult
from src.domain.exceptions import (
    EmptyKnowledgeContentError,
    EntityNotFoundError,
    KnowledgeSourceNotFoundError,
    ResourceOwnershipError,
)
from src.domain.protocols import IEmbeddingService, IKnowledgeValidationService
from src.domain.services import SemanticChunkerService


class IngestKnowledgeSourceUseCase:
    """Caso de uso para ingestão, sanitização, chunking e vetorização de materiais didáticos."""

    def __init__(
        self,
        source_repo: IKnowledgeSourceRepository,
        chunk_repo: IKnowledgeChunkRepository,
        topic_repo: ITopicRepository,
        subject_repo: ISubjectRepository,
        embedding_service: IEmbeddingService,
    ) -> None:
        self._source_repo = source_repo
        self._chunk_repo = chunk_repo
        self._topic_repo = topic_repo
        self._subject_repo = subject_repo
        self._embedding_service = embedding_service

    async def execute(
        self,
        user_id: UUID,
        topic_id: UUID,
        request: CreateKnowledgeSourceRequest,
    ) -> KnowledgeSourceResponse:
        topic = self._topic_repo.get_by_id(topic_id)
        if not topic:
            raise EntityNotFoundError("Tema não encontrado.")

        subject = self._subject_repo.get_by_id(topic.subject_id)
        if not subject or not subject.can_be_edited_by(user_id):
            raise ResourceOwnershipError(
                "Apenas o proprietário da matéria pode cadastrar materiais didáticos."
            )

        # Sanitização defensiva do conteúdo
        cleaned_content = nh3.clean(request.content.strip(), tags=set()).strip()
        if len(cleaned_content) < 20:
            raise EmptyKnowledgeContentError(
                "O conteúdo do material deve ter pelo menos 20 caracteres úteis."
            )

        # Chunking semântico
        chunk_texts = SemanticChunkerService.chunk_text(cleaned_content)

        # Vetorização em lote via serviço de embedding
        embeddings = await self._embedding_service.generate_embeddings_batch(chunk_texts)

        # Criação da entidade fonte
        source = KnowledgeSource(
            topic_id=topic_id,
            title=request.title,
            content_type=request.content_type,
            total_chunks=len(chunk_texts),
            char_count=len(cleaned_content),
        )
        saved_source = self._source_repo.save(source)

        # Criação e persistência dos chunks
        chunks = [
            KnowledgeChunk(
                source_id=saved_source.id,
                topic_id=topic_id,
                chunk_index=idx,
                content=txt,
                embedding=tuple(emb),
                token_estimate=max(1, len(txt) // 4),
            )
            for idx, (txt, emb) in enumerate(zip(chunk_texts, embeddings, strict=True))
        ]
        self._chunk_repo.save_batch(chunks)

        return KnowledgeSourceResponse(
            id=saved_source.id,
            topic_id=saved_source.topic_id,
            title=saved_source.title,
            content_type=saved_source.content_type,
            total_chunks=saved_source.total_chunks,
            char_count=saved_source.char_count,
            created_at=saved_source.created_at.isoformat(),
        )


class GetTopicKnowledgeSourcesUseCase:
    """Caso de uso para listagem dos materiais didáticos cadastrados em um tema."""

    def __init__(
        self,
        source_repo: IKnowledgeSourceRepository,
        topic_repo: ITopicRepository,
        subject_repo: ISubjectRepository,
    ) -> None:
        self._source_repo = source_repo
        self._topic_repo = topic_repo
        self._subject_repo = subject_repo

    async def execute(
        self,
        user_id: UUID,
        topic_id: UUID,
    ) -> list[KnowledgeSourceResponse]:
        topic = self._topic_repo.get_by_id(topic_id)
        if not topic:
            raise EntityNotFoundError("Tema não encontrado.")

        subject = self._subject_repo.get_by_id(topic.subject_id)
        if not subject or not subject.can_be_studied_by(user_id):
            raise ResourceOwnershipError("Sem permissão para visualizar o tema.")

        sources = self._source_repo.list_by_topic(topic_id)
        return [
            KnowledgeSourceResponse(
                id=s.id,
                topic_id=s.topic_id,
                title=s.title,
                content_type=s.content_type,
                total_chunks=s.total_chunks,
                char_count=s.char_count,
                created_at=s.created_at.isoformat(),
            )
            for s in sources
        ]


class DeleteKnowledgeSourceUseCase:
    """Caso de uso para remoção de uma fonte e cascata de chunks."""

    def __init__(
        self,
        source_repo: IKnowledgeSourceRepository,
        chunk_repo: IKnowledgeChunkRepository,
        topic_repo: ITopicRepository,
        subject_repo: ISubjectRepository,
    ) -> None:
        self._source_repo = source_repo
        self._chunk_repo = chunk_repo
        self._topic_repo = topic_repo
        self._subject_repo = subject_repo

    async def execute(self, user_id: UUID, source_id: UUID) -> None:
        source = self._source_repo.get_by_id(source_id)
        if not source:
            raise KnowledgeSourceNotFoundError("Fonte de conhecimento não encontrada.")

        topic = self._topic_repo.get_by_id(source.topic_id)
        if not topic:
            raise EntityNotFoundError("Tema não encontrado.")

        subject = self._subject_repo.get_by_id(topic.subject_id)
        if not subject or not subject.can_be_edited_by(user_id):
            raise ResourceOwnershipError("Apenas o proprietário pode excluir materiais didáticos.")

        self._chunk_repo.delete_by_source(source_id)
        self._source_repo.delete(source_id)


class ValidateQuestionWithKnowledgeUseCase:
    """Caso de uso para validação factual de enunciado e gabarito via RAG."""

    def __init__(
        self,
        chunk_repo: IKnowledgeChunkRepository,
        topic_repo: ITopicRepository,
        subject_repo: ISubjectRepository,
        embedding_service: IEmbeddingService,
        validation_service: IKnowledgeValidationService,
    ) -> None:
        self._chunk_repo = chunk_repo
        self._topic_repo = topic_repo
        self._subject_repo = subject_repo
        self._embedding_service = embedding_service
        self._validation_service = validation_service

    async def execute(
        self,
        user_id: UUID,
        topic_id: UUID,
        request: ValidateQuestionWithKnowledgeRequest,
    ) -> ValidationResultResponse:
        topic = self._topic_repo.get_by_id(topic_id)
        if not topic:
            raise EntityNotFoundError("Tema não encontrado.")

        subject = self._subject_repo.get_by_id(topic.subject_id)
        if not subject or not subject.can_be_studied_by(user_id):
            raise ResourceOwnershipError("Sem permissão para consultar o tema.")

        query_text = f"{request.prompt.strip()}\n{request.expected_answer.strip()}"
        query_embedding = await self._embedding_service.generate_embedding(query_text)

        similar_chunks = self._chunk_repo.search_similar(
            topic_id=topic_id,
            query_embedding=query_embedding,
            top_k=5,
        )

        if not similar_chunks:
            return ValidationResultResponse(
                is_grounded=False,
                confidence_score=0.0,
                evidence_chunk_ids=[],
                evidence_quotes=[],
                reasoning="Nenhum material de conhecimento cadastrado no tema para validação.",
                suggested_improvements=["Cadastre livros ou resumos no tema para auditoria de IA."],
            )

        context_chunks = [chunk for chunk, _ in similar_chunks]
        result: ValidationResult = await self._validation_service.validate_question_grounding(
            prompt=request.prompt,
            expected_answer=request.expected_answer,
            context_chunks=context_chunks,
        )

        return ValidationResultResponse(
            is_grounded=result.is_grounded,
            confidence_score=result.confidence_score,
            evidence_chunk_ids=[str(cid) for cid in result.evidence_chunk_ids],
            evidence_quotes=list(result.evidence_quotes),
            reasoning=result.reasoning,
            suggested_improvements=list(result.suggested_improvements),
        )
