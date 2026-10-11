"""Casos de uso para Estudo e Gestão da Pool de Flashcards (Clean Architecture - Camada 2)."""

from uuid import UUID, uuid4

from src.application.dto.study_dto import GetNextCardDTO, StudyBatchDTO, StudyCardDTO
from src.application.ports.repositories import (
    IFlashcardRepository,
    ISessionRepository,
    ISubjectRepository,
    ITopicRepository,
)
from src.domain.entities import FlashcardPoolSession
from src.domain.exceptions import EmptyPoolError, ResourceOwnershipError
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
        subject_repo: ISubjectRepository | None = None,
    ) -> None:
        self._card_repo = card_repo
        self._session_repo = session_repo
        self._rng = rng
        self._topic_repo = topic_repo
        self._subject_repo = subject_repo

    def execute(self, input_dto: GetNextCardDTO, user_id: UUID | None = None) -> StudyCardDTO:
        if user_id is not None and self._subject_repo is not None and input_dto.subject_id:
            subject = self._subject_repo.get_by_id(input_dto.subject_id)
            if subject is not None and not subject.can_be_studied_by(user_id):
                raise ResourceOwnershipError("Você não tem acesso a esta matéria privada.")

        all_cards = self._card_repo.list_pool(input_dto.subject_id, input_dto.topic_id)
        total_cards = len(all_cards)
        if total_cards == 0:
            raise EmptyPoolError(
                "Nenhum flashcard disponível para estudo com os filtros selecionados."
            )

        session = self._session_repo.get_active_session(
            input_dto.subject_id, input_dto.topic_id, user_id=user_id
        )
        if session is None:
            session = FlashcardPoolSession(
                user_id=user_id if user_id is not None else uuid4(),
                subject_id=input_dto.subject_id,
                topic_id_filter=input_dto.topic_id,
                current_position=0,
                round_number=1,
                current_index=0,
                card_queue=[c.id for c in all_cards],
            )
        elif not session.card_queue:
            session.card_queue = [c.id for c in all_cards]
            if session.current_position > 0:
                for idx, c in enumerate(all_cards):
                    if c.position == session.current_position:
                        session.current_index = idx + 1
                        break
            else:
                session.current_index = 0

        if input_dto.current_index is not None and input_dto.current_index > 0:
            session.current_index = max(session.current_index, input_dto.current_index)

        round_shuffled = False
        if session.is_round_finished():
            # Fim de rodada: projeta e embaralha lista escalar de UUIDs exclusivamente na sessão
            shuffled_ids = FlashcardPoolService.execute_round_shuffle(all_cards, self._rng)
            session.start_new_round(shuffled_ids)
            round_shuffled = True

        next_card_id = session.get_current_card_id()
        cards_map = {c.id: c for c in all_cards}
        if next_card_id is None or next_card_id not in cards_map:
            shuffled_ids = FlashcardPoolService.execute_round_shuffle(all_cards, self._rng)
            session.start_new_round(shuffled_ids)
            round_shuffled = True
            next_card_id = session.get_current_card_id()

        next_card = (
            cards_map[next_card_id]
            if next_card_id is not None and next_card_id in cards_map
            else all_cards[0]
        )
        current_index = session.current_index + 1
        session.advance()
        session.current_position = next_card.position
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
            session_id=session.id,
        )


