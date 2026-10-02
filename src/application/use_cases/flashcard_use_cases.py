"""Casos de uso para Flashcards (Clean Architecture - Camada 2)."""

from uuid import UUID

from src.application.dto.flashcard_dto import CreateFlashcardDTO, FlashcardDTO
from src.application.ports.repositories import (
    IFlashcardRepository,
    ISessionRepository,
    ITopicRepository,
)
from src.domain.entities import Flashcard
from src.domain.exceptions import DomainValidationError, EntityNotFoundError
from src.domain.protocols import IRandomGenerator
from src.domain.services import FlashcardPoolService


class CreateFlashcardUseCase:
    """Caso de uso para criação de flashcard com Gap Indexing nos primeiros 10%."""

    def __init__(
        self,
        card_repo: IFlashcardRepository,
        topic_repo: ITopicRepository,
        session_repo: ISessionRepository,
        rng: IRandomGenerator,
    ) -> None:
        self._card_repo = card_repo
        self._topic_repo = topic_repo
        self._session_repo = session_repo
        self._rng = rng

    def execute(self, input_dto: CreateFlashcardDTO) -> FlashcardDTO:
        target_topic_ids = input_dto.topic_ids or (
            [input_dto.topic_id] if input_dto.topic_id else []
        )
        if not target_topic_ids:
            raise DomainValidationError("Flashcard deve estar associado a pelo menos 1 tema.")

        for t_id in target_topic_ids:
            topic = self._topic_repo.get_by_id(t_id)
            if topic is None:
                raise EntityNotFoundError("Tema não encontrado.")

        primary_topic_id = target_topic_ids[0]
        pool = self._card_repo.list_pool(None, primary_topic_id)
        target_idx = FlashcardPoolService.calculate_target_index(len(pool), self._rng)

        if target_idx == 0:
            prev_pos = None
            next_pos = pool[0].position if pool else None
        elif target_idx >= len(pool):
            prev_pos = pool[-1].position if pool else None
            next_pos = None
        else:
            prev_pos = pool[target_idx - 1].position
            next_pos = pool[target_idx].position

        new_position = FlashcardPoolService.calculate_new_position(prev_pos, next_pos)
        card = Flashcard(
            topic_ids=tuple(target_topic_ids),
            front=input_dto.front,
            back=input_dto.back,
            position=new_position,
        )

        candidate_pool = sorted(pool + [card], key=lambda c: c.position)
        if FlashcardPoolService.needs_rebalance([c.position for c in candidate_pool]):
            rebalanced = FlashcardPoolService.rebalance_positions(candidate_pool)
            self._card_repo.save_all(rebalanced)
            saved_card = next(c for c in rebalanced if c.id == card.id)
            return FlashcardDTO(
                id=saved_card.id,
                front=saved_card.front,
                back=saved_card.back,
                position=saved_card.position,
                created_at=saved_card.created_at,
                topic_ids=list(saved_card.topic_ids),
                topic_id=saved_card.primary_topic_id,
            )

        self._card_repo.save(card)
        return FlashcardDTO(
            id=card.id,
            front=card.front,
            back=card.back,
            position=card.position,
            created_at=card.created_at,
            topic_ids=list(card.topic_ids),
            topic_id=card.primary_topic_id,
        )


class DeleteFlashcardUseCase:
    """Caso de uso para exclusão de flashcard e atualização da sessão ativa."""

    def __init__(
        self,
        card_repo: IFlashcardRepository,
        session_repo: ISessionRepository,
        rng: IRandomGenerator,
    ) -> None:
        self._card_repo = card_repo
        self._session_repo = session_repo
        self._rng = rng

    def execute(self, flashcard_id: UUID) -> None:
        card = self._card_repo.get_by_id(flashcard_id)
        if card is None:
            raise EntityNotFoundError("Flashcard não encontrado.")

        self._card_repo.delete(flashcard_id)

        session = self._session_repo.get_active_session(None, card.topic_id)
        if session is not None and session.current_position == card.position:
            remaining = self._card_repo.list_pool(None, card.topic_id)
            next_card, round_finished = FlashcardPoolService.get_next_card(remaining, card.position)
            if round_finished:
                if remaining:
                    shuffled = FlashcardPoolService.execute_round_shuffle(remaining, self._rng)
                    self._card_repo.save_all(shuffled)
                    session.next_round(initial_position=shuffled[0].position)
                else:
                    session.current_position = 0
            elif next_card is not None:
                session.advance_to(next_card.position)

            self._session_repo.save_session(session)
