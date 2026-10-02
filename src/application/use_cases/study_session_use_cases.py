"""Casos de uso para Estudo e Gestão da Pool de Flashcards (Clean Architecture - Camada 2)."""

from src.application.dto.study_dto import GetNextCardDTO, StudyCardDTO
from src.application.ports.repositories import IFlashcardRepository, ISessionRepository
from src.domain.entities import FlashcardPoolSession
from src.domain.exceptions import EmptyPoolError
from src.domain.protocols import IRandomGenerator
from src.domain.services import FlashcardPoolService


class GetNextFlashcardUseCase:
    """Caso de uso para busca do próximo flashcard da rodada e gestão de ciclos."""

    def __init__(
        self,
        card_repo: IFlashcardRepository,
        session_repo: ISessionRepository,
        rng: IRandomGenerator,
    ) -> None:
        self._card_repo = card_repo
        self._session_repo = session_repo
        self._rng = rng

    def execute(self, input_dto: GetNextCardDTO) -> StudyCardDTO:
        cards = self._card_repo.list_pool(input_dto.subject_id, input_dto.topic_id)
        if not cards:
            raise EmptyPoolError(
                "Nenhum flashcard disponível para estudo com os filtros selecionados."
            )

        session = self._session_repo.get_active_session(input_dto.subject_id, input_dto.topic_id)
        if session is None:
            session = FlashcardPoolSession(
                subject_id_filter=input_dto.subject_id,
                topic_id_filter=input_dto.topic_id,
                current_position=0,
                round_number=1,
            )

        next_card, round_finished = FlashcardPoolService.get_next_card(
            cards, session.current_position
        )
        round_shuffled = False

        if round_finished or next_card is None:
            shuffled = FlashcardPoolService.execute_round_shuffle(cards, self._rng)
            self._card_repo.save_all(shuffled)
            session.next_round(initial_position=shuffled[0].position)
            next_card = shuffled[0]
            round_shuffled = True
            active_cards = shuffled
        else:
            session.advance_to(next_card.position)
            active_cards = cards

        self._session_repo.save_session(session)

        current_index = 1
        for idx, c in enumerate(active_cards):
            if c.id == next_card.id:
                current_index = idx + 1
                break

        return StudyCardDTO(
            id=next_card.id,
            topic_id=next_card.topic_id,
            front=next_card.front,
            back=next_card.back,
            position=next_card.position,
            current_index=current_index,
            total_cards=len(active_cards),
            round_number=session.round_number,
            round_shuffled=round_shuffled,
        )
