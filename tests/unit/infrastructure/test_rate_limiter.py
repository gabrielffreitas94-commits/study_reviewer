"""Testes unitários para o mecanismo de rate limiting."""

from unittest.mock import patch

from src.infrastructure.security.rate_limiter import (
    _REQUEST_TIMESTAMPS,
    RateLimiter,
    reset_rate_limits,
)


def test_rate_limiter_allows_under_limit() -> None:
    reset_rate_limits()
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    user_id = "user_test_1"

    assert limiter.is_allowed(user_id) is True
    assert limiter.is_allowed(user_id) is True
    assert limiter.is_allowed(user_id) is True
    assert limiter.is_allowed(user_id) is False


def test_rate_limiter_resets_limits() -> None:
    reset_rate_limits()
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    user_id = "user_test_2"

    assert limiter.is_allowed(user_id) is True
    assert limiter.is_allowed(user_id) is False

    reset_rate_limits()
    assert limiter.is_allowed(user_id) is True


def test_rate_limiter_purges_empty_keys_on_expiration() -> None:
    reset_rate_limits()
    limiter = RateLimiter(max_requests=2, window_seconds=10)
    user_id = "user_test_expire"

    current_time = 1000.0

    with patch("time.monotonic", return_value=current_time):
        assert limiter.is_allowed(user_id) is True
        assert user_id in _REQUEST_TIMESTAMPS
        assert len(_REQUEST_TIMESTAMPS[user_id]) == 1

    # Avança além da janela temporal (10s): timestamps anteriores expiram
    future_time = current_time + 15.0
    with patch("time.monotonic", return_value=future_time):
        # Durante a verificação, timestamps expirados são removidos e chave vazia é purgada
        # e como a requisição é aceita, um novo timestamp é inserido
        assert limiter.is_allowed(user_id) is True
        assert len(_REQUEST_TIMESTAMPS[user_id]) == 1


def test_rate_limiter_key_purged_when_all_timestamps_expired() -> None:
    reset_rate_limits()
    limiter = RateLimiter(max_requests=0, window_seconds=10)
    user_id = "user_test_purge"

    # Simula presença residual de timestamps no dicionário
    _REQUEST_TIMESTAMPS[user_id] = [100.0]

    with patch("time.monotonic", return_value=200.0):
        # A requisição será rejeitada pois max_requests=0, mas a chave expirada deve ser purgada
        assert limiter.is_allowed(user_id) is False
        assert user_id not in _REQUEST_TIMESTAMPS
