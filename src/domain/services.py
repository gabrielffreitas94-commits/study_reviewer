"""Serviço de domínio para a Pool de Flashcards com Gap Indexing (Clean Architecture - Camada 1)."""

import math
from datetime import date, timedelta
from uuid import UUID

from src.domain.entities import Flashcard
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
