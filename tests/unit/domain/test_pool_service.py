"""Testes unitários para o FlashcardPoolService e algoritmo de Gap Indexing (ADR-002)."""

from typing import Any
from uuid import UUID, uuid4

import pytest

from src.domain.entities import Flashcard
from src.domain.protocols import IRandomGenerator
from src.domain.services import FlashcardPoolService


class DeterministicRandom(IRandomGenerator):
    """Implementação determinística para testes unitários de RNG."""

    def __init__(self, fixed_randint: int = 0) -> None:
        self.fixed_randint = fixed_randint
        self.shuffle_called = False

    def randint(self, a: int, b: int) -> int:
        return min(b, max(a, self.fixed_randint))

    def shuffle(self, items: list[Any]) -> None:
        self.shuffle_called = True
        # Inverte os itens para simular um shuffle determinístico previsível
        items.reverse()


@pytest.mark.unit
def test_calculate_target_index_empty_pool() -> None:
    """Verifica target_index com pool vazia."""
    rng = DeterministicRandom(0)
    assert FlashcardPoolService.calculate_target_index(0, rng) == 0


@pytest.mark.unit
def test_calculate_target_index_single_card() -> None:
    """Verifica target_index com pool unitária."""
    rng = DeterministicRandom(1)
    # total_cards = 1 -> floor(0.1 * 1) = 0 -> max(1, 0) = 1 -> min(1, 1) = 1
    assert FlashcardPoolService.calculate_target_index(1, rng) == 1


@pytest.mark.unit
def test_calculate_target_index_large_pool() -> None:
    """Verifica target_index com pool de 100 cards (primeiros 10%)."""
    rng = DeterministicRandom(7)
    idx = FlashcardPoolService.calculate_target_index(100, rng)
    assert idx == 7
    assert 0 <= idx <= 10


@pytest.mark.unit
def test_calculate_new_position_empty_pool() -> None:
    """Pool vazia: primeiro card recebe 100."""
    pos = FlashcardPoolService.calculate_new_position(None, None)
    assert pos == 100


@pytest.mark.unit
def test_calculate_new_position_head_insertion() -> None:
    """Inserção na cabeça antes do primeiro card (next_pos = 100)."""
    pos = FlashcardPoolService.calculate_new_position(None, 100)
    assert pos == 50

    # Inserção quando next_pos é ímpar
    pos_odd = FlashcardPoolService.calculate_new_position(None, 3)
    assert pos_odd == 1

    # Inserção quando next_pos é 1 (reserva mínima 1)
    pos_min = FlashcardPoolService.calculate_new_position(None, 1)
    assert pos_min == 1


@pytest.mark.unit
def test_calculate_new_position_tail_insertion() -> None:
    """Inserção no fim da pool após o último card (prev_pos = 400)."""
    pos = FlashcardPoolService.calculate_new_position(400, None)
    assert pos == 500


@pytest.mark.unit
def test_calculate_new_position_between_cards() -> None:
    """Inserção no ponto médio entre dois cards adjacentes."""
    pos = FlashcardPoolService.calculate_new_position(100, 200)
    assert pos == 150

    pos_tight = FlashcardPoolService.calculate_new_position(100, 103)
    assert pos_tight == 101


@pytest.mark.unit
def test_needs_rebalance_empty_or_single() -> None:
    """Verifica rebalanceamento em pools vazias ou com 1 item."""
    assert FlashcardPoolService.needs_rebalance([]) is False
    assert FlashcardPoolService.needs_rebalance([100]) is False
    # Posição 1 na cabeça requer rebalanceamento
    assert FlashcardPoolService.needs_rebalance([1]) is True


