"""Testes unitários para controladores de avaliação em áudio e conselho multiagente (Sprint 09)."""

import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile

from src.adapters.api.evaluation_controllers import (
    DisputeEvaluationRequest,
    dispute_evaluation_endpoint,
    evaluate_audio_answer,
)
from src.application.dto.evaluation_dto import (
    DisputeEvaluationResponseDTO,
    EvaluateAnswerResponseDTO,
)
from src.domain.entities import User
from src.domain.exceptions import (
    DomainValidationError,
    EntityNotFoundError,
    EvaluationServiceError,
    InsufficientTokensError,
    QuestionNotDueError,
    QuestionNotFoundError,
    ResourceOwnershipError,
)


@pytest.fixture
def mock_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-unit-audio",
        email="audio.unit@test.local",
        name="Unit Audio User",
    )


def test_evaluate_audio_answer_controller_success(mock_user: User) -> None:
    db = MagicMock()
    q_id = uuid4()

    mock_upload = MagicMock(spec=UploadFile)
    mock_upload.read = AsyncMock(return_value=b"fake audio stream")
    mock_upload.content_type = "audio/webm"

    expected_dto = EvaluateAnswerResponseDTO(
        question_id=q_id,
        score=95,
        feedback="Excelente resposta falada.",
        coverage_score=95,
        accuracy_score=95,
        depth_score=90,
        evidence_quotes=["Artigo 5"],
        level_before=0,
        level_after=1,
        next_review_date=date(2026, 10, 9),
        tokens_deducted=250,
        remaining_token_balance=750,
        evaluation_mode="AI_AUDIO",
        transcribed_text="Mandado de segurança protege direito líquido e certo.",
    )

    with patch(
        "src.adapters.api.evaluation_controllers.EvaluateAudioAnswerUseCase.execute",
        new_callable=AsyncMock,
        return_value=expected_dto,
    ):
        result = asyncio.run(evaluate_audio_answer(q_id, mock_upload, mock_user, db))
        assert result["score"] == 95
        assert result["evaluation_mode"] == "AI_AUDIO"
        assert result["transcribed_text"] == "Mandado de segurança protege direito líquido e certo."
        assert result["tokens_deducted"] == 250