class GetCurrentStudyCardUseCase:
    """Caso de uso para obter o flashcard atual da sessão de estudo sem avançar."""

    def __init__(
        self,
        card_repo: IFlashcardRepository,
        session_repo: ISessionRepository,
        topic_repo: ITopicRepository | None = None,
        subject_repo: ISubjectRepository | None = None,
    ) -> None:
        self._card_repo = card_repo
        self._session_repo = session_repo
        self._topic_repo = topic_repo
        self._subject_repo = subject_repo

    def execute(self, input_dto: GetNextCardDTO, user_id: UUID | None = None) -> StudyCardDTO:
        if user_id is not None and self._subject_repo is not None and input_dto.subject_id:
            subject = self._subject_repo.get_by_id(input_dto.subject_id)
            if subject is not None and not subject.can_be_studied_by(user_id):
                raise ResourceOwnershipError("Você não tem acesso a esta matéria privada.")

        cards = self._card_repo.list_pool(input_dto.subject_id, input_dto.topic_id)
        if not cards:
            raise EmptyPoolError(
                "Nenhum flashcard disponível para estudo com os filtros selecionados."
            )

        session = self._session_repo.get_active_session(
            input_dto.subject_id, input_dto.topic_id, user_id=user_id
        )
        if session is None:
            first_card = cards[0]
            session = FlashcardPoolSession(
                user_id=user_id if user_id is not None else uuid4(),
                subject_id=input_dto.subject_id,
                topic_id_filter=input_dto.topic_id,
                current_position=first_card.position,
                round_number=1,
                current_index=0,
                card_queue=[c.id for c in cards],
            )
            self._session_repo.save_session(session)
            active_card = first_card
            current_index = 1
        else:
            if not session.card_queue:
                session.card_queue = [c.id for c in cards]
                if session.current_position > 0:
                    for idx, c in enumerate(cards):
                        if c.position == session.current_position:
                            session.current_index = idx
                            break

            cards_map = {c.id: c for c in cards}
            curr_id = session.get_current_card_id()
            if curr_id and curr_id in cards_map:
                active_card = cards_map[curr_id]
                current_index = session.current_index + 1
            else:
                matching_card = next(
                    (c for c in cards if c.position == session.current_position), None
                )
                if matching_card is not None:
                    active_card = matching_card
                else:
                    active_card = next(
                        (c for c in cards if c.position >= session.current_position), cards[0]
                    )
                    session.advance_to(active_card.position)
                    self._session_repo.save_session(session)
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
            session_id=session.id,
        )


class GetStudyBatchUseCase:
    """Caso de uso para carregar cards em lotes de 100 para o frontend reduzir requisições."""

    def __init__(
        self,
        card_repo: IFlashcardRepository,
        session_repo: ISessionRepository,
        topic_repo: ITopicRepository | None = None,
        subject_repo: ISubjectRepository | None = None,
    ) -> None:
        self._card_repo = card_repo
        self._session_repo = session_repo
        self._topic_repo = topic_repo
        self._subject_repo = subject_repo

    def execute(
        self, input_dto: GetNextCardDTO, limit: int = 100, user_id: UUID | None = None
    ) -> StudyBatchDTO:
        if user_id is not None and self._subject_repo is not None and input_dto.subject_id:
            subject = self._subject_repo.get_by_id(input_dto.subject_id)
            if subject is not None and not subject.can_be_studied_by(user_id):
                raise ResourceOwnershipError("Você não tem acesso a esta matéria privada.")

        total_cards = self._card_repo.count_pool(input_dto.subject_id, input_dto.topic_id)
        if total_cards == 0:
            raise EmptyPoolError(
                "Nenhum flashcard disponível para estudo com os filtros selecionados."
            )

        all_cards = self._card_repo.list_pool(input_dto.subject_id, input_dto.topic_id)
        session = self._session_repo.get_active_session(
            input_dto.subject_id, input_dto.topic_id, user_id=user_id
        )
        if session is None:
            session = FlashcardPoolSession(
                user_id=user_id if user_id is not None else uuid4(),
                subject_id=input_dto.subject_id,
                topic_id_filter=input_dto.topic_id,
                current_position=0,
                round_number=1,
                current_index=0,
                card_queue=[c.id for c in all_cards],
            )
            self._session_repo.save_session(session)
        elif not session.card_queue:
            session.card_queue = [c.id for c in all_cards]
            self._session_repo.save_session(session)

        # Atualiza current_index com base em current_position se aplicável
        start_index = session.current_index
        if session.current_position > 0:
            for idx, c in enumerate(all_cards):
                if c.position == session.current_position:
                    start_index = idx + 1
                    break

        batch_ids = session.card_queue[start_index : start_index + limit]
        if not batch_ids:
            batch_ids = session.card_queue[:limit]

        cards_map = {c.id: c for c in all_cards}
        cards = [cards_map[cid] for cid in batch_ids if cid in cards_map]
        if not cards:
            cards = all_cards[:limit]

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
                    session_id=session.id,
                )
            )

        return StudyBatchDTO(
            cards=card_dtos,
            total_cards=total_cards,
            round_number=session.round_number,
            has_more=len(cards) == limit,
        )
