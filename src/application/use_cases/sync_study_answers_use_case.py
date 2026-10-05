"""Caso de uso para sincronização em lote de respostas e histórico (Camada 2)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from src.application.dto.study_dto import SyncStudyBatchDTO, SyncStudyResultDTO
from src.application.ports.repositories import ISessionRepository, IStudyEventRepository
from src.domain.exceptions import (
    DomainValidationError,
    EntityNotFoundError,
    ResourceOwnershipError,
)


class SyncStudyAnswersUseCase:
    """Ingestão idempotente de respostas com blindagem anti-IDOR e convergência de cursor."""

    def __init__(
        self,
        event_repo: IStudyEventRepository,
        session_repo: ISessionRepository,
    ) -> None:
        self._event_repo = event_repo
        self._session_repo = session_repo

    def execute(self, input_dto: SyncStudyBatchDTO, user_id: UUID) -> SyncStudyResultDTO:
        if not input_dto.events or len(input_dto.events) > 100:
            raise DomainValidationError("O lote deve conter entre 1 e 100 eventos.")

        # 1. Recupera sessão e aplica controle estrito anti-IDOR (CWE-639)
        session = self._session_repo.get_by_id(input_dto.session_id)
        if session is None:
            raise EntityNotFoundError("Sessão de estudo não encontrada.")

        if session.user_id != user_id:
            raise ResourceOwnershipError(
                "Acesso negado: a sessão informada pertence a outro usuário."
            )

        # 2. Valida autorização de cada card_id na fila da sessão
        if session.card_queue:
            authorized_card_ids = set(session.card_queue)
            for event in input_dto.events:
                if event.card_id not in authorized_card_ids:
                    raise ResourceOwnershipError(
                        f"O card '{event.card_id}' não está autorizado para esta sessão de estudo."
                    )

        # 3. Validação temporal e anti-tampering (Clock Skew e Replay)
        now = datetime.now(UTC)
        for event in input_dto.events:
            if event.status not in ("viewed", "completed"):
                raise DomainValidationError(
                    f"Status inválido '{event.status}'. Valores aceitos: 'viewed', 'completed'."
                )

            ev_time = (
                event.reviewed_at
                if event.reviewed_at.tzinfo is not None
                else event.reviewed_at.replace(tzinfo=UTC)
            )

            # Rejeição de relógio adiantado (> 60 segundos no futuro)
            if ev_time > now + timedelta(seconds=60):
                raise DomainValidationError(
                    "Timestamp inválido: evento com horário no futuro detectado."
                )

            # Janela máxima de tolerância offline (30 dias)
            if now - ev_time > timedelta(days=30):
                raise DomainValidationError(
                    "Timestamp expirado: tolerância máxima para sincronização offline é de 30 dias."
                )

        # 4. Convergência determinística do cursor da sessão no servidor
        if input_dto.batch_index is not None:
            session.current_index = max(session.current_index, input_dto.batch_index)
            self._session_repo.save_session(session)

        # 5. Inserção em lote idempotente no histórico append-only
        events_payload = [
            {
                "id": ev.id if ev.id is not None else uuid4(),
                "reviewed_at": (
                    ev.reviewed_at
                    if ev.reviewed_at.tzinfo is not None
                    else ev.reviewed_at.replace(tzinfo=UTC)
                ),
                "user_id": user_id,
                "card_id": ev.card_id,
                "session_id": input_dto.session_id,
                "status": ev.status,
                "device_id": ev.device_id,
            }
            for ev in input_dto.events
        ]

        synced_count = self._event_repo.bulk_insert(events_payload)

        return SyncStudyResultDTO(
            synced_count=synced_count,
            session_id=session.id,
            current_index=session.current_index,
            status="ok",
        )
