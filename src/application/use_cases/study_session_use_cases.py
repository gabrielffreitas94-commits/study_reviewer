"""Casos de uso para Estudo e Gestão da Pool de Flashcards (Clean Architecture - Camada 2)."""

from src.application.dto.study_dto import GetNextCardDTO, StudyBatchDTO, StudyCardDTO
from src.application.ports.repositories import (
    IFlashcardRepository,
    ISessionRepository,
    ITopicRepository,
)
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
        topic_repo: ITopicRepository | None = None,
    ) -> None:
        self._card_repo = card_repo
        self._session_repo = session_repo
        self._rng = rng
        self._topic_repo = topic_repo

    def execute(self, input_dto: GetNextCardDTO) -> StudyCardDTO:
        total_cards = self._card_repo.count_pool(input_dto.subject_id, input_dto.topic_id)
        if total_cards == 0:
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

        # Busca paginada dos próximos 100 cards a partir da posição atual da sessão
        upcoming = self._card_repo.list_pool(
            input_dto.subject_id,
            input_dto.topic_id,
            limit=100,
            min_position=session.current_position,
        )

        round_shuffled = False
        if not upcoming:
            # Fim de rodada: carrega os cards da pool para embaralhamento da nova bateria
            all_cards = self._card_repo.list_pool(input_dto.subject_id, input_dto.topic_id)
            shuffled = FlashcardPoolService.execute_round_shuffle(all_cards, self._rng)
            self._card_repo.save_all(shuffled)
            session.next_round(initial_position=shuffled[0].position)
            next_card = shuffled[0]
            round_shuffled = True
            current_index = 1
        else:
            next_card = upcoming[0]
            session.advance_to(next_card.position)
            all_cards = self._card_repo.list_pool(input_dto.subject_id, input_dto.topic_id)
            current_index = 1
            for idx, c in enumerate(all_cards):
                if c.id == next_card.id:
                    current_index = idx + 1
                    break

        self._session_repo.save_session(session)

        topic_names: list[str] = []
        if self._topic_repo is not None:
            for t_id in next_card.topic_ids:
                t = self._topic_repo.get_by_id(t_id)
                if t:
                    topic_names.append(t.name)

        return StudyCardDTO(
            id=next_card.id,
            front=next_card.front,
            back=next_card.back,
            position=next_card.position,
            current_index=current_index,
            total_cards=total_cards,
            round_number=session.round_number,
            round_shuffled=round_shuffled,
            topic_ids=list(next_card.topic_ids),
            topic_names=topic_names,
            topic_id=next_card.primary_topic_id,
        )


class GetCurrentStudyCardUseCase:
    """Caso de uso para obter o flashcard atual da sessão de estudo sem avançar."""

    def __init__(
        self,
        card_repo: IFlashcardRepository,
        session_repo: ISessionRepository,
        topic_repo: ITopicRepository | None = None,
    ) -> None:
        self._card_repo = card_repo
        self._session_repo = session_repo
        self._topic_repo = topic_repo

    def execute(self, input_dto: GetNextCardDTO) -> StudyCardDTO:
        cards = self._card_repo.list_pool(input_dto.subject_id, input_dto.topic_id)
        if not cards:
            raise EmptyPoolError(
                "Nenhum flashcard disponível para estudo com os filtros selecionados."
            )

        session = self._session_repo.get_active_session(input_dto.subject_id, input_dto.topic_id)
        if session is None:
            first_card = cards[0]
            session = FlashcardPoolSession(
                subject_id_filter=input_dto.subject_id,
                topic_id_filter=input_dto.topic_id,
                current_position=first_card.position,
                round_number=1,
            )
            self._session_repo.save_session(session)
            active_card = first_card
        else:
            matching_card = next((c for c in cards if c.position == session.current_position), None)
            if matching_card is not None:
                active_card = matching_card
            else:
                fallback_card = next(
                    (c for c in cards if c.position >= session.current_position), cards[0]
                )
                session.advance_to(fallback_card.position)
                self._session_repo.save_session(session)
                active_card = fallback_card

        current_index = 1
        for idx, c in enumerate(cards):
            if c.id == active_card.id:
                current_index = idx + 1
                break

        topic_names: list[str] = []
        if self._topic_repo is not None:
            for t_id in active_card.topic_ids:
                t = self._topic_repo.get_by_id(t_id)
                if t:
                    topic_names.append(t.name)

        return StudyCardDTO(
            id=active_card.id,
            front=active_card.front,
            back=active_card.back,
            position=active_card.position,
            current_index=current_index,
            total_cards=len(cards),
            round_number=session.round_number,
            round_shuffled=False,
            topic_ids=list(active_card.topic_ids),
            topic_names=topic_names,
            topic_id=active_card.primary_topic_id,
        )


class GetStudyBatchUseCase:
    """Caso de uso para carregar cards em lotes de 100 para o frontend reduzir requisições."""

    def __init__(
        self,
        card_repo: IFlashcardRepository,
        session_repo: ISessionRepository,
        topic_repo: ITopicRepository | None = None,
    ) -> None:
        self._card_repo = card_repo
        self._session_repo = session_repo
        self._topic_repo = topic_repo

    def execute(self, input_dto: GetNextCardDTO, limit: int = 100) -> StudyBatchDTO:
        total_cards = self._card_repo.count_pool(input_dto.subject_id, input_dto.topic_id)
        if total_cards == 0:
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
            self._session_repo.save_session(session)

        # Busca lote de até 100 cards após a posição atual da sessão
        cards = self._card_repo.list_pool(
            input_dto.subject_id,
            input_dto.topic_id,
            limit=limit,
            min_position=session.current_position,
        )

        # Se não houver cards restantes nesta rodada, busca do início
        if not cards:
            cards = self._card_repo.list_pool(
                input_dto.subject_id,
                input_dto.topic_id,
                limit=limit,
            )

        card_dtos: list[StudyCardDTO] = []
        for idx, card in enumerate(cards):
            topic_names: list[str] = []
            if self._topic_repo is not None:
                for t_id in card.topic_ids:
                    t = self._topic_repo.get_by_id(t_id)
                    if t:
                        topic_names.append(t.name)

            card_dtos.append(
                StudyCardDTO(
                    id=card.id,
                    front=card.front,
                    back=card.back,
                    position=card.position,
                    current_index=idx + 1,
                    total_cards=total_cards,
                    round_number=session.round_number,
                    round_shuffled=False,
                    topic_ids=list(card.topic_ids),
                    topic_names=topic_names,
                    topic_id=card.primary_topic_id,
                )
            )

        return StudyBatchDTO(
            cards=card_dtos,
            total_cards=total_cards,
            round_number=session.round_number,
            has_more=len(cards) == limit,
        )