@pytest.mark.unit
def test_needs_rebalance_gap_depleted() -> None:
    """Verifica colisão quando gap <= 1 entre cards consecutivos."""
    # Gap normal (100, 200) -> 100 de distância
    assert FlashcardPoolService.needs_rebalance([100, 200, 300]) is False

    # Gap esgotado (101, 102) -> 1 de distância
    assert FlashcardPoolService.needs_rebalance([100, 101, 102, 200]) is True

    # Posições iguais (colisão)
    assert FlashcardPoolService.needs_rebalance([100, 100]) is True


@pytest.mark.unit
def test_rebalance_positions() -> None:
    """Verifica redistribuição uniforme em múltiplos de 100."""
    t_id = uuid4()
    c1 = Flashcard(topic_id=t_id, front="1", back="1", position=1)
    c2 = Flashcard(topic_id=t_id, front="2", back="2", position=2)
    c3 = Flashcard(topic_id=t_id, front="3", back="3", position=5)

    rebalanced = FlashcardPoolService.rebalance_positions([c2, c1, c3])

    # Deve ordenar por position e reatribuir 100, 200, 300
    assert [c.position for c in rebalanced] == [100, 200, 300]
    assert [c.front for c in rebalanced] == ["1", "2", "3"]


@pytest.mark.unit
def test_execute_round_shuffle() -> None:
    """Verifica shuffle geral e projeção de lista escalar de UUIDs."""
    t_id = uuid4()
    cards = [
        Flashcard(topic_id=t_id, front="Card 1", back="1", position=100),
        Flashcard(topic_id=t_id, front="Card 2", back="2", position=200),
        Flashcard(topic_id=t_id, front="Card 3", back="3", position=300),
    ]

    rng = DeterministicRandom()
    shuffled = FlashcardPoolService.execute_round_shuffle(cards, rng)

    assert rng.shuffle_called is True
    assert len(shuffled) == 3
    assert all(isinstance(uid, UUID) for uid in shuffled)
    # DeterministicRandom inverte os itens
    assert shuffled[0] == cards[2].id
    assert shuffled[1] == cards[1].id
    assert shuffled[2] == cards[0].id

    # Teste com lista de UUIDs direta
    uuid_list = [cards[0].id, cards[1].id]
    shuffled_uuids = FlashcardPoolService.execute_round_shuffle(uuid_list, rng)
    assert len(shuffled_uuids) == 2
    assert shuffled_uuids[0] == cards[1].id
    assert shuffled_uuids[1] == cards[0].id

    # Teste com lista vazia
    assert FlashcardPoolService.execute_round_shuffle([], rng) == []


@pytest.mark.unit
def test_get_next_card_nominal() -> None:
    """Busca o próximo card com position > current_position."""
    t_id = uuid4()
    cards = [
        Flashcard(topic_id=t_id, front="C1", back="1", position=100),
        Flashcard(topic_id=t_id, front="C2", back="2", position=200),
        Flashcard(topic_id=t_id, front="C3", back="3", position=300),
    ]

    # Início da rodada (current_pos = 0) -> retorna C1
    next_card, round_finished = FlashcardPoolService.get_next_card(cards, 0)
    assert next_card is not None
    assert next_card.position == 100
    assert round_finished is False

    # No meio da rodada (current_pos = 100) -> retorna C2
    next_card, round_finished = FlashcardPoolService.get_next_card(cards, 100)
    assert next_card is not None
    assert next_card.position == 200
    assert round_finished is False


@pytest.mark.unit
def test_get_next_card_end_of_round() -> None:
    """Ao atingir ou ultrapassar o último card, sinaliza fim de rodada."""
    t_id = uuid4()
    cards = [
        Flashcard(topic_id=t_id, front="C1", back="1", position=100),
        Flashcard(topic_id=t_id, front="C2", back="2", position=200),
    ]

    # No último card (current_pos = 200) -> fim de rodada
    next_card, round_finished = FlashcardPoolService.get_next_card(cards, 200)
    assert next_card is None
    assert round_finished is True

    # Pool vazia -> fim de rodada
    next_card, round_finished = FlashcardPoolService.get_next_card([], 0)
    assert next_card is None
    assert round_finished is True