def test_evaluate_audio_answer_controller_exceptions(mock_user: User) -> None:
    db = MagicMock()
    q_id = uuid4()
    mock_upload = MagicMock(spec=UploadFile)
    mock_upload.read = AsyncMock(return_value=b"fake audio")
    mock_upload.content_type = "audio/webm"

    # 1. InsufficientTokensError -> 402
    with patch(
        "src.adapters.api.evaluation_controllers.EvaluateAudioAnswerUseCase.execute",
        new_callable=AsyncMock,
        side_effect=InsufficientTokensError("Saldo insuficiente"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(evaluate_audio_answer(q_id, mock_upload, mock_user, db))
        assert exc_info.value.status_code == 402

    # 2. DomainValidationError -> 400
    with patch(
        "src.adapters.api.evaluation_controllers.EvaluateAudioAnswerUseCase.execute",
        new_callable=AsyncMock,
        side_effect=DomainValidationError("Formato de áudio inválido"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(evaluate_audio_answer(q_id, mock_upload, mock_user, db))
        assert exc_info.value.status_code == 400

    # 3. QuestionNotDueError -> 400
    with patch(
        "src.adapters.api.evaluation_controllers.EvaluateAudioAnswerUseCase.execute",
        new_callable=AsyncMock,
        side_effect=QuestionNotDueError("Pergunta não vencida"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(evaluate_audio_answer(q_id, mock_upload, mock_user, db))
        assert exc_info.value.status_code == 400

    # 4. ResourceOwnershipError -> 403
    with patch(
        "src.adapters.api.evaluation_controllers.EvaluateAudioAnswerUseCase.execute",
        new_callable=AsyncMock,
        side_effect=ResourceOwnershipError("Acesso negado"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(evaluate_audio_answer(q_id, mock_upload, mock_user, db))
        assert exc_info.value.status_code == 403

    # 5. QuestionNotFoundError -> 404
    with patch(
        "src.adapters.api.evaluation_controllers.EvaluateAudioAnswerUseCase.execute",
        new_callable=AsyncMock,
        side_effect=QuestionNotFoundError("Pergunta não encontrada"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(evaluate_audio_answer(q_id, mock_upload, mock_user, db))
        assert exc_info.value.status_code == 404

    # 6. EntityNotFoundError -> 404
    with patch(
        "src.adapters.api.evaluation_controllers.EvaluateAudioAnswerUseCase.execute",
        new_callable=AsyncMock,
        side_effect=EntityNotFoundError("Tema não encontrado"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(evaluate_audio_answer(q_id, mock_upload, mock_user, db))
        assert exc_info.value.status_code == 404

    # 7. EvaluationServiceError -> 503
    with patch(
        "src.adapters.api.evaluation_controllers.EvaluateAudioAnswerUseCase.execute",
        new_callable=AsyncMock,
        side_effect=EvaluationServiceError("Falha de IA multimodal"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(evaluate_audio_answer(q_id, mock_upload, mock_user, db))
        assert exc_info.value.status_code == 503


def test_dispute_evaluation_controller_success(mock_user: User) -> None:
    db = MagicMock()
    q_id = uuid4()
    req = DisputeEvaluationRequest(
        student_answer="Minha resposta original",
        dispute_argument="Argumento fundamentado com base na doutrina.",
    )

    expected_dto = DisputeEvaluationResponseDTO(
        question_id=q_id,
        status="UPHELD",
        previous_score=40,
        revised_score=85,
        advocate_rationale="Advogado constatou validade.",
        critic_rationale="Crítico confirmou conformidade.",
        arbitrator_verdict="Veredito procedente.",
        level_before=0,
        level_after=1,
        next_review_date=date(2026, 10, 9),
        tokens_deducted=0,
        remaining_token_balance=1000,
        refund_dispute_tokens=True,
    )

    with patch(
        "src.adapters.api.evaluation_controllers.DisputeEvaluationUseCase.execute",
        new_callable=AsyncMock,
        return_value=expected_dto,
    ):
        result = asyncio.run(dispute_evaluation_endpoint(q_id, req, mock_user, db))
        assert result["status"] == "UPHELD"
        assert result["revised_score"] == 85
        assert result["refund_dispute_tokens"] is True


def test_dispute_evaluation_controller_exceptions(mock_user: User) -> None:
    db = MagicMock()
    q_id = uuid4()
    req = DisputeEvaluationRequest(
        student_answer="Minha resposta original",
        dispute_argument="Argumento fundamentado.",
    )

    # 1. InsufficientTokensError -> 402
    with patch(
        "src.adapters.api.evaluation_controllers.DisputeEvaluationUseCase.execute",
        new_callable=AsyncMock,
        side_effect=InsufficientTokensError("Saldo insuficiente"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(dispute_evaluation_endpoint(q_id, req, mock_user, db))
        assert exc_info.value.status_code == 402

    # 2. DomainValidationError -> 400
    with patch(
        "src.adapters.api.evaluation_controllers.DisputeEvaluationUseCase.execute",
        new_callable=AsyncMock,
        side_effect=DomainValidationError("Argumento inválido"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(dispute_evaluation_endpoint(q_id, req, mock_user, db))
        assert exc_info.value.status_code == 400

    # 3. ResourceOwnershipError -> 403
    with patch(
        "src.adapters.api.evaluation_controllers.DisputeEvaluationUseCase.execute",
        new_callable=AsyncMock,
        side_effect=ResourceOwnershipError("Acesso negado"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(dispute_evaluation_endpoint(q_id, req, mock_user, db))
        assert exc_info.value.status_code == 403

    # 4. QuestionNotFoundError -> 404
    with patch(
        "src.adapters.api.evaluation_controllers.DisputeEvaluationUseCase.execute",
        new_callable=AsyncMock,
        side_effect=QuestionNotFoundError("Pergunta não encontrada"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(dispute_evaluation_endpoint(q_id, req, mock_user, db))
        assert exc_info.value.status_code == 404

    # 5. EntityNotFoundError -> 404
    with patch(
        "src.adapters.api.evaluation_controllers.DisputeEvaluationUseCase.execute",
        new_callable=AsyncMock,
        side_effect=EntityNotFoundError("Tema não encontrado"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(dispute_evaluation_endpoint(q_id, req, mock_user, db))
        assert exc_info.value.status_code == 404

    # 6. EvaluationServiceError -> 503
    with patch(
        "src.adapters.api.evaluation_controllers.DisputeEvaluationUseCase.execute",
        new_callable=AsyncMock,
        side_effect=EvaluationServiceError("Falha na câmara multiagente"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(dispute_evaluation_endpoint(q_id, req, mock_user, db))
        assert exc_info.value.status_code == 503
