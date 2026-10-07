"""Serviço de domínio para a Pool de Flashcards com Gap Indexing (Clean Architecture - Camada 1)."""

import math
from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from src.domain.entities import Flashcard, ReviewAuditLog, UserQuestionProgress
from src.domain.exceptions import DomainValidationError, InvalidScoreError
from src.domain.protocols import IRandomGenerator


class FlashcardPoolService:
    """Encapsula as regras matemáticas e operacionais da pool dinâmica de flashcards."""

    @staticmethod
    def calculate_target_index(total_cards: int, rng: IRandomGenerator) -> int:
        """Calcula o índice alvo nos primeiros 10% da pool para inserção de novo card."""
        if total_cards <= 0:
            return 0

        max_ten_pct = max(1, math.floor(0.1 * total_cards))
        target_limit = min(total_cards, max_ten_pct)
        return rng.randint(0, target_limit)

    @staticmethod
    def calculate_new_position(prev_pos: int | None, next_pos: int | None) -> int:
        """Calcula a nova posição inteira através de ponto médio ou avanço de gap.

        - Pool vazia: 100.
        - Cabeça: metade da primeira posição (mínimo 1).
        - Cauda: posição anterior + 100.
        - Meio: ponto médio entre a posição anterior e a próxima.
        """
        if prev_pos is None:
            if next_pos is None:
                return 100
            return max(1, next_pos // 2)

        if next_pos is None:
            return prev_pos + 100

        return prev_pos + (next_pos - prev_pos) // 2

    @staticmethod
    def needs_rebalance(positions: list[int]) -> bool:
        """Avalia se a distância entre quaisquer duas posições consecutivas é <= 1

        ou se a primeira posição atingiu <= 1.
        """
        if not positions:
            return False

        if positions[0] <= 1:
            return True

        for i in range(len(positions) - 1):
            if positions[i + 1] - positions[i] <= 1:
                return True

        return False

    @staticmethod
    def rebalance_positions(cards: list[Flashcard]) -> list[Flashcard]:
        """Redistribui uniformemente as posições dos cards em múltiplos de 100 (100, 200, 300...)

        preservando a ordem relativa original.
        """
        sorted_cards = sorted(cards, key=lambda c: c.position)
        for idx, card in enumerate(sorted_cards):
            card.position = (idx + 1) * 100
        return sorted_cards

    @staticmethod
    def execute_round_shuffle(
        cards: list[Flashcard] | list[UUID], rng: IRandomGenerator
    ) -> list[UUID]:
        """Projeta e embaralha exclusivamente a lista escalar de UUIDs para a sessão do usuário."""
        if not cards:
            return []
        first = cards[0]
        if isinstance(first, Flashcard):
            ids = [c.id for c in cards]  # type: ignore[union-attr]
        else:
            ids = [c for c in cards]
        shuffled = list(ids)
        rng.shuffle(shuffled)
        return shuffled

    @staticmethod
    def get_next_card(
        cards: list[Flashcard], current_position: int
    ) -> tuple[Flashcard | None, bool]:
        """Busca o próximo card com position > current_position.

        Retorna (card, False) se houver card, ou (None, True) se a rodada terminou.
        """
        sorted_cards = sorted(cards, key=lambda c: c.position)
        upcoming = [c for c in sorted_cards if c.position > current_position]
        if upcoming:
            return upcoming[0], False
        return None, True


class SpacingPolicyService:
    """Motor de repetição espaçada por calendário (SRS Estrito)."""

    INTERVALS: tuple[int, ...] = (1, 7, 15, 30, 60, 90, 180)

    @classmethod
    def get_interval(cls, level: int) -> int:
        """Retorna o intervalo em dias para o nível especificado (limitado entre 0 e 6)."""
        idx = max(0, min(level, len(cls.INTERVALS) - 1))
        return cls.INTERVALS[idx]

    @classmethod
    def calculate_next_schedule(
        cls, current_level: int, score: int, review_date: date
    ) -> tuple[int, date]:
        """Calcula o novo nível e a data da próxima revisão com base na nota atribuída.

        Regras:
        - score == 100:
          - se level < 6: level + 1, data = review_date + INTERVALS[novo_level]
          - se level == 6: permanece 6, data = review_date + 180 dias
        - score < 100:
          - se level == 6: penalidade severa -> level = 2, data = review_date + 15 dias
          - se level < 6: permanece no nível atual, data = review_date + INTERVALS[level]
        """
        if not (0 <= score <= 100):
            raise InvalidScoreError("A nota deve estar entre 0 e 100.")
        if not (0 <= current_level <= 6):
            raise DomainValidationError("O nível atual deve estar entre 0 e 6.")

        if score == 100:
            new_level = min(current_level + 1, 6)
            interval_days = cls.INTERVALS[new_level]
        else:
            if current_level == 6:
                new_level = 2
                interval_days = cls.INTERVALS[2]  # 15 dias
            else:
                new_level = current_level
                interval_days = cls.INTERVALS[current_level]

        return new_level, review_date + timedelta(days=interval_days)


@dataclass(slots=True, frozen=True)
class SubjectPerformance:
    """Métrica agregada de desempenho em uma matéria histórica."""

    subject_name: str
    total_reviews: int
    perfect_reviews: int
    retention_rate: float


@dataclass(slots=True, frozen=True)
class MatureDataPoint:
    """Ponto de dado na linha do tempo de perguntas consolidadas em Retenção Madura."""

    date: date
    mature_count: int


@dataclass(slots=True, frozen=True)
class ComputedStudyStatistics:
    """Estatísticas consolidadas calculadas pelo serviço de domínio."""

    total_reviews_count: int
    retention_rate: float
    mature_questions_count: int
    active_days_count: int
    srs_distribution: dict[int, int]
    subject_performances: list[SubjectPerformance]
    mature_evolution_timeline: list[MatureDataPoint]


class StudyStatisticsCalculatorService:
    """Serviço puro de domínio para consolidação e cálculo de métricas de estudo (Sprint 04)."""

    @classmethod
    def compute_metrics(
        cls,
        logs: list["ReviewAuditLog"],
        progresses: list["UserQuestionProgress"],
    ) -> ComputedStudyStatistics:
        """Calcula todas as métricas consolidadas do estudante em tempo O(N) e memória O(1)."""
        total_reviews = len(logs)
        perfect_reviews = sum(1 for log in logs if log.score == 100)
        retention_rate = (
            round((perfect_reviews / total_reviews) * 100, 2) if total_reviews > 0 else 0.0
        )

        mature_count = sum(1 for p in progresses if p.current_level >= 4)
        active_days = len({log.review_date for log in logs})

        srs_distribution: dict[int, int] = {i: 0 for i in range(7)}
        for p in progresses:
            if 0 <= p.current_level <= 6:
                srs_distribution[p.current_level] += 1

        subject_performances = cls.compute_subject_performances(logs)
        mature_timeline = cls.compute_mature_timeline(logs)

        return ComputedStudyStatistics(
            total_reviews_count=total_reviews,
            retention_rate=retention_rate,
            mature_questions_count=mature_count,
            active_days_count=active_days,
            srs_distribution=srs_distribution,
            subject_performances=subject_performances,
            mature_evolution_timeline=mature_timeline,
        )

    @classmethod
    def compute_subject_performances(cls, logs: list["ReviewAuditLog"]) -> list[SubjectPerformance]:
        """Agrupa e calcula a taxa de retenção por matéria histórica."""
        subjects_data: dict[str, list[int]] = {}
        for log in logs:
            name = log.historical_subject_name
            if name not in subjects_data:
                subjects_data[name] = [0, 0]  # [total, perfect]
            subjects_data[name][0] += 1
            if log.score == 100:
                subjects_data[name][1] += 1

        performances: list[SubjectPerformance] = []
        for name, (total, perfect) in sorted(subjects_data.items()):
            rate = round((perfect / total) * 100, 2) if total > 0 else 0.0
            performances.append(
                SubjectPerformance(
                    subject_name=name,
                    total_reviews=total,
                    perfect_reviews=perfect,
                    retention_rate=rate,
                )
            )
        return performances

    @classmethod
    def compute_mature_timeline(cls, logs: list["ReviewAuditLog"]) -> list[MatureDataPoint]:
        """Calcula a evolução cronológica líquida de perguntas em Retenção Madura (Nível 4+)."""
        if not logs:
            return []

        # Ordena logs cronologicamente
        sorted_logs = sorted(logs, key=lambda log_item: (log_item.review_date, log_item.id))
        timeline_by_date: dict[date, int] = {}
        mature_questions: set[UUID] = set()

        for log in sorted_logs:
            if log.question_id is not None:
                if log.level_after >= 4:
                    mature_questions.add(log.question_id)
                elif log.question_id in mature_questions:
                    mature_questions.remove(log.question_id)
            timeline_by_date[log.review_date] = len(mature_questions)

        return [
            MatureDataPoint(date=d, mature_count=count)
            for d, count in sorted(timeline_by_date.items())
        ]
